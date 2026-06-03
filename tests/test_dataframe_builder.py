"""Tests for the DataFrameBuilder class."""

from __future__ import annotations

import pandas as pd
import pytest

from ts_data_generator.core.dataframe_builder import DataFrameBuilder


@pytest.fixture
def timestamps() -> pd.DatetimeIndex:
    return pd.date_range("2024-01-01", periods=10, freq="h")


@pytest.fixture
def empty_dims() -> dict:
    return {}


@pytest.fixture
def empty_metrics() -> dict:
    return {}


@pytest.fixture
def empty_multi() -> dict:
    return {}


class TestDataFrameBuilderSimple:
    """Tests with a minimal empty configuration."""

    def test_build_with_nothing_returns_index_with_epoch(
        self, timestamps: pd.DatetimeIndex
    ) -> None:
        builder = DataFrameBuilder(dimensions={}, metrics={}, multi_items={})
        result = builder.build(timestamps)

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["epoch"]
        assert len(result) == len(timestamps)

    def test_epoch_values_are_unix_timestamps(
        self, timestamps: pd.DatetimeIndex
    ) -> None:
        builder = DataFrameBuilder(dimensions={}, metrics={}, multi_items={})
        result = builder.build(timestamps)

        expected = [int(ts.timestamp()) for ts in timestamps]
        assert list(result["epoch"]) == expected


class TestDataFrameBuilderWithMetrics:
    """Tests with Metrics only."""

    def test_metric_column_appears(
        self, timestamps: pd.DatetimeIndex
    ) -> None:
        metrics = _make_metrics("temp")
        builder = DataFrameBuilder(dimensions={}, metrics=metrics, multi_items={})
        result = builder.build(timestamps)

        assert "temp" in result.columns

    def test_skips_existing_column(
        self, timestamps: pd.DatetimeIndex
    ) -> None:
        metrics = _make_metrics("temp")
        existing = pd.DataFrame({"temp": [1.0] * len(timestamps)}, index=timestamps)
        builder = DataFrameBuilder(dimensions={}, metrics=metrics, multi_items={})
        result = builder.build(timestamps, existing_data=existing)

        # The existing 'temp' column should be preserved, not regenerated
        assert list(result["temp"]) == [1.0] * len(timestamps)


class TestDataFrameBuilderWithDimensions:
    """Tests with Dimensions only."""

    def test_dimension_column_appears(
        self, timestamps: pd.DatetimeIndex
    ) -> None:
        dims = _make_dimensions("region", ["US", "EU"])
        builder = DataFrameBuilder(dimensions=dims, metrics={}, multi_items={})
        result = builder.build(timestamps)

        assert "region" in result.columns

    def test_skips_existing_column(
        self, timestamps: pd.DatetimeIndex
    ) -> None:
        dims = _make_dimensions("region", ["US", "EU"])
        existing = pd.DataFrame({"region": ["FIXED"] * len(timestamps)}, index=timestamps)
        builder = DataFrameBuilder(dimensions=dims, metrics={}, multi_items={})
        result = builder.build(timestamps, existing_data=existing)

        assert list(result["region"]) == ["FIXED"] * len(timestamps)


class TestDataFrameBuilderWithMultiItems:
    """Tests with MultiItems only."""

    def test_multi_item_columns_appear(
        self, timestamps: pd.DatetimeIndex
    ) -> None:
        multi = _make_multi_items(["a", "b"])
        builder = DataFrameBuilder(dimensions={}, metrics={}, multi_items=multi)
        result = builder.build(timestamps)

        assert "a" in result.columns
        assert "b" in result.columns

    def test_skips_existing_multi_items(
        self, timestamps: pd.DatetimeIndex
    ) -> None:
        multi = _make_multi_items(["a", "b"])
        existing = pd.DataFrame(
            {"a": [99] * len(timestamps), "b": [88] * len(timestamps)},
            index=timestamps,
        )
        builder = DataFrameBuilder(dimensions={}, metrics={}, multi_items=multi)
        result = builder.build(timestamps, existing_data=existing)

        assert list(result["a"]) == [99] * len(timestamps)
        assert list(result["b"]) == [88] * len(timestamps)

    def test_multi_item_generates_when_existing_missing_columns(
        self, timestamps: pd.DatetimeIndex
    ) -> None:
        """When existing_data has extra unrelated columns, multi-items are regenerated."""
        multi = _make_multi_items(["a", "b"])
        existing = pd.DataFrame({"extra_col": [99] * len(timestamps)}, index=timestamps)
        builder = DataFrameBuilder(dimensions={}, metrics={}, multi_items=multi)
        result = builder.build(timestamps, existing_data=existing)

        assert "a" in result.columns
        assert "b" in result.columns


