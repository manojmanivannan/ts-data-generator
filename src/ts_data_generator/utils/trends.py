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


class HolidayTrend(Trends):
    """Generate a trend that ramps up/down around holidays.

    Resolves holidays automatically via the ``holidays`` library when
    installed, or from a user-provided list of date strings via the
    ``dates`` parameter.

    The effect ramps linearly: 0 at ``holiday - pre_window`` days,
    peaking at ``effect`` on the holiday, returning to 0 at
    ``holiday + post_window`` days.  Overlapping holiday windows
    sum their effects.

    Args:
        name: Human-readable name.
        country: ISO 3166-1 alpha-2 country code for holiday resolution.
        effect: Peak magnitude of the holiday adjustment.
        pre_window: Days before the holiday to start the ramp.
        post_window: Days after the holiday to end the ramp.
        direction: ``'up'`` increases values, ``'down'`` decreases.
        dates: Explicit list of date strings (``YYYY-MM-DD``) as a
            fallback when the ``holidays`` library is not installed.

    Example:
        CLI shorthand:
        ``HolidayTrend(country='US',effect=50,pre_window=3,post_window=2,direction='up')``

    Raises:
        ImportError: If ``holidays`` is not installed and no ``dates`` are provided.
    """

    _example = (
        "sales:HolidayTrend(country='US',effect=50,pre_window=3,post_window=2,direction='up')"
    )

    def __init__(
        self,
        name: str = "default",
        country: str = "US",
        effect: float = 50.0,
        pre_window: int = 3,
        post_window: int = 2,
        direction: Literal["up", "down"] = "up",
        dates: list[str] | None = None,
    ) -> None:
        super().__init__(name)
        self._country = country
        self._effect = effect
        self._pre_window = pre_window
        self._post_window = post_window
        self._direction = direction
        self._dates = dates

    @property
    def country(self) -> str:
        return self._country

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
    def dates(self) -> list[str] | None:
        return self._dates

    def _resolve_holidays(self, timestamps: pd.DatetimeIndex) -> list[pd.Timestamp]:
        """Return the list of holiday :class:`pd.Timestamp` values.

        Uses the ``holidays`` library when available, otherwise falls back
        to the user-provided ``dates`` list.
        """
        if self._dates is not None:
            return [pd.Timestamp(d) for d in self._dates]

        try:
            import holidays
        except ImportError:
            raise ImportError(
                "The 'holidays' library is required for automatic holiday resolution. "
                "Install it with: pip install holidays\n"
                "Or provide explicit dates via the 'dates' parameter."
            ) from None

        start_year = timestamps[0].year
        end_year = timestamps[-1].year
        country_holidays = holidays.country_holidays(
            self._country, years=list(range(start_year, end_year + 1))
        )

        start_date = timestamps[0].date()
        end_date = timestamps[-1].date()
        return [
            pd.Timestamp(d)
            for d in country_holidays
            if start_date <= d <= end_date
        ]

    def generate(
        self, timestamps: pd.DatetimeIndex, rng: SeedableRNG | None = None
    ) -> np.ndarray:
        holiday_dates = self._resolve_holidays(timestamps)
        result = np.zeros(len(timestamps))
        sign = 1 if self._direction == "up" else -1

        ts_dates = timestamps.normalize()

        for holiday_date in holiday_dates:
            holiday_ts = pd.Timestamp(holiday_date).normalize()
            day_offsets = (ts_dates - holiday_ts).days.values

            if self._pre_window > 0:
                pre_mask = (-self._pre_window <= day_offsets) & (day_offsets <= -1)
                result[pre_mask] += (
                    sign
                    * self._effect
                    * (self._pre_window + day_offsets[pre_mask])
                    / self._pre_window
                )

            holiday_mask = day_offsets == 0
            result[holiday_mask] += sign * self._effect

            if self._post_window > 0:
                post_mask = (1 <= day_offsets) & (day_offsets <= self._post_window)
                result[post_mask] += (
                    sign
                    * self._effect
                    * (self._post_window - day_offsets[post_mask])
                    / self._post_window
                )

        return result


