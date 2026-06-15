"""Weighted fair queueing over token cost.

This module is intentionally framework-light so it can run as a gateway sidecar,
EPP plugin helper, or admission-service library. Requests are dequeued from the
tenant with the lowest `served_token_cost / weight`, then reconciled when actual
output tokens are known.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic
from typing import Any, Callable

try:
    import yaml
except ImportError:  # pragma: no cover - only needed when loading YAML files.
    yaml = None


DEFAULT_PRIORITY_WAIT_MS = {
    "Critical": 500,
    "Standard": 1000,
    "Sheddable": 2000,
}


@dataclass(frozen=True)
class TenantWeight:
    tenant: str
    weight: float

    def __post_init__(self) -> None:
        if not self.tenant:
            raise ValueError("tenant must be non-empty")
        if self.weight <= 0:
            raise ValueError(f"weight for tenant {self.tenant!r} must be > 0")


@dataclass(frozen=True)
class WFQConfig:
    tenant_weights: tuple[TenantWeight, ...]
    debt_decay_half_life_s: float = 60.0
    max_queue_wait_ms: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_PRIORITY_WAIT_MS))
    default_weight: float = 1.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WFQConfig":
        tenants = data.get("tenants", {})
        if not isinstance(tenants, dict) or not tenants:
            raise ValueError("wfq.tenants must be a non-empty mapping")

        tenant_weights = tuple(
            TenantWeight(tenant=str(tenant), weight=float(settings.get("weight", 1.0)))
            for tenant, settings in sorted(tenants.items())
        )
        aging = data.get("aging", {})
        max_wait = aging.get("max_queue_wait_ms", DEFAULT_PRIORITY_WAIT_MS)
        return cls(
            tenant_weights=tenant_weights,
            debt_decay_half_life_s=float(aging.get("debt_decay_half_life_s", 60.0)),
            max_queue_wait_ms={str(k): int(v) for k, v in max_wait.items()},
            default_weight=float(data.get("default_weight", 1.0)),
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "WFQConfig":
        if yaml is None:
            raise RuntimeError("pyyaml is required to load WFQ YAML config")
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_dict(yaml.safe_load(handle) or {})

    def weights(self) -> dict[str, float]:
        return {entry.tenant: entry.weight for entry in self.tenant_weights}

    def __post_init__(self) -> None:
        if self.debt_decay_half_life_s <= 0:
            raise ValueError("debt_decay_half_life_s must be > 0")
        if self.default_weight <= 0:
            raise ValueError("default_weight must be > 0")
        if not self.tenant_weights:
            raise ValueError("at least one tenant weight is required")
        for priority, wait_ms in self.max_queue_wait_ms.items():
            if wait_ms <= 0:
                raise ValueError(f"max queue wait for {priority!r} must be > 0")


@dataclass
class Request:
    request_id: str
    tenant: str
    priority_class: str
    input_tokens: int
    expected_output_tokens: int
    payload: dict[str, Any] = field(default_factory=dict)
    enqueued_at_s: float = 0.0
    sequence: int = 0

    @property
    def estimated_cost(self) -> int:
        return self.input_tokens + self.expected_output_tokens

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("request_id must be non-empty")
        if not self.tenant:
            raise ValueError("tenant must be non-empty")
        if self.input_tokens < 0 or self.expected_output_tokens < 0:
            raise ValueError("token counts must be >= 0")


@dataclass(frozen=True)
class QueueSnapshot:
    queued_by_tenant: dict[str, int]
    debt_by_tenant: dict[str, float]
    score_by_tenant: dict[str, float]


class WeightedFairQueue:
    def __init__(
        self,
        config: WFQConfig | dict[str, float],
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if isinstance(config, WFQConfig):
            self.config = config
            self.weights = config.weights()
        else:
            self.config = WFQConfig(
                tenant_weights=tuple(TenantWeight(tenant=k, weight=v) for k, v in sorted(config.items()))
            )
            self.weights = dict(config)
        self.clock = clock
        self.debts: dict[str, float] = {tenant: 0.0 for tenant in self.weights}
        self.queues: dict[str, list[Request]] = {tenant: [] for tenant in self.weights}
        self.last_decay = self.clock()
        self._sequence = 0

    def enqueue(self, req: Request) -> None:
        if req.tenant not in self.weights:
            self.weights[req.tenant] = self.config.default_weight
            self.queues[req.tenant] = []
            self.debts[req.tenant] = 0.0
        self.debts.setdefault(req.tenant, 0.0)
        self._sequence += 1
        req.enqueued_at_s = self.clock()
        req.sequence = self._sequence
        self.queues[req.tenant].append(req)

    def dequeue(self) -> Request | None:
        self._decay_debt()
        candidates = [tenant for tenant, q in self.queues.items() if q]
        if not candidates:
            return None
        tenant = min(candidates, key=self._tenant_order_key)
        req = self.queues[tenant].pop(0)
        self.debts[tenant] = self.debts.get(tenant, 0.0) + req.estimated_cost
        return req

    def reconcile(self, tenant: str, estimated_cost: int, actual_input_tokens: int, actual_output_tokens: int) -> None:
        if min(estimated_cost, actual_input_tokens, actual_output_tokens) < 0:
            raise ValueError("token costs must be >= 0")
        actual_cost = actual_input_tokens + actual_output_tokens
        self.debts[tenant] = self.debts.get(tenant, 0.0) + (actual_cost - estimated_cost)

    def debt_ratio(self) -> dict[str, float]:
        return {t: self._base_score(t) for t in sorted(self.weights)}

    def snapshot(self) -> QueueSnapshot:
        return QueueSnapshot(
            queued_by_tenant={tenant: len(self.queues.get(tenant, [])) for tenant in sorted(self.weights)},
            debt_by_tenant={tenant: self.debts.get(tenant, 0.0) for tenant in sorted(self.weights)},
            score_by_tenant=self.debt_ratio(),
        )

    def _tenant_order_key(self, tenant: str) -> tuple[float, int, str]:
        queue = self.queues[tenant]
        head = queue[0]
        return (self._aged_score(tenant, head), head.sequence, tenant)

    def _base_score(self, tenant: str) -> float:
        return self.debts.get(tenant, 0.0) / self.weights[tenant]

    def _aged_score(self, tenant: str, req: Request) -> float:
        max_wait_ms = self.config.max_queue_wait_ms.get(
            req.priority_class,
            self.config.max_queue_wait_ms.get("Standard", DEFAULT_PRIORITY_WAIT_MS["Standard"]),
        )
        waited_ms = max(0.0, (self.clock() - req.enqueued_at_s) * 1000.0)
        # Aging is bounded and deterministic: one max-wait interval can offset
        # one estimated request cost, preventing starvation without erasing debt.
        age_credit = min(waited_ms / max_wait_ms, 1.0) * max(req.estimated_cost, 1)
        return self._base_score(tenant) - age_credit

    def _decay_debt(self) -> None:
        now = self.clock()
        elapsed = now - self.last_decay
        if elapsed <= 0:
            return
        factor = 0.5 ** (elapsed / self.config.debt_decay_half_life_s)
        for tenant in list(self.debts):
            self.debts[tenant] *= factor
        self.last_decay = now
