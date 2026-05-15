"""Missing data injector — NaN gaps in metric values."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import numpy as np
import pandas as pd

from ts_data_generator.anomalies.base import Anomaly

if TYPE_CHECKING:
    from ts_data_generator.random import SeedableRNG


class MissingData(Anomaly):
    """Inject NaN values to simulate missing data.

    Args:
        mode: ``"random"`` for per-timestamp independent probability;
            ``"burst"`` for consecutive blocks of NaN.
        probability: Per-timestamp NaN probability (random mode, default 0.01).
        burst_probability: Per-timestamp probability of a burst starting
            (burst mode, default 0.02).
        min_length: Minimum burst gap length (default 2).
        max_length: Maximum burst gap length (default 5).

    Example:
        >>> MissingData(mode="random", probability=0.05)
        >>> MissingData(mode="burst", burst_probability=0.02, min_length=3, max_length=10)
    """

    def __init__(
        self,
        mode: Literal["random", "burst"] = "random",
        probability: float = 0.01,
        burst_probability: float = 0.02,
        min_length: int = 2,
        max_length: int = 5,
    ) -> None:
        if mode not in ("random", "burst"):
            raise ValueError(f"mode must be 'random' or 'burst', got {mode!r}")
        self._mode = mode
        self._probability = probability
        self._burst_probability = burst_probability
        self._min_length = min_length
        self._max_length = max_length

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def probability(self) -> float:
        return self._probability

    @property
    def burst_probability(self) -> float:
        return self._burst_probability

    @property
    def min_length(self) -> int:
        return self._min_length

    @property
    def max_length(self) -> int:
        return self._max_length

    def intervene(
        self,
        base_array: np.ndarray,
        timestamps: pd.DatetimeIndex,
        rng: SeedableRNG | None = None,
    ) -> np.ndarray:
        result = base_array.copy()
        n = len(base_array)

        if self._mode == "random":
            self._apply_random(result, n, rng)
        else:
            self._apply_burst(result, n, rng)

        return result

    def _apply_random(
        self, result: np.ndarray, n: int, rng: SeedableRNG | None
    ) -> None:
        if rng is not None:
            mask = rng.random(n) < self._probability
        else:
            mask = np.random.random(n) < self._probability
        result[mask] = np.nan

    def _apply_burst(
        self, result: np.ndarray, n: int, rng: SeedableRNG | None
    ) -> None:
        i = 0
        while i < n:
            if rng is not None:
                burst_trigger = rng.random() < self._burst_probability
            else:
                burst_trigger = np.random.random() < self._burst_probability

            if burst_trigger:
                length = self._sample_length(rng)
                end = min(i + length, n)
                result[i:end] = np.nan
                i = end
            else:
                i += 1

    def _sample_length(self, rng: SeedableRNG | None) -> int:
        if rng is not None:
            return int(np.floor(rng.uniform(self._min_length, self._max_length + 1)))
        return int(np.floor(np.random.uniform(self._min_length, self._max_length + 1)))