class ARNoiseTrend(Trends):
    """Generate autoregressive AR(p) noise.

    ``value[t] = sum(coefficients[i] * value[t-i-1]) + N(0, noise_std)``.

    Users provide explicit ``coefficients`` (list of floats, whose length
    determines the order *p*) **or** a ``decay`` parameter that auto-generates
    stable coefficients guaranteed to have roots inside the unit circle.

    A warm-up period of *p* steps initialises the lag buffer so that the
    returned array has exactly ``len(timestamps)`` values.

    Args:
        name: Human-readable name.
        coefficients: Explicit AR coefficients. Length determines order *p*.
        noise_std: Standard deviation of the white-noise innovation.
        decay: If given (instead of ``coefficients``), auto-generate stable
            coefficients. Must be in ``(0, 1)``.
        order: Order *p* when using ``decay``.  Ignored when ``coefficients``
            is provided.

    Raises:
        ValueError: If neither (or both) ``coefficients`` and ``decay`` are given,
            or if ``decay`` is outside ``(0, 1)``.

    Example:
        CLI shorthand:
        ``ARNoiseTrend(coefficients=[0.5,-0.2],noise_std=0.5)``
    """

    _example = "sales:ARNoiseTrend(coefficients=[0.5,-0.2],noise_std=0.5)"

    def __init__(
        self,
        name: str = "default",
        coefficients: list[float] | None = None,
        noise_std: float = 1.0,
        decay: float | None = None,
        order: int = 1,
    ) -> None:
        super().__init__(name)
        if coefficients is not None and decay is not None:
            raise ValueError("Provide either 'coefficients' or 'decay', not both.")
        if coefficients is None and decay is None:
            raise ValueError("Either 'coefficients' or 'decay' must be provided.")

        if coefficients is not None:
            self._order = len(coefficients)
            self._coefficients = np.array(coefficients, dtype=np.float64)
        else:
            if not 0 < decay < 1:
                raise ValueError("decay must be in (0, 1)")
            if order < 1:
                raise ValueError("order must be >= 1")
            self._order = order
            self._coefficients = self._generate_coefficients(decay, order)

        self._noise_std = noise_std

    @staticmethod
    def _generate_coefficients(decay: float, order: int) -> np.ndarray:
        """Auto-generate stable AR coefficients via inverse Levinson-Durbin.

        Uses reflection coefficients all set to ``decay``, which guarantees
        stationarity (roots of the characteristic polynomial lie inside the
        unit circle) since every reflection coefficient is in (-1, 1).
        """
        reflection = np.full(order, decay)
        phi = np.array([reflection[0]])
        for k in range(2, order + 1):
            new_phi = np.zeros(k)
            new_phi[k - 1] = reflection[k - 1]
            for j in range(k - 1):
                new_phi[j] = phi[j] - reflection[k - 1] * phi[k - 2 - j]
            phi = new_phi
        return phi

    @property
    def order(self) -> int:
        return self._order

    @property
    def coefficients(self) -> np.ndarray:
        return self._coefficients

    @property
    def noise_std(self) -> float:
        return self._noise_std

    def generate(
        self, timestamps: pd.DatetimeIndex, rng: SeedableRNG | None = None
    ) -> np.ndarray:
        n = len(timestamps)
        p = self._order
        total = n + p

        if rng is not None:
            noise = rng.normal(0, self._noise_std, total)
        else:
            noise = np.random.normal(0, self._noise_std, total)

        result = np.zeros(total)
        result[:p] = noise[:p]

        coeffs = self._coefficients
        for t in range(p, total):
            result[t] = float(np.dot(coeffs, result[t - p : t][::-1])) + noise[t]

        return result[p:]


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
