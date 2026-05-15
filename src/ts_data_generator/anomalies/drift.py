"""Concept drift anomaly — gradual regime shifts in metric distributions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from ts_data_generator.anomalies.base import Anomaly

if TYPE_CHECKING:
    from ts_data_generator.random import SeedableRNG


@dataclass
class DriftSegment:
    """Parameters for a single concept drift segment.

    Exactly one of ``start_index`` or ``start_timestamp`` must be provided.

    Args:
        start_index: Index into the timestamps array where drift begins.
        start_timestamp: Timestamp (resolved to index) where drift begins.
        transition_window: Number of timestamps for gradual onset.
        target_mean: Mean of the target Gaussian distribution.
        target_std: Standard deviation of the target Gaussian distribution.
        hold_duration: How long to stay in the new regime.
        restore: If True, transition back to baseline after hold.
    """

    start_index: int | None = None
    start_timestamp: pd.Timestamp | str | None = None
    transition_window: int = 50
    target_mean: float = 0.0
    target_std: float = 1.0
    hold_duration: int = 200
    restore: bool = False

    def __post_init__(self) -> None:
        if self.start_index is None and self.start_timestamp is None:
            raise ValueError(
                "Either start_index or start_timestamp must be provided"
            )
        if self.start_index is not None and self.start_timestamp is not None:
            raise ValueError(
                "Only one of start_index or start_timestamp should be provided"
            )
        if self.transition_window <= 0:
            raise ValueError("transition_window must be positive")
        if self.hold_duration <= 0:
            raise ValueError("hold_duration must be positive")
        if self.target_std < 0:
            raise ValueError("target_std must be non-negative")


class ConceptDrift(Anomaly):
    """Apply concept drift as gradual distribution-level regime shifts.

    Args:
        segments: Ordered list of DriftSegment defining the drift sequence.

    Example:
        >>> cd = ConceptDrift(segments=[
        ...     DriftSegment(start_index=100, transition_window=50,
        ...                  target_mean=50, target_std=5,
        ...                  hold_duration=200, restore=True),
        ... ])
    """

    def __init__(self, segments: list[DriftSegment]) -> None:
        self._segments = segments

    @property
    def segments(self) -> list[DriftSegment]:
        return self._segments

    def intervene(
        self,
        base_array: np.ndarray,
        timestamps: pd.DatetimeIndex,
        rng: SeedableRNG | None = None,
    ) -> np.ndarray:
        result = base_array.copy()
        n = len(base_array)

        for seg in self._segments:
            start = self._resolve_start(seg, timestamps, n)
            self._apply_segment(result, base_array, start, seg, n, rng)

        return result

    def _resolve_start(
        self, seg: DriftSegment, timestamps: pd.DatetimeIndex, n: int
    ) -> int:
        if seg.start_index is not None:
            if seg.start_index < 0 or seg.start_index >= n:
                raise ValueError(
                    f"start_index {seg.start_index} out of bounds [0, {n})"
                )
            return seg.start_index

        ts = pd.Timestamp(seg.start_timestamp)
        try:
            idx = timestamps.get_loc(ts)
        except KeyError:
            raise ValueError(
                f"start_timestamp {seg.start_timestamp} not found in timestamps"
            ) from None
        if isinstance(idx, slice):
            raise ValueError(
                f"start_timestamp {seg.start_timestamp} matched multiple timestamps"
            )
        return int(idx)

    @staticmethod
    def _apply_segment(
        result: np.ndarray,
        base_array: np.ndarray,
        start: int,
        seg: DriftSegment,
        n: int,
        rng: SeedableRNG | None,
    ) -> None:
        tw = seg.transition_window
        hd = seg.hold_duration

        # Transition into target regime
        trans_in_end = min(start + tw, n)
        if trans_in_end > start:
            indices = np.arange(start, trans_in_end)
            alphas = (indices - start) / tw
            target_draws = _normal(seg.target_mean, seg.target_std, len(indices), rng)
            result[indices] = (1 - alphas) * base_array[indices] + alphas * target_draws

        # Hold at target regime
        hold_start = trans_in_end
        hold_end = min(hold_start + hd, n)
        if hold_end > hold_start:
            result[hold_start:hold_end] = _normal(
                seg.target_mean, seg.target_std, hold_end - hold_start, rng
            )

        # Restore transition back to baseline
        if seg.restore:
            restore_start = hold_end
            restore_end = min(restore_start + tw, n)
            if restore_end > restore_start:
                indices = np.arange(restore_start, restore_end)
                alphas = (indices - restore_start) / tw
                target_draws = _normal(
                    seg.target_mean, seg.target_std, len(indices), rng
                )
                result[indices] = (1 - alphas) * target_draws + alphas * base_array[indices]


def _normal(
    loc: float, scale: float, size: int, rng: SeedableRNG | None
) -> np.ndarray:
    if rng is not None:
        return rng.normal(loc, scale, size)
    return np.random.normal(loc, scale, size)
