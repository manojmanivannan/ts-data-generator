"""Normalization strategies for numeric time-series data."""

import logging
from abc import ABC, abstractmethod

import pandas as pd

from ts_data_generator.exceptions import ValidationError

logger = logging.getLogger(__name__)


class NormalizationStrategy(ABC):
    """Abstract base for normalization strategies."""

    @abstractmethod
    def fit(self, data: pd.DataFrame) -> None:
        """Compute scaling parameters from the data.

        Args:
            data: DataFrame containing numeric columns.
        """

    @abstractmethod
    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply normalization to a copy of the data.

        Args:
            data: DataFrame to normalize.

        Returns:
            Normalized DataFrame.
        """

    @abstractmethod
    def inverse_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Reverse the normalization.

        Args:
            data: Normalized DataFrame.

        Returns:
            DataFrame with original scale restored.
        """


class MinMaxStrategy(NormalizationStrategy):
    """Min-max normalization scaling values to [0, 1]."""

    def __init__(self) -> None:
        self._min: pd.Series | None = None
        self._max: pd.Series | None = None

    def fit(self, data: pd.DataFrame) -> None:
        numeric = data.select_dtypes(include=["number"])
        self._min = numeric.min()
        self._max = numeric.max()

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        if self._min is None or self._max is None:
            raise ValidationError("Strategy must be fit before transform.")
        numeric = data.select_dtypes(include=["number"])
        denominator = self._max - self._min
        scaled = numeric.copy()
        for col in numeric.columns:
            if denominator[col] == 0:
                scaled[col] = 0.0
            else:
                scaled[col] = (numeric[col] - self._min[col]) / denominator[col]
        return scaled

    def inverse_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        if self._min is None or self._max is None:
            raise ValidationError("Strategy must be fit before inverse_transform.")
        numeric = data.select_dtypes(include=["number"])
        descaled = numeric.copy()
        for col in numeric.columns:
            descaled[col] = (
                numeric[col] * (self._max[col] - self._min[col]) + self._min[col]
            )
        return descaled


class StandardStrategy(NormalizationStrategy):
    """Z-score normalization (mean=0, std=1)."""

    def __init__(self) -> None:
        self._mean: pd.Series | None = None
        self._std: pd.Series | None = None

    def fit(self, data: pd.DataFrame) -> None:
        numeric = data.select_dtypes(include=["number"])
        self._mean = numeric.mean()
        self._std = numeric.std()

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        if self._mean is None or self._std is None:
            raise ValidationError("Strategy must be fit before transform.")
        numeric = data.select_dtypes(include=["number"])
        scaled = numeric.copy()
        for col in numeric.columns:
            if self._std[col] == 0:
                scaled[col] = 0.0
            else:
                scaled[col] = (numeric[col] - self._mean[col]) / self._std[col]
        return scaled

    def inverse_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        if self._mean is None or self._std is None:
            raise ValidationError("Strategy must be fit before inverse_transform.")
        numeric = data.select_dtypes(include=["number"])
        descaled = numeric.copy()
        for col in numeric.columns:
            descaled[col] = numeric[col] * self._std[col] + self._mean[col]
        return descaled


class Normalizer:
    """Applies a normalization strategy to DataGen data."""

    def __init__(self, strategy: NormalizationStrategy) -> None:
        """Initialize with a normalization strategy.

        Args:
            strategy: The normalization strategy to use.
        """
        self._strategy = strategy

    @property
    def strategy(self) -> NormalizationStrategy:
        return self._strategy

    def normalize(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fit the strategy on data and apply normalization in place.

        Args:
            data: DataFrame to normalize.

        Returns:
            Normalized numeric columns (view into original).
        """
        self._strategy.fit(data)
        numeric_cols = data.select_dtypes(include=["number"]).columns
        transformed = self._strategy.transform(data)
        data[numeric_cols] = transformed
        return data

    def denormalize(self, data: pd.DataFrame) -> pd.DataFrame:
        """Reverse normalization in place.

        Args:
            data: Previously normalized DataFrame.

        Returns:
            DataFrame with original scale restored.
        """
        numeric_cols = data.select_dtypes(include=["number"]).columns
        descaled = self._strategy.inverse_transform(data)
        data[numeric_cols] = descaled
        return data


def create_normalizer(method: str) -> Normalizer:
    """Factory function for creating a Normalizer from a method name.

    Args:
        method: One of 'min-max' or 'mean-std'.

    Returns:
        Configured Normalizer instance.

    Raises:
        ValidationError: If the method name is unknown.
    """
    strategies: dict[str, NormalizationStrategy] = {
        "min-max": MinMaxStrategy(),
        "mean-std": StandardStrategy(),
    }
    strategy = strategies.get(method)
    if strategy is None:
        raise ValidationError(
            f"Unknown normalization method '{method}'. "
            f"Allowed values: {', '.join(strategies.keys())}"
        )
    return Normalizer(strategy)
