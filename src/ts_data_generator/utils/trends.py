"""Trend generators for time series metrics.

Each trend class inherits from the abstract ``Trends`` base and implements
``generate(timestamps)`` to produce a numpy array of values.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Literal

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from ts_data_generator.random import SeedableRNG

logger = logging.getLogger(__name__)

# Map pandas frequency strings to conversion functions for LinearTrend.
# Each function takes (time_deltas, timestamps) and returns numeric time units.
_FREQ_CONVERTERS: dict[str, object] = {
    "s": lambda d, _: d.total_seconds() / 60.0 / 5,
    "min": lambda d, _: d.total_seconds() / 60.0 / 5,
    "5min": lambda d, _: d.total_seconds() / 60.0,
    "h": lambda d, _: d.total_seconds() / 3600.0,
    "D": lambda d, _: d.days,
    "W": lambda d, _: d.days / 7.0,
    "ME": lambda d, _: d.days / 30.0,
    "Y": lambda d, _: d.days / 365.0,
}


class Trends(ABC):
    """Abstract base for all trend generators.

    Subclasses must implement ``generate(timestamps)`` to produce a numpy
    array of values matching the length of the given timestamps.

    Args:
        name: Human-readable name for this trend.
    """

    def __init__(self, name: str = "default") -> None:
        self._name = name

    @property
    def name(self) -> str:
        """The human-readable name for this trend."""
        return self._name

    @abstractmethod
    def generate(
        self, timestamps: pd.DatetimeIndex, rng: SeedableRNG | None = None
    ) -> np.ndarray:
        """Generate trend values for the given timestamps.

        Args:
            timestamps: DatetimeIndex of time points.
            rng: Optional SeedableRNG for deterministic randomness.
                Falls back to global ``np.random`` when not provided.

        Returns:
            Numpy array of trend values with length matching timestamps.
        """
        ...


class SinusoidalTrend(Trends):
    """Generate a sinusoidal wave with optional noise.

    Args:
        name: Human-readable name.
        amplitude: Peak amplitude of the sine wave.
        freq: Period of oscillation in days.
        phase: Phase offset in hours.
        noise_level: Standard deviation of Gaussian noise to add.

    Example:
        CLI shorthand: ``SinusoidalTrend(amplitude=1,freq=24,phase=0,noise_level=0)``
    """

    _example = "sales:SinusoidalTrend(amplitude=1,freq=24,phase=0,noise_level=0)"

    def __init__(
        self,
        name: str = "default",
        amplitude: float = 1.0,
        freq: float = 1.0,
        phase: float = 0.0,
        noise_level: float = 0.0,
    ) -> None:
        super().__init__(name)
        self._amplitude = amplitude
        self._freq = freq
        self._phase = phase
        self._noise_level = noise_level

    @property
    def amplitude(self) -> float:
        return self._amplitude

    @property
    def freq(self) -> float:
        return self._freq

    @property
    def phase(self) -> float:
        return self._phase

    @property
    def noise_level(self) -> float:
        return self._noise_level

    def generate(
        self, timestamps: pd.DatetimeIndex, rng: SeedableRNG | None = None
    ) -> np.ndarray:
        time_in_days = (timestamps - timestamps[0]).total_seconds() / (24 * 3600)
        phase_in_days = self._phase / 24.0
        base_wave = self._amplitude * np.sin(
            2 * np.pi * (1 / self._freq) * (time_in_days + phase_in_days)
        )
        if rng is not None:
            noise = rng.normal(0, self._noise_level, len(timestamps))
        else:
            noise = np.random.normal(0, self._noise_level, len(timestamps))
        return base_wave + noise


class LinearTrend(Trends):
    """Generate a linear trend with optional noise.

    The slope is derived from the limit and the number of timestamps.
    Time units vary by granularity (minutes, hours, days, etc.).

    Args:
        name: Human-readable name.
        offset: Intercept (value at t=0).
        noise_level: Standard deviation of Gaussian noise.
        limit: Controls the slope; must be in [1, 1000].

    Raises:
        ValueError: If limit is outside [1, 1000].

    Example:
        CLI shorthand: ``LinearTrend(offset=0,noise_level=1,limit=10)``
    """

    _example = "sales:LinearTrend(offset=0,noise_level=1,limit=10)"

    def __init__(
        self,
        name: str = "default",
        offset: float = 0.0,
        noise_level: float = 0.0,
        limit: float = 2.0,
    ) -> None:
        super().__init__(name)
        self._offset = offset
        self._noise_level = noise_level
        if limit < 1 or limit > 1000:
            raise ValueError("Limit must be within the range of 1 and 1000")
        self._limit = limit * 10

    @property
    def limit(self) -> float:
        return self._limit

    @property
    def offset(self) -> float:
        return self._offset

    @property
    def noise_level(self) -> float:
        return self._noise_level

    def generate(
        self, timestamps: pd.DatetimeIndex, rng: SeedableRNG | None = None
    ) -> np.ndarray:
        time_deltas = timestamps - timestamps[0]

        freq_str = timestamps.freqstr if timestamps.freq else "D"
        converter = _FREQ_CONVERTERS.get(freq_str)
        if converter is None:
            logger.warning(
                "Unrecognised frequency %r for LinearTrend; defaulting to daily units.",
                freq_str,
            )
            converter = lambda d, _: d.days  # noqa: E731

        time_numeric = converter(time_deltas, timestamps)

        self._coefficient = np.radians(np.sin(self._limit / len(time_numeric)))
        base_trend = self._coefficient * time_numeric + self._offset
        if rng is not None:
            noise = rng.normal(0, self._noise_level, len(timestamps))
        else:
            noise = np.random.normal(0, self._noise_level, len(timestamps))
        return base_trend + noise


class WeekendTrend(Trends):
    """Generate a trend that spikes (up or down) on weekends.

    Args:
        name: Human-readable name.
        weekend_effect: Magnitude of the weekend adjustment.
        direction: ``'up'`` increases the value on weekends, ``'down'`` decreases.
        noise_level: Standard deviation of Gaussian noise.
        limit: Clamp value to [-limit, limit].

    Example:
        CLI shorthand: ``WeekendTrend(weekend_effect=10,direction='up',noise_level=0.5,limit=10)``
    """

    _example = "sales:WeekendTrend(weekend_effect=10,direction='up',noise_level=0.5,limit=10)"

    def __init__(
        self,
        name: str = "default",
        weekend_effect: float = 1.0,
        direction: Literal["up", "down"] = "up",
        noise_level: float = 0.0,
        limit: float = 10.0,
    ) -> None:
        super().__init__(name)
        self._weekend_effect = weekend_effect
        self._direction = direction
        self._noise_level = noise_level
        self._limit = limit

    @property
    def weekend_effect(self) -> float:
        return self._weekend_effect

    @property
    def direction(self) -> str:
        return self._direction

    @property
    def noise_level(self) -> float:
        return self._noise_level

    @property
    def limit(self) -> float:
        return self._limit

    def generate(
        self, timestamps: pd.DatetimeIndex, rng: SeedableRNG | None = None
    ) -> np.ndarray:
        trend = np.zeros(len(timestamps))
        is_weekend = timestamps.weekday >= 5
        adjustment = (
            self._weekend_effect if self._direction == "up" else -self._weekend_effect
        )
        trend[is_weekend] = adjustment
        trend = np.clip(trend, -self._limit, self._limit)
        if rng is not None:
            noise = rng.normal(0, self._noise_level, len(timestamps))
        else:
            noise = np.random.normal(0, self._noise_level, len(timestamps))
        return trend + noise


class StockTrend(Trends):
    """Generate a stock-like trend with random walk and multi-scale sine components.

    Args:
        name: Human-readable name.
        amplitude: Overall scale of the trend.
        direction: ``'up'`` for rising, ``'down'`` for falling.
        noise_level: Volatility of the random walk component.

    Example:
        CLI shorthand: ``StockTrend(amplitude=15.0,direction='up',noise_level=0.0)``
    """

    _example = "sales:StockTrend(amplitude=15.0,direction='up',noise_level=0.0)"

    def __init__(
        self,
        name: str = "default",
        amplitude: float = 15.0,
        direction: Literal["up", "down"] = "up",
        noise_level: float = 0.0,
    ) -> None:
        super().__init__(name)
        self._amplitude = amplitude
        self._direction = direction
        self._noise_level = noise_level

    @property
    def amplitude(self) -> float:
        return self._amplitude

    @property
    def direction(self) -> str:
        return self._direction

    @property
    def noise_level(self) -> float:
        return self._noise_level

    def generate(
        self, timestamps: pd.DatetimeIndex, rng: SeedableRNG | None = None
    ) -> np.ndarray:
        num_steps = len(timestamps)
        trend = np.zeros(num_steps)
        drift_per_step = self._amplitude / num_steps if num_steps > 0 else 0

        if rng is not None:
            volatilities = rng.normal(0, self._noise_level, num_steps)
        else:
            volatilities = np.random.normal(0, self._noise_level, num_steps)

        for i in range(1, num_steps):
            trend[i] = trend[i - 1] + drift_per_step + volatilities[i]

        time_in_days = (timestamps - timestamps[0]).total_seconds() / (24 * 3600)
        base_wave = (
            self._amplitude * np.sin(2 * np.pi * (time_in_days / 5))
            - self._amplitude
            + 2 * self._amplitude * np.sin(2 * np.pi * (time_in_days / 30))
            - self._amplitude
            + 2 * self._amplitude * np.sin(2 * np.pi * (time_in_days / 45))
            + 3 * self._amplitude * np.sin(2 * np.pi * (time_in_days / 180))
        )
        if self._direction == "down":
            base_wave = base_wave[::-1]

        return base_wave + trend
