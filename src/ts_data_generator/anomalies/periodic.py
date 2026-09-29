"""Periodic burst anomaly — recurring, cross-metric-correlated bursts.

Real failure modes such as RF jammers, duty-cycled interference, or scheduled
maintenance jobs do not strike a single metric in isolation: a jammer keying
on for two seconds every ten seconds degrades BLER, SNR, and throughput all
at once, on the *same* timestamps, and the effect typically spikes at onset
then decays back toward baseline rather than snapping cleanly on/off.
Neither :class:`~ts_data_generator.anomalies.point.PointAnomaly` (memoryless
per-timestamp trigger) nor
:class:`~ts_data_generator.anomalies.drift.ConceptDrift` (one-shot regime
shift) can express that. :class:`EventSchedule` plus
:class:`PeriodicBurstAnomaly` fill this gap.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from ts_data_generator.anomalies.base import Anomaly
from ts_data_generator.random import RNGProtocol


class EventSchedule:
    """A reusable, lazily-materialized set of recurring burst windows.

    Building the schedule once and sharing the *same instance* across several
    :class:`PeriodicBurstAnomaly` objects (one per affected metric, plus
    optionally one driving a dedicated flag metric) guarantees every metric
    spikes and recovers on exactly the same timestamps — the correlated,
    multi-metric event pattern needed to model things like RF jammers.

    Burst starts follow a renewal process: the gap between one burst's start
    and the next is normally exactly ``period``, but with probability
    ``skip_probability`` the device instead "misses" one or more cycles, and
    the next start is drawn to be ``2..max_skip_periods`` periods away. This
    mirrors real duty-cycled interference, which mostly ticks on a fixed
    cadence but occasionally goes quiet for a few extra cycles.

    Args:
        period: Number of samples between the start of consecutive bursts
            under normal (non-skipped) operation.
        duration: Burst length in samples (fixed) or a ``(min, max)`` tuple
            sampled uniformly per burst.
        skip_probability: Probability, evaluated at each scheduled burst,
            that the *next* burst's gap is stretched to ``2..max_skip_periods``
            periods instead of exactly one (default ``0.0``, i.e. perfectly
            periodic).
        max_skip_periods: Upper bound (inclusive) on how many periods a
            skipped gap can span. Ignored when ``skip_probability`` is 0.
        jitter: Max random +/- offset (in samples) applied to each burst's
            start position.
        phase: Sample index of the first burst's start (default ``0``).

    Example:
        >>> sched = EventSchedule(period=100, duration=(15, 20),
        ...                       skip_probability=0.03, max_skip_periods=3,
        ...                       phase=250)

    """

    def __init__(
        self,
        period: int,
        duration: int | tuple[int, int] = 10,
        skip_probability: float = 0.0,
        max_skip_periods: int = 3,
        jitter: int = 0,
        phase: int = 0,
    ) -> None:
        if period <= 0:
            raise ValueError("period must be positive")
        if not 0 <= skip_probability <= 1:
            raise ValueError("skip_probability must be in [0, 1]")
        if max_skip_periods < 2:
            raise ValueError("max_skip_periods must be >= 2")
        if jitter < 0:
            raise ValueError("jitter must be >= 0")
        if phase < 0:
            raise ValueError("phase must be >= 0")
        self._period = period
        self._duration = duration
        self._skip_probability = skip_probability
        self._max_skip_periods = max_skip_periods
        self._jitter = jitter
        self._phase = phase
        self._mask: np.ndarray | None = None
        self._windows: list[tuple[int, int]] = []

    @property
    def period(self) -> int:
        """Nominal number of samples between consecutive burst starts."""
        return self._period

    @property
    def windows(self) -> list[tuple[int, int]]:
        """Resolved ``(start, end_inclusive)`` burst windows from the last ``build()``."""
        return self._windows

    def build(self, n: int, rng: RNGProtocol) -> np.ndarray:
        """Materialize the boolean mask (and window list) for ``n`` samples.

        Idempotent for a given ``n``: once built, the same mask and window
        list are returned on every subsequent call (even with a different
        ``rng``), so every :class:`PeriodicBurstAnomaly` sharing this schedule
        — and any flag metric built from it — sees identical windows.

        Returns:
            Boolean numpy array of length ``n``, ``True`` during bursts.

        """
        if self._mask is not None and len(self._mask) == n:
            return self._mask

        mask = np.zeros(n, dtype=bool)
        windows: list[tuple[int, int]] = []
        pos = self._phase

        while pos < n:
            offset = int(rng.integers(-self._jitter, self._jitter + 1)) if self._jitter else 0
            start = max(0, pos + offset)
            if isinstance(self._duration, tuple):
                length = int(rng.integers(self._duration[0], self._duration[1] + 1))
            else:
                length = self._duration
            end = min(n - 1, start + length - 1)

            if start < n:
                mask[start : end + 1] = True
                windows.append((start, end))

            if self._skip_probability > 0 and rng.random() < self._skip_probability:
                multiplier = int(rng.integers(2, self._max_skip_periods + 1))
            else:
                multiplier = 1
            pos += self._period * multiplier

        self._mask = mask
        self._windows = windows
        return mask


class PeriodicBurstAnomaly(Anomaly):
    """Inject recurring bursts with an onset spike and exponential decay tail.

    Pairs with :class:`EventSchedule` to create correlated multi-metric
    events: build one schedule, share it across several
    ``PeriodicBurstAnomaly`` instances (one per affected metric) so every
    metric spikes and decays over the exact same windows — e.g. RF jammer
    interference that simultaneously degrades BLER, SNR, and throughput, or
    a boolean flag metric that marks exactly when the event is active.

    Args:
        schedule: Shared :class:`EventSchedule` driving burst timing.
            Mutually exclusive with ``period``.
        period: Convenience shorthand for standalone (non-shared) use —
            builds an internal ``EventSchedule(period=period, duration=duration,
            skip_probability=skip_probability, max_skip_periods=max_skip_periods,
            jitter=jitter, phase=phase)``. Mutually exclusive with ``schedule``.
        duration: Forwarded to the internal schedule when ``period`` is used.
        skip_probability: Forwarded to the internal schedule when ``period`` is used.
        max_skip_periods: Forwarded to the internal schedule when ``period`` is used.
        jitter: Forwarded to the internal schedule when ``period`` is used.
        phase: Forwarded to the internal schedule when ``period`` is used.
        peak_magnitude: Fixed scalar or ``(min, max)`` tuple sampled per burst —
            the value injected at the burst's onset.
        decay: Exponential decay rate per sample applied from the burst onset
            (``0`` disables decay: the injected value stays at
            ``peak_magnitude`` for the whole burst, then drops instantly).
        tail_length: Extra samples appended after the flagged burst window over
            which the effect keeps exponentially decaying back toward baseline
            before it is cut off (default ``0``: no tail beyond the burst).
        mode: ``"additive"`` adds the decaying value to the trend value;
            ``"replacement"`` overwrites it.

    Raises:
        ValueError: If neither (or both) ``schedule`` and ``period`` are given.

    Example:
        >>> shared = EventSchedule(period=100, duration=(15, 20), phase=250,
        ...                        skip_probability=0.03)
        >>> bler_burst = PeriodicBurstAnomaly(
        ...     schedule=shared, peak_magnitude=(0.03, 0.08), decay=0.3,
        ...     tail_length=12, mode="additive",
        ... )
        >>> flag = PeriodicBurstAnomaly(
        ...     schedule=shared, peak_magnitude=1.0, decay=0.0, mode="replacement",
        ... )

    """

    def __init__(
        self,
        schedule: EventSchedule | None = None,
        period: int | None = None,
        duration: int | tuple[int, int] = 10,
        skip_probability: float = 0.0,
        max_skip_periods: int = 3,
        jitter: int = 0,
        phase: int = 0,
        peak_magnitude: float | tuple[float, float] = 1.0,
        decay: float = 0.0,
        tail_length: int = 0,
        mode: Literal["additive", "replacement"] = "additive",
    ) -> None:
        if mode not in ("additive", "replacement"):
            raise ValueError(f"mode must be 'additive' or 'replacement', got {mode!r}")
        if schedule is not None and period is not None:
            raise ValueError("Provide either 'schedule' or 'period', not both.")
        if schedule is None and period is None:
            raise ValueError("Either 'schedule' or 'period' must be provided.")
        if decay < 0:
            raise ValueError("decay must be >= 0")
        if tail_length < 0:
            raise ValueError("tail_length must be >= 0")

        self._schedule = schedule or EventSchedule(
            period=period,  # type: ignore[arg-type]
            duration=duration,
            skip_probability=skip_probability,
            max_skip_periods=max_skip_periods,
            jitter=jitter,
            phase=phase,
        )
        self._peak_magnitude = peak_magnitude
        self._decay = decay
        self._tail_length = tail_length
        self._mode = mode

    @property
    def schedule(self) -> EventSchedule:
        """The (possibly shared) :class:`EventSchedule` driving burst timing."""
        return self._schedule

    @property
    def peak_magnitude(self) -> float | tuple[float, float]:
        """Fixed onset magnitude, or a ``(low, high)`` tuple sampled per burst."""
        return self._peak_magnitude

    @property
    def decay(self) -> float:
        """Exponential decay rate per sample from the burst onset."""
        return self._decay

    @property
    def tail_length(self) -> int:
        """Extra decaying samples appended after the flagged burst window."""
        return self._tail_length

    @property
    def mode(self) -> Literal["additive", "replacement"]:
        """How the decaying burst value is applied: added to or replacing the trend value."""
        return self._mode

    def intervene(
        self,
        base_array: np.ndarray,
        timestamps: pd.DatetimeIndex,
        rng: RNGProtocol,
    ) -> np.ndarray:
        """Inject onset-spike-plus-decay bursts into a copy of the base array.

        The shared schedule is built (or reused, if another anomaly already
        built it for this many samples) to get the burst windows, then each
        window contributes a ``peak_magnitude * exp(-decay * t)`` curve
        spanning the burst plus ``tail_length`` extra samples.

        Returns:
            A new numpy array (a copy of ``base_array``); the input is never
            mutated.

        """
        result = base_array.copy()
        n = len(base_array)
        self._schedule.build(n, rng)

        for start, end in self._schedule.windows:
            peak = self._sample_peak(rng)
            length = min((end - start + 1) + self._tail_length, n - start)
            if length <= 0:
                continue
            curve = peak * np.exp(-self._decay * np.arange(length))
            idx = slice(start, start + length)
            if self._mode == "additive":
                result[idx] += curve
            else:
                result[idx] = curve

        return result

    def _sample_peak(self, rng: RNGProtocol) -> float:
        if isinstance(self._peak_magnitude, tuple):
            low, high = self._peak_magnitude
            return float(rng.uniform(low, high))
        return float(self._peak_magnitude)
