"""Admission-time reserve accounting.

Reserve accounting protects Critical capacity before the engine queue, based on
the measured goodput knee from the benchmark report. The ledger tracks request
ids so gateway/EPP integrations can release capacity exactly once when a request
finishes or is cancelled.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - only needed when loading YAML files.
    yaml = None


PRIORITY_CLASSES = ("Critical", "Standard", "Sheddable")


@dataclass
class ReserveConfig:
    knee_concurrency: int
    critical_fraction: float = 0.30
    standard_fraction: float = 0.55
    sheddable_fraction: float = 0.15
    default_tenant_kv_tokens: int = 1_000_000
    tenant_kv_tokens: dict[str, int] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReserveConfig":
        tenants = data.get("tenant_kv_tokens", {})
        return cls(
            knee_concurrency=int(data["knee_concurrency"]),
            critical_fraction=float(data.get("critical_fraction", 0.30)),
            standard_fraction=float(data.get("standard_fraction", 0.55)),
            sheddable_fraction=float(data.get("sheddable_fraction", 0.15)),
            default_tenant_kv_tokens=int(data.get("default_tenant_kv_tokens", 1_000_000)),
            tenant_kv_tokens={str(k): int(v) for k, v in tenants.items()},
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ReserveConfig":
        if yaml is None:
            raise RuntimeError("pyyaml is required to load reserve YAML config")
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_dict(yaml.safe_load(handle) or {})

    def __post_init__(self) -> None:
        if self.knee_concurrency <= 0:
            raise ValueError("knee_concurrency must be > 0")
        if self.default_tenant_kv_tokens <= 0:
            raise ValueError("default_tenant_kv_tokens must be > 0")
        fractions = (self.critical_fraction, self.standard_fraction, self.sheddable_fraction)
        if any(f <= 0 for f in fractions):
            raise ValueError("reserve fractions must be > 0")
        if sum(fractions) > 1.0:
            raise ValueError("reserve fractions must sum to <= 1.0")


@dataclass(frozen=True)
class Reservation:
    request_id: str
    tenant: str
    priority: str
    kv_tokens: int


@dataclass(frozen=True)
class AdmissionDecision:
    admitted: bool
    reason: str
    priority_capacity: int
    priority_inflight: int
    tenant_kv_capacity: int
    tenant_kv_inflight: int


class ReserveLedger:
    def __init__(self, config: ReserveConfig) -> None:
        self.config = config
        self.inflight = {priority: 0 for priority in PRIORITY_CLASSES}
        self.tenant_kv_inflight: dict[str, int] = {}
        self.reservations: dict[str, Reservation] = {}

    def capacity_for(self, priority: str) -> int:
        frac = {
            "Critical": self.config.critical_fraction,
            "Standard": self.config.standard_fraction,
            "Sheddable": self.config.sheddable_fraction,
        }.get(priority, self.config.standard_fraction)
        return max(1, int(self.config.knee_concurrency * frac))

    def tenant_kv_capacity(self, tenant: str) -> int:
        tenant_caps = self.config.tenant_kv_tokens or {}
        return tenant_caps.get(tenant, self.config.default_tenant_kv_tokens)

    def can_admit(self, tenant: str, priority: str, kv_tokens: int) -> AdmissionDecision:
        if priority not in PRIORITY_CLASSES:
            return self._decision(False, "unknown_priority", tenant, priority)
        if kv_tokens < 0:
            return self._decision(False, "invalid_kv_tokens", tenant, priority)
        if self.inflight[priority] >= self.capacity_for(priority):
            return self._decision(False, "priority_reserve_exhausted", tenant, priority)
        if self.tenant_kv_inflight.get(tenant, 0) + kv_tokens > self.tenant_kv_capacity(tenant):
            return self._decision(False, "tenant_kv_cap_exceeded", tenant, priority)
        return self._decision(True, "admitted", tenant, priority)

    def admit(self, request_id: str, tenant: str, priority: str, kv_tokens: int) -> AdmissionDecision:
        if request_id in self.reservations:
            return self._decision(False, "duplicate_request_id", tenant, priority)
        decision = self.can_admit(tenant, priority, kv_tokens)
        if not decision.admitted:
            return decision
        self.inflight[priority] += 1
        self.tenant_kv_inflight[tenant] = self.tenant_kv_inflight.get(tenant, 0) + kv_tokens
        self.reservations[request_id] = Reservation(request_id, tenant, priority, kv_tokens)
        return self._decision(True, "admitted", tenant, priority)

    def release(self, request_id: str) -> bool:
        reservation = self.reservations.pop(request_id, None)
        if reservation is None:
            return False
        self.inflight[reservation.priority] = max(0, self.inflight[reservation.priority] - 1)
        self.tenant_kv_inflight[reservation.tenant] = max(
            0, self.tenant_kv_inflight.get(reservation.tenant, 0) - reservation.kv_tokens
        )
        return True

    @staticmethod
    def estimate_kv_tokens(concurrency: int, max_context_tokens: int) -> int:
        if concurrency < 0 or max_context_tokens < 0:
            raise ValueError("concurrency and max_context_tokens must be >= 0")
        return concurrency * max_context_tokens

    def snapshot(self) -> dict[str, Any]:
        return {
            "priority_inflight": dict(sorted(self.inflight.items())),
            "tenant_kv_inflight": dict(sorted(self.tenant_kv_inflight.items())),
            "reservations": len(self.reservations),
        }

    def _decision(self, admitted: bool, reason: str, tenant: str, priority: str) -> AdmissionDecision:
        return AdmissionDecision(
            admitted=admitted,
            reason=reason,
            priority_capacity=self.capacity_for(priority),
            priority_inflight=self.inflight.get(priority, 0),
            tenant_kv_capacity=self.tenant_kv_capacity(tenant),
            tenant_kv_inflight=self.tenant_kv_inflight.get(tenant, 0),
        )
