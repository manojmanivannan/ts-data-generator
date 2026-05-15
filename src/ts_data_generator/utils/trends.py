"""Trend generators for time series metrics.

Each trend class inherits from the abstract ``Trends`` base and implements
``generate(timestamps)`` to produce a numpy array of values.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Literal, Optional

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

class HolidayTrend(Trends):
    """Generate a trend that spikes on holidays with optional ramp up/down windows.

    Args:
        name: Human-readable name.
        country: Country code for which to generate holidays. Mutually exclusive with dates.
        dates: Explicit list of holiday dates as ISO strings. If country is provided and holidays library is available, this parameter can be omitted.
        effect: Magnitude of the holiday spike.
        pre_window: Number of days before the holiday to ramp up the effect.
        post_window: Number of days after the holiday to ramp down the effect.
        direction: ``'up'`` or ``'down'`` for how the effect is applied.
        noise_level: Standard deviation of Gaussian noise.

    Example:
        CLI shorthand: ``HolidayTrend(effect=50,country='US',pre_window=2,post_window=2,direction='up')``

    Notes:
        - If `country` is supplied and the `holidays` library is available, holiday dates are derived automatically.
        - If `country` is not supplied or `holidays` is not installed, `dates` must be provided.
    """

    _example = "sales:HolidayTrend(effect=50,country='US',pre_window=2,post_window=2,direction='up')"

    def __init__(
        self,
        name: str = "default",
        country: Optional[str] = None,
        dates: Optional[list[str]] = None,
        effect: float = 1.0,
        pre_window: int = 0,
        post_window: int = 0,
        direction: Literal["up", "down"] = "up",
        noise_level: float = 0.0,
    ) -> None:
        super().__init__(name)
        self._country = country
        self._dates = dates
        self._effect = effect
        self._pre_window = pre_window
        self._post_window = post_window
        self._direction = direction
        self._noise_level = noise_level
        self._effect_sign = effect if direction == "up" else -abs(effect)

        if pre_window < 0 or post_window < 0:
            raise ValueError("pre_window and post_window must be non-negative")
        if country is None and dates is None:
            raise ValueError("Either country or dates must be provided for HolidayTrend")

    @property
    def country(self) -> Optional[str]:
        return self._country

    @property
    def dates(self) -> Optional[list[str]]:
        return self._dates

    @property
    def effect(self) -> float:
        return self._effect

    @property
    def pre_window(self) -> int:
        return self._pre_window

    @property
    def post_window(self) -> int:
        return self._post_window

    @property
    def direction(self) -> str:
        return self._direction

    @property
    def noise_level(self) -> float:
        return self._noise_level

    def generate(
        self, timestamps: pd.DatetimeIndex, rng: SeedableRNG | None = None
    ) -> np.ndarray:
        trend = np.zeros(len(timestamps))

        # Determine holiday dates
        if self._dates is not None:
            holiday_dates = [pd.Timestamp(d) for d in self._dates]
        else:
            try:
                import holidays  # type: ignore
            except ImportError as exc:
                raise RuntimeError(
                    "holidays library is required to compute holidays for country "
                    f"{self._country}. Install via pip install holidays or provide explicit dates."
                ) from exc
            start_year = timestamps[0].year
            end_year = timestamps[-1].year
            holiday_dates = []
            for year in range(start_year, end_year + 1):
                holiday_obj = holidays.CountryHoliday(self._country, years=[year])  # type: ignore
                holiday_dates.extend(holiday_obj.keys())

        timestamps_norm = timestamps.normalize()
        for h_ts in holiday_dates:
            h_mid = h_ts.normalize()
            diff_days = (timestamps_norm - h_mid).days
            coeff = np.zeros_like(diff_days, dtype=float)
            if self._pre_window > 0:
                up_mask = (diff_days >= -self._pre_window) & (diff_days <= 0)
                coeff[up_mask] = (diff_days[up_mask] + self._pre_window) / self._pre_window
            else:
                coeff[diff_days == 0] = 1.0
            if self._post_window > 0:
                down_mask = (diff_days >= 0) & (diff_days <= self._post_window)
                coeff[down_mask] = 1 - diff_days[down_mask] / self._post_window
            else:
                coeff[diff_days == 0] = 1.0
            trend += self._effect_sign * coeff

        if rng is not None:
            noise = rng.normal(0, self._noise_level, len(timestamps))
        else:
            noise = np.random.normal(0, self._noise_level, len(timestamps))
        return trend + noise
