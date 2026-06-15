"""Brownout ladder controller.

Consumes fleet KV pressure and returns the cumulative action set from §6.5.
The deployment layer is responsible for wiring these actions into gateway
feature flags. The controller is deterministic and side-effect free except for
its retained rung/stability state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - only needed when loading YAML files.
    yaml = None


DEFAULT_RUNGS = (
    (1, 0.85, ("shed_sheddable",)),
    (2, 0.90, ("cap_standard_max_tokens", "disable_speculative_decoding")),
    (3, 0.95, ("route_standard_to_fallback_model",)),
    (4, 0.97, ("shed_standard", "critical_only")),
)


@dataclass(frozen=True)
class BrownoutRung:
    level: int
    kv_cache_usage_threshold: float
    actions: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.level <= 0:
            raise ValueError("brownout rung level must be > 0")
        if not 0.0 < self.kv_cache_usage_threshold < 1.0:
            raise ValueError("brownout threshold must be between 0 and 1")
        if not self.actions:
            raise ValueError("brownout rung must declare at least one action")


@dataclass(frozen=True)
class BrownoutConfig:
    enabled: bool = True
    recovery_hysteresis: float = 0.03
    stable_recovery_intervals: int = 2
    rungs: tuple[BrownoutRung, ...] = tuple(BrownoutRung(level, threshold, actions) for level, threshold, actions in DEFAULT_RUNGS)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BrownoutConfig:
        raw_rungs = data.get("rungs")
        if raw_rungs:
            rungs = tuple(
                BrownoutRung(
                    level=int(item["level"]),
                    kv_cache_usage_threshold=float(item["kv_cache_usage_threshold"]),
                    actions=tuple(str(action) for action in item["actions"]),
                )
                for item in raw_rungs
            )
        else:
            rungs = cls.rungs
        return cls(
            enabled=bool(data.get("enabled", True)),
            recovery_hysteresis=float(data.get("recovery_hysteresis", 0.03)),
            stable_recovery_intervals=int(data.get("stable_recovery_intervals", 2)),
            rungs=tuple(sorted(rungs, key=lambda rung: rung.level)),
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> BrownoutConfig:
        if yaml is None:
            raise RuntimeError("pyyaml is required to load brownout YAML config")
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_dict(yaml.safe_load(handle) or {})

    def __post_init__(self) -> None:
        if not 0.0 <= self.recovery_hysteresis < 1.0:
            raise ValueError("recovery_hysteresis must be in [0, 1)")
        if self.stable_recovery_intervals < 1:
            raise ValueError("stable_recovery_intervals must be >= 1")
        levels = [rung.level for rung in self.rungs]
        if len(levels) != len(set(levels)):
            raise ValueError("brownout rung levels must be unique")


@dataclass(frozen=True)
class BrownoutState:
    rung: int
    actions: tuple[str, ...]
    reason: str
    stable_recovery_count: int


class BrownoutController:
    def __init__(self, config: BrownoutConfig | None = None) -> None:
        self.config = config or BrownoutConfig()
        self.rung = 0
        self.stable_recovery_count = 0

    def evaluate(self, kv_cache_usage_perc: float, preemption_storm: bool = False) -> BrownoutState:
        if not 0.0 <= kv_cache_usage_perc <= 1.0:
            raise ValueError("kv_cache_usage_perc must be in [0, 1]")
        if not self.config.enabled:
            self.rung = 0
            self.stable_recovery_count = 0
            return BrownoutState(0, (), "disabled", 0)

        target = self._target_rung(kv_cache_usage_perc, preemption_storm)
        if target >= self.rung:
            self.rung = target
            self.stable_recovery_count = 0
            reason = "pressure_increase" if target else "steady"
        elif kv_cache_usage_perc < self._threshold_for(self.rung) - self.config.recovery_hysteresis:
            self.stable_recovery_count += 1
            if self.stable_recovery_count >= self.config.stable_recovery_intervals:
                self.rung = max(0, self.rung - 1)
                self.stable_recovery_count = 0
                reason = "hysteresis_recovery"
            else:
                reason = "waiting_for_stable_recovery"
        else:
            self.stable_recovery_count = 0
            reason = "within_hysteresis"
        return BrownoutState(self.rung, self._actions(self.rung), reason, self.stable_recovery_count)

    def _target_rung(self, kv: float, storm: bool) -> int:
        if storm:
            return max((rung.level for rung in self.config.rungs), default=0)
        target = 0
        for rung in self.config.rungs:
            if kv >= rung.kv_cache_usage_threshold:
                target = rung.level
        return target

    def _threshold_for(self, rung: int) -> float:
        for item in self.config.rungs:
            if item.level == rung:
                return item.kv_cache_usage_threshold
        return 0.0

    def _actions(self, rung: int) -> tuple[str, ...]:
        actions: list[str] = []
        for item in self.config.rungs:
            if rung >= item.level:
                actions.extend(item.actions)
        return tuple(actions)