class TestDataFrameBuilderColumnOrdering:
    """Tests for column sorting."""

    def test_column_order(
        self, timestamps: pd.DatetimeIndex
    ) -> None:
        metrics = _make_metrics("sales")
        dims = _make_dimensions("store", ["X", "Y"])
        multi = _make_multi_items(["extra1", "extra2"])

        builder = DataFrameBuilder(dimensions=dims, metrics=metrics, multi_items=multi)
        result = builder.build(timestamps)

        expected_order = ["epoch", "store", "sales", "extra1", "extra2"]
        assert list(result.columns) == expected_order

    def test_existing_columns_outside_order_are_dropped(
        self, timestamps: pd.DatetimeIndex
    ) -> None:
        """Columns in existing_data that aren't in dims/metrics/multi get dropped by reindex."""
        metrics = _make_metrics("sales")
        existing = pd.DataFrame(
            {"existing_col": [1] * len(timestamps)}, index=timestamps
        )
        builder = DataFrameBuilder(dimensions={}, metrics=metrics, multi_items={})
        result = builder.build(timestamps, existing_data=existing)

        # existing_col is not in column_order, so it's dropped
        assert "existing_col" not in result.columns
        assert "sales" in result.columns

    def test_column_order_with_existing(
        self, timestamps: pd.DatetimeIndex
    ) -> None:
        """When existing_data has known columns, they slot into their ordered position."""
        existing = pd.DataFrame({"sales": [99.0] * len(timestamps)}, index=timestamps)
        dims = _make_dimensions("store", ["X", "Y"])
        builder = DataFrameBuilder(dimensions=dims, metrics={}, multi_items={})
        result = builder.build(timestamps, existing_data=existing)

        expected_order = ["epoch", "store"]
        assert list(result.columns) == expected_order


class TestDataFrameBuilderRNG:
    """Tests that RNG is passed through to metric generation."""

    def test_rng_determinism(self, timestamps: pd.DatetimeIndex) -> None:
        """Using the same SeedableRNG produces identical output."""
        from ts_data_generator.random import SeedableRNG

        metrics = _make_metrics("temp")
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)

        builder1 = DataFrameBuilder(dimensions={}, metrics=metrics, multi_items={}, rng=rng1)
        builder2 = DataFrameBuilder(dimensions={}, metrics=metrics, multi_items={}, rng=rng2)

        result1 = builder1.build(timestamps)
        result2 = builder2.build(timestamps)

        pd.testing.assert_frame_equal(result1, result2)


# ── helpers ─────────────────────────────────────────────────────────────

def _make_metrics(name: str) -> dict:
    """Create a dict of one Metrics instance."""
    from ts_data_generator.schema.models import Metrics
    from ts_data_generator.utils.trends import SinusoidalTrend
    return {name: Metrics(name=name, trends={SinusoidalTrend(amplitude=1, freq=24)})}


def _make_dimensions(name: str, values: list) -> dict:
    """Create a dict of one Dimensions instance."""
    from ts_data_generator.schema.models import Dimensions
    from ts_data_generator.utils.functions import random_choice
    return {name: Dimensions(name=name, function=random_choice(values))}


def _make_multi_items(names: list[str]) -> dict:
    """Create a dict of one MultiItems instance."""
    from ts_data_generator.schema.models import MultiItems

    def linked_gen():
        while True:
            yield tuple(range(len(names)))

    return {",".join(names): MultiItems(names=names, function=linked_gen())}
