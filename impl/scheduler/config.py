"""Unified E3 scheduler configuration loader.

The public config examples use neutral snake_case keys, while Helm values often
use camelCase. This loader normalizes both shapes into the typed policy objects
used by the scheduler primitives.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scheduler.brownout.controller import BrownoutConfig
from scheduler.reserves.reserves import ReserveConfig
from scheduler.routing.cost_classifier import RoutingConfig
from scheduler.wfq.scheduler import WFQConfig

try:
    import yaml
except ImportError:  # pragma: no cover - only needed when loading YAML files.
    yaml = None


@dataclass(frozen=True)
class SchedulerConfig:
    wfq: WFQConfig
    reserves: ReserveConfig
    brownout: BrownoutConfig
    routing: RoutingConfig

    @classmethod
    def from_yaml(cls, path: str | Path) -> SchedulerConfig:
        if yaml is None:
            raise RuntimeError("pyyaml is required to load scheduler YAML config")
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_dict(yaml.safe_load(handle) or {})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SchedulerConfig:
        scheduler = data.get("scheduler", data)
        return cls(
            wfq=WFQConfig.from_dict(_normalize_wfq(scheduler.get("wfq", scheduler))),
            reserves=ReserveConfig.from_dict(_normalize_reserves(scheduler.get("reserves", {}))),
            brownout=BrownoutConfig.from_dict(_normalize_brownout(scheduler.get("brownout", {}))),
            routing=RoutingConfig.from_dict(_normalize_routing(scheduler.get("routing", {}))),
        )


def _normalize_wfq(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "tenants": data.get("tenants", {}),
        "default_weight": _pick(data, "default_weight", "defaultWeight", default=1),
        "aging": {
            "debt_decay_half_life_s": _pick(
                data.get("aging", data), "debt_decay_half_life_s", "debtDecayHalfLifeSeconds", default=60
            ),
            "max_queue_wait_ms": _pick(
                data.get("aging", data), "max_queue_wait_ms", "maxQueueWaitMs", default={}
            ),
        },
    }


def _normalize_reserves(data: dict[str, Any]) -> dict[str, Any]:
    fractions = data.get("fractions", {})
    return {
        "knee_concurrency": _pick(data, "knee_concurrency", "kneeConcurrency"),
        "critical_fraction": _pick(data, "critical_fraction", "critical", default=fractions.get("critical", 0.30)),
        "standard_fraction": _pick(data, "standard_fraction", "standard", default=fractions.get("standard", 0.55)),
        "sheddable_fraction": _pick(data, "sheddable_fraction", "sheddable", default=fractions.get("sheddable", 0.15)),
        "default_tenant_kv_tokens": _pick(
            data, "default_tenant_kv_tokens", "defaultTenantKvTokens", default=1_000_000
        ),
        "tenant_kv_tokens": _pick(data, "tenant_kv_tokens", "tenantKvTokens", default={}),
    }


def _normalize_brownout(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "enabled": data.get("enabled", True),
        "recovery_hysteresis": _pick(data, "recovery_hysteresis", "recoveryHysteresis", default=0.03),
        "stable_recovery_intervals": _pick(
            data, "stable_recovery_intervals", "stableRecoveryIntervals", default=2
        ),
        "rungs": data.get("rungs"),
    }


def _normalize_routing(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "heavy_threshold_tokens": _pick(data, "heavy_threshold_tokens", "heavyThresholdTokens", default=32_000),
        "pools": data.get("pools", {}),
    }


def _pick(data: dict[str, Any], snake_key: str, camel_key: str, *, default: Any = None) -> Any:
    if snake_key in data:
        return data[snake_key]
    if camel_key in data:
        return data[camel_key]
    return default
