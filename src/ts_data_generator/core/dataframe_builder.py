"""Builds DataFrames from dimension, metric, and multi-item models."""

import logging
from itertools import chain

import pandas as pd

from ts_data_generator.schema.models import Dimensions, Metrics, MultiItems

logger = logging.getLogger(__name__)


class DataFrameBuilder:
    """Orchestrates the construction of the generated data DataFrame.

    Composes dimension, metric, and multi-item data into a single unified
    DataFrame indexed by timestamps.
    """

    def __init__(
        self,
        dimensions: dict[str, Dimensions],
        metrics: dict[str, Metrics],
        multi_items: dict[str, MultiItems],
    ) -> None:
        """Initialize the builder with model collections.

        Args:
            dimensions: Mapping of dimension name to Dimensions instance.
            metrics: Mapping of metric name to Metrics instance.
            multi_items: Mapping of comma-joined names to MultiItems instance.
        """
        self._dimensions = dimensions
        self._metrics = metrics
        self._multi_items = multi_items

    def build(
        self,
        timestamps: pd.DatetimeIndex,
        existing_data: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Generate data for all dimensions, metrics, and multi-items.

        Args:
            timestamps: DatetimeIndex from pd.date_range.
            existing_data: Previously generated DataFrame, used to avoid
                regenerating columns that are already present.

        Returns:
            A DataFrame with all generated columns indexed by timestamps,
            including an 'epoch' column with Unix timestamps.
        """
        existing_columns: set[str] = set()
        if existing_data is not None:
            existing_columns = set(existing_data.columns)

        metric_df = self._build_metrics(timestamps, existing_columns)
        dimension_df = self._build_dimensions(timestamps, existing_columns)
        multi_item_df = self._build_multi_items(timestamps, existing_columns)

        data = existing_data if existing_data is not None else pd.DataFrame(index=timestamps)

        for component in (dimension_df, metric_df, multi_item_df):
            if not component.empty:
                data = pd.concat([data, component], axis=1)

        if "epoch" not in data.columns:
            unix_timestamps = [int(ts.timestamp()) for ts in timestamps]
            data = pd.concat(
                [data, pd.DataFrame(unix_timestamps, columns=["epoch"], index=timestamps)],
                axis=1,
            )

        data = self._sort_columns(data)
        return data

    def _build_metrics(
        self, timestamps: pd.DatetimeIndex, existing_columns: set[str]
    ) -> pd.DataFrame:
        """Generate metric columns, skipping any already present."""
        df = pd.DataFrame(index=timestamps)
        for metric in self._metrics.values():
            if metric.name not in existing_columns:
                generated = metric.generate(timestamps)
                df = pd.concat([df, generated], axis=1)
        return df

    def _build_dimensions(
        self, timestamps: pd.DatetimeIndex, existing_columns: set[str]
    ) -> pd.DataFrame:
        """Generate dimension columns, skipping any already present."""
        df = pd.DataFrame(index=timestamps)
        for dimension in self._dimensions.values():
            if dimension.name not in existing_columns:
                generated = dimension.generate(timestamps)
                df = pd.concat([df, generated], axis=1)
        return df

    def _build_multi_items(
        self, timestamps: pd.DatetimeIndex, existing_columns: set[str]
    ) -> pd.DataFrame:
        """Generate multi-item columns, skipping any already present."""
        df = pd.DataFrame(index=timestamps)
        for multi_item in self._multi_items.values():
            if any(item not in existing_columns for item in multi_item.names):
                generated = multi_item.generate(timestamps)
                df = pd.concat([df, generated], axis=1)
        return df

    def _sort_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Order columns: epoch, dimensions, metrics, multi-items."""
        dimension_names = list(self._dimensions.keys())
        metric_names = list(self._metrics.keys())
        multi_item_names = list(
            chain.from_iterable(s.split(",") for s in self._multi_items.keys())
        )

        column_order = ["epoch"] + dimension_names + metric_names + multi_item_names
        available = [col for col in column_order if col in data.columns]
        return data.reindex(columns=available)
