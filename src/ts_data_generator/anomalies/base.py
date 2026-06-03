"""Abstract base class for anomaly injection."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

from ts_data_generator.random import RNGProtocol


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
        rng: RNGProtocol,
    ) -> np.ndarray:
        """Apply the anomaly to the base array.

        Args:
            base_array: The metric values after trend composition.
            timestamps: DatetimeIndex of time points.
            rng: RNG instance for deterministic or non-deterministic generation.

        Returns:
            Modified numpy array (may be the same array mutated, or a copy).
        """
        ...
