"""Concept drift anomaly — gradual regime shifts in metric distributions."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from ts_data_generator.anomalies.base import Anomaly

if TYPE_CHECKING:
    from ts_data_generator.random import SeedableRNG


@dataclass
class DriftSegment:
    """Parameters for a single concept drift segment.

    Args:
        start_timestamp: Timestamp where drift begins (e.g. ``"2024-01-15T06:00:00"``).
            Mutually exclusive with ``start_index``.
        start_index: Index position (relative to previous segment's end) where drift
            begins. The first segment uses this as an absolute index.
            Mutually exclusive with ``start_timestamp``.
        transition_window: Duration in seconds for gradual onset (default 1800 = 30 min).
        target_mean: Mean of the target Gaussian distribution.
        target_std: Standard deviation of the target Gaussian distribution.
        hold_duration: Duration in seconds to stay in the new regime (default 7200 = 2 h).
        restore: If True, transition back to baseline after hold.
    """

    start_timestamp: pd.Timestamp | str | None = None
    start_index: int | None = None
    transition_window: float = 1800
    target_mean: float = 0.0
    target_std: float = 1.0
    hold_duration: float = 7200
    restore: bool = False

    def __post_init__(self) -> None:
        has_ts = self.start_timestamp is not None
        has_idx = self.start_index is not None
        if has_ts and has_idx:
            raise ValueError(
                "Provide exactly one of start_timestamp or start_index, not both"
            )
        if not has_ts and not has_idx:
            raise ValueError(
                "Provide exactly one of start_timestamp or start_index"
            )
        if has_idx and self.start_index < 0:  # type: ignore[operator]
            raise ValueError("start_index must be non-negative")
        if has_ts:
            if isinstance(self.start_timestamp, str) and not self.start_timestamp.strip():
                raise ValueError("start_timestamp must not be empty")
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
        ...     DriftSegment(start_timestamp="2024-01-15T06:00:00",
        ...                  transition_window=1800, target_mean=50, target_std=5,
        ...                  hold_duration=7200, restore=True),
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
        interval_seconds = (timestamps[1] - timestamps[0]).total_seconds()

        cursor = 0
        for seg in self._segments:
            if seg.start_index is not None:
                start = cursor + seg.start_index
            else:
                start = self._resolve_start(seg, timestamps, n)
            if start >= n:
                continue
            self._apply_segment(
                result, base_array, start, seg, n, rng, interval_seconds
            )
            cursor = self._segment_end(start, seg, interval_seconds, n)

        return result

    @staticmethod
    def _segment_end(
        start: int, seg: DriftSegment, interval_seconds: float, n: int
    ) -> int:
        tw = max(1, int(round(seg.transition_window / interval_seconds)))
        hd = max(1, int(round(seg.hold_duration / interval_seconds)))
        end = start + tw + hd
        if seg.restore:
            end += tw
        return min(end, n)

    @staticmethod
    def _resolve_start(seg: DriftSegment, timestamps: pd.DatetimeIndex, n: int) -> int:
        if seg.start_timestamp is None:
            return n  # should not happen — caller checks start_index first
        ts = pd.Timestamp(seg.start_timestamp)

        if ts < timestamps[0] or ts > timestamps[-1]:
            logging.warning(
                f"start_timestamp {seg.start_timestamp} is out of bounds for timestamps range "
                f"{timestamps[0]} to {timestamps[-1]}. Skipping this segment."
            )
            return (
                n  # Return n to indicate no valid start index, segment will be skipped
            )
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
        interval_seconds: float,
    ) -> None:
        tw = max(1, int(round(seg.transition_window / interval_seconds)))
        hd = max(1, int(round(seg.hold_duration / interval_seconds)))

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
                result[indices] = (1 - alphas) * target_draws + alphas * base_array[
                    indices
                ]


def _normal(loc: float, scale: float, size: int, rng: SeedableRNG | None) -> np.ndarray:
    if rng is not None:
        return rng.normal(loc, scale, size)
    return np.random.normal(loc, scale, size)
