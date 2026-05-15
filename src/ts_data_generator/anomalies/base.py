"""Abstract base class for anomaly injection."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from ts_data_generator.random import SeedableRNG


class Anomaly(ABC):
    """Abstract base for anomaly injectors.

    Subclasses implement ``intervene()`` to modify a base array in place
    or return a new array.
    """

    @abstractmethod
    def intervene(
        self,
        base_array: np.ndarray,
        timestamps: pd.DatetimeIndex,
        rng: SeedableRNG | None = None,
    ) -> np.ndarray:
        """Apply the anomaly to the base array.

        Args:
            base_array: The metric values after trend composition.
            timestamps: DatetimeIndex of time points.
            rng: Optional SeedableRNG for deterministic randomness.

        Returns:
            Modified numpy array (may be the same array mutated, or a copy).
        """
        ...
