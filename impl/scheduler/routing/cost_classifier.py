"""Request cost classifier for heavy-pool routing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - only needed when loading YAML files.
    yaml = None


@dataclass(frozen=True)
class RoutingConfig:
    heavy_threshold_tokens: int = 32_000
    critical_pool: str = "critical"
    standard_pool: str = "standard"
    heavy_pool: str = "heavy"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoutingConfig:
        pools = data.get("pools", {})
        return cls(
            heavy_threshold_tokens=int(data.get("heavy_threshold_tokens", 32_000)),
            critical_pool=str(pools.get("critical", "critical")),
            standard_pool=str(pools.get("standard", "standard")),
            heavy_pool=str(pools.get("heavy", "heavy")),
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> RoutingConfig:
        if yaml is None:
            raise RuntimeError("pyyaml is required to load routing YAML config")
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_dict(yaml.safe_load(handle) or {})

    def __post_init__(self) -> None:
        if self.heavy_threshold_tokens <= 0:
            raise ValueError("heavy_threshold_tokens must be > 0")
        for name in (self.critical_pool, self.standard_pool, self.heavy_pool):
            if not name:
                raise ValueError("pool names must be non-empty")


@dataclass(frozen=True)
class RouteDecision:
    pool: str
    cost_class: str
    estimated_tokens: int
    reason: str


class CostClassifier:
    def __init__(self, config: RoutingConfig | None = None) -> None:
        self.config = config or RoutingConfig()

    def classify_context(self, input_tokens: int, output_tokens: int) -> str:
        total = self._estimated_tokens(input_tokens, output_tokens)
        if total >= self.config.heavy_threshold_tokens:
            return "heavy"
        return "standard"

    def target_pool(self, priority_class: str, input_tokens: int, output_tokens: int) -> RouteDecision:
        estimated = self._estimated_tokens(input_tokens, output_tokens)
        if priority_class == "Critical":
            return RouteDecision(self.config.critical_pool, "critical", estimated, "critical_priority")
        cost_class = self.classify_context(input_tokens, output_tokens)
        if cost_class == "heavy":
            return RouteDecision(self.config.heavy_pool, cost_class, estimated, "heavy_context")
        return RouteDecision(self.config.standard_pool, cost_class, estimated, "standard_context")

    @staticmethod
    def _estimated_tokens(input_tokens: int, output_tokens: int) -> int:
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("token counts must be >= 0")
        return input_tokens + output_tokens


def classify_context(input_tokens: int, output_tokens: int, heavy_threshold_tokens: int = 32_000) -> str:
    return CostClassifier(RoutingConfig(heavy_threshold_tokens=heavy_threshold_tokens)).classify_context(
        input_tokens, output_tokens
    )


def target_pool(priority_class: str, input_tokens: int, output_tokens: int) -> str:
    return CostClassifier().target_pool(priority_class, input_tokens, output_tokens).pool
