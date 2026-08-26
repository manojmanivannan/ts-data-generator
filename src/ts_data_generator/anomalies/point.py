"""Point anomaly injector — isolated spikes in metric values."""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from ts_data_generator.anomalies.base import Anomaly
from ts_data_generator.random import RNGProtocol


class PointAnomaly(Anomaly):
    """Inject point anomalies at a configurable rate and magnitude.

    Args:
        probability: Per-timestamp probability of an anomaly (default 0.01).
        mode: ``"additive"`` adds magnitude to trend value;
            ``"replacement"`` replaces with magnitude.
        magnitude: Fixed scalar or ``(min, max)`` tuple for uniform sampling.

    Example:
        >>> PointAnomaly(probability=0.05, magnitude=999, mode="replacement")

    """

    def __init__(
        self,
        probability: float = 0.01,
        mode: Literal["additive", "replacement"] = "additive",
        magnitude: float | tuple[float, float] = 1.0,
    ) -> None:
        if mode not in ("additive", "replacement"):
            raise ValueError(f"mode must be 'additive' or 'replacement', got {mode!r}")
        self._probability = probability
        self._mode = mode
        self._magnitude = magnitude

    @property
    def probability(self) -> float:
        """Per-timestamp probability of a point-anomaly spike."""
        return self._probability

    @property
    def mode(self) -> Literal["additive", "replacement"]:
        """How ``magnitude`` is applied: added to or replacing the trend value."""
        return self._mode

    @property
    def magnitude(self) -> float | tuple[float, float]:
        """Fixed spike magnitude, or a ``(low, high)`` tuple sampled uniformly per hit."""
        return self._magnitude

    def intervene(
        self,
        base_array: np.ndarray,
        timestamps: pd.DatetimeIndex,
        rng: RNGProtocol,
    ) -> np.ndarray:
        """Inject isolated point-anomaly spikes into a copy of the base array.

        Each timestamp triggers independently with probability ``probability``;
        on a hit, ``magnitude`` (or a uniform draw from the ``(low, high)``
        tuple) is added to the trend value in ``additive`` mode, or replaces it
        in ``replacement`` mode.

        Returns:
            A new numpy array (a copy of ``base_array``); the input is never
            mutated.

        """
        result = base_array.copy()
        n = len(base_array)

        mask = rng.random(n) < self._probability

        if self._mode == "additive":
            magnitudes = self._sample_magnitudes(np.sum(mask), rng)
            result[mask] += magnitudes
        else:
            magnitudes = self._sample_magnitudes(np.sum(mask), rng)
            result[mask] = magnitudes

        return result

    def _sample_magnitudes(self, count: int, rng: RNGProtocol) -> np.ndarray:
        if isinstance(self._magnitude, tuple):
            low, high = self._magnitude
            return rng.uniform(low, high, count)
        return np.full(count, self._magnitude)
