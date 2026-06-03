from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any

# Alias for acceptable dimension/multi-item function values
ValueSource = int | float | str | list[Any] | Generator[Any, None, None]


@dataclass
class DimensionSpec:
    name: str
    function_name: str
    args: tuple[Any, ...] | list[Any] = field(default_factory=tuple)


@dataclass
class TrendSpec:
    name: str
    kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalySpec:
    name: str
    kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class PresetConfig:
    start: str = "2024-01-01"
    end: str = "2024-01-31"
    granularity: str = "D"
    output: str = "data.csv"
    dimensions: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)
