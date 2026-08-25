"""Tests for the ``expand_dimensions`` core engine mechanics (#54).

``DataGen(..., expand_dimensions=True)`` turns the output from one row per
timestamp into one row per *(timestamp x Cartesian product of all enumerable
dimensions' distinct values)*, each combination carrying its own independently
regenerated, reproducible metric series. The domain comes from the carriers'
``.domain`` (#53) — no generator introspection, no sampling. This module lifts
the #48 prototype's verified logic into the real engine.

Aggregation and the auto-emit ``<metric>_anomaly`` column fall out correctly
per series via the existing groupby keys / ``max``-OR rule (#48 confirmed) —
captured here as regression tests.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ts_data_generator import DataGen
from ts_data_generator.anomalies.point import PointAnomaly
from ts_data_generator.exceptions import ConfigurationError, ExpandError
from ts_data_generator.expand import combination_seed
from ts_data_generator.schema.models import Granularity
from ts_data_generator.utils.functions import (
    constant,
    ordered_choice,
    random_choice,
    random_float,
    random_int,
)
from ts_data_generator.utils.trends import LinearTrend

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _expand_dg(seed: int | None = 42) -> DataGen:
    """Two enumerable dimensions (2 x 2 = 4 combos) + one metric, expand on."""
    dg = DataGen(
        start_datetime="2024-01-01",
        end_datetime="2024-01-03",
        granularity=Granularity.DAILY,
        seed=seed,
        expand_dimensions=True,
    )
    dg.add_dimension("region", random_choice(["US", "EU"]))
    dg.add_dimension("env", ordered_choice(["prod", "dev"]))
    dg.add_metric("sales", {LinearTrend(offset=10, noise_level=1)})
    return dg


def _opaque_gen():
    """A plain generator with no carried domain — non-enumerable at expand time."""

    def gen():
        while True:
            yield "only"

    return gen()


# ---------------------------------------------------------------------------
# combination_seed — stable, order-insensitive per-combination seed
# ---------------------------------------------------------------------------


class TestCombinationSeed:
    def test_stable_for_same_inputs(self) -> None:
        combo = [("region", "US"), ("env", "dev")]
        assert combination_seed(42, combo) == combination_seed(42, combo)

    def test_order_insensitive(self) -> None:
        a = [("region", "US"), ("env", "dev")]
        b = [("env", "dev"), ("region", "US")]
        assert combination_seed(42, a) == combination_seed(42, b)

    def test_different_base_seed_usually_different(self) -> None:
        combo = [("region", "US")]
        assert combination_seed(42, combo) != combination_seed(99, combo)

    def test_different_combination_different(self) -> None:
        assert combination_seed(42, [("region", "US")]) != combination_seed(42, [("region", "EU")])

    def test_seed_within_uint32(self) -> None:
        seed = combination_seed(42, [("region", "US"), ("env", "dev")])
        assert 0 <= seed < 2**32


# ---------------------------------------------------------------------------
# Row shape: one row per (timestamp x Cartesian product)
# ---------------------------------------------------------------------------


class TestExpandRowShape:
    def test_row_count_is_product_times_timestamps(self) -> None:
        dg = _expand_dg()
        # 3 daily timestamps x 2 regions x 2 envs = 12 rows.
        assert len(dg.data) == 3 * 2 * 2

    def test_each_combo_has_all_timestamps(self) -> None:
        dg = _expand_dg()
        grouped = dg.data.groupby(["region", "env"])
        for _, group in grouped:
            assert len(group) == 3
            assert group.index.equals(dg.data.index.unique())

    def test_filter_by_dimension_value_yields_intact_series(self) -> None:
        dg = _expand_dg()
        us = dg.data[dg.data["region"] == "US"]
        # 2 envs x 3 timestamps = 6 rows; each (region, env) combo is intact.
        assert len(us) == 6
        for _, group in us.groupby("env"):
            assert len(group) == 3
            assert group.index.equals(dg.data.index.unique())
            assert group.index.is_monotonic_increasing

    def test_dimension_values_constant_within_combo(self) -> None:
        dg = _expand_dg()
        for _, group in dg.data.groupby(["region", "env"]):
            assert group["region"].nunique() == 1
            assert group["env"].nunique() == 1

    def test_constant_list_dimension_expands(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=7,
            expand_dimensions=True,
        )
        dg.add_dimension("tier", ["gold", "silver", "bronze"])  # static list
        dg.add_metric("m", {LinearTrend(offset=1, noise_level=0)})
        # 3 timestamps x 3 tiers = 9 rows.
        assert len(dg.data) == 9
        assert set(dg.data["tier"]) == {"gold", "silver", "bronze"}


# ---------------------------------------------------------------------------
# Determinism + order-insensitivity
# ---------------------------------------------------------------------------


class TestExpandDeterminism:
    def test_same_seed_identical(self) -> None:
        assert _expand_dg(seed=42).data.equals(_expand_dg(seed=42).data)

    def test_different_seed_different_metric_series(self) -> None:
        a = _expand_dg(seed=42).data["sales"].to_numpy()
        b = _expand_dg(seed=99).data["sales"].to_numpy()
        assert not np.array_equal(a, b)

    def test_dimension_add_order_insensitive(self) -> None:
        def build(order: str) -> DataGen:
            dg = DataGen(
                start_datetime="2024-01-01",
                end_datetime="2024-01-03",
                granularity=Granularity.DAILY,
                seed=42,
                expand_dimensions=True,
            )
            if order == "region_first":
                dg.add_dimension("region", random_choice(["US", "EU"]))
                dg.add_dimension("env", ordered_choice(["prod", "dev"]))
            else:
                dg.add_dimension("env", ordered_choice(["prod", "dev"]))
                dg.add_dimension("region", random_choice(["US", "EU"]))
            dg.add_metric("sales", {LinearTrend(offset=10, noise_level=1)})
            return dg

        assert build("region_first").data.equals(build("env_first").data)


# ---------------------------------------------------------------------------
# Row ordering: timestamp-first, then dimension values (alphabetical dim names)
# ---------------------------------------------------------------------------


class TestExpandOrdering:
    def test_timestamp_first_then_dims_alphabetical(self) -> None:
        dg = _expand_dg()
        df = dg.data.reset_index(names="_ts")
        dim_names = sorted(["region", "env"])  # alphabetical
        expected = df.sort_values(by=["_ts", *dim_names], kind="stable").reset_index(drop=True)
        # The engine output already has this order.
        df = df.reset_index(drop=True)
        pd.testing.assert_frame_equal(df, expected)

    def test_index_is_monotonic_increasing(self) -> None:
        dg = _expand_dg()
        assert dg.data.index.is_monotonic_increasing


# ---------------------------------------------------------------------------
# Non-enumerable dimensions raise a clear ExpandError
# ---------------------------------------------------------------------------


class TestExpandNonEnumerable:
    def test_random_int_raises(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=1,
            expand_dimensions=True,
        )
        with pytest.raises(ExpandError, match="port"):
            dg.add_dimension("port", random_int(1, 100))

    def test_random_float_raises(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=1,
            expand_dimensions=True,
        )
        with pytest.raises(ExpandError, match="lat"):
            dg.add_dimension("lat", random_float(0.0, 1.0))

    def test_auto_generate_name_raises(self) -> None:
        from ts_data_generator.utils.functions import auto_generate_name

        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=1,
            expand_dimensions=True,
        )
        with pytest.raises(ExpandError, match="name"):
            dg.add_dimension("name", auto_generate_name("dimension"))

    def test_opaque_generator_without_domain_raises(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=1,
            expand_dimensions=True,
        )
        with pytest.raises(ExpandError, match="custom"):
            dg.add_dimension("custom", _opaque_gen())

    def test_error_message_names_reason(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=1,
            expand_dimensions=True,
        )
        with pytest.raises(ExpandError, match="random_int"):
            dg.add_dimension("port", random_int(1, 100))

    def test_non_enumerable_ok_when_flag_off(self) -> None:
        # Same non-enumerable dimension generates normally without the flag.
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=1,
            expand_dimensions=False,
        )
        dg.add_dimension("port", random_int(1, 100))
        dg.add_metric("m", {LinearTrend(offset=1, noise_level=0)})
        assert len(dg.data) == 3  # one row per timestamp, no expansion
        assert "port" in dg.data.columns


# ---------------------------------------------------------------------------
# Default-seed behaviour: unseeded DataGen + flag on
# ---------------------------------------------------------------------------


class TestExpandDefaultSeed:
    def test_unseeded_expand_runs(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            expand_dimensions=True,  # no seed
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))
        dg.add_metric("sales", {LinearTrend(offset=10, noise_level=1)})
        # 3 timestamps x 2 regions = 6 rows — expand works without a base seed.
        assert len(dg.data) == 6

    def test_unseeded_filter_yields_intact_series(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))
        dg.add_metric("sales", {LinearTrend(offset=10, noise_level=1)})
        us = dg.data[dg.data["region"] == "US"]
        assert len(us) == 3
        assert us.index.equals(dg.data.index.unique())

    def test_unseeded_nondeterministic_across_runs(self) -> None:
        def build() -> np.ndarray:
            dg = DataGen(
                start_datetime="2024-01-01",
                end_datetime="2024-01-03",
                granularity=Granularity.DAILY,
                expand_dimensions=True,
            )
            dg.add_dimension("region", random_choice(["US", "EU"]))
            dg.add_metric("sales", {LinearTrend(offset=10, noise_level=1)})
            return dg.data.sort_values(["region"]).sort_index()["sales"].to_numpy()

        # Mirrors DefaultRNG: unseeded expand differs across runs.
        assert not np.array_equal(build(), build())


# ---------------------------------------------------------------------------
# Regression: aggregation resamples per combination (no aggregator change)
# ---------------------------------------------------------------------------


class TestExpandAggregationRegression:
    def test_aggregation_per_combination(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-07",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))
        dg.add_dimension("env", ordered_choice(["prod", "dev"]))
        dg.add_metric("sales", {LinearTrend(offset=10, slope=0, noise_level=0)})

        agg = dg.aggregate("W")
        # 4 combos x 1 weekly bucket (Mon 2024-01-01 .. Sun 2024-01-07) = 4 rows.
        assert len(agg) == 4
        # Dimensions survive as groupby keys.
        assert "region" in agg.columns and "env" in agg.columns

        # Manual per-combination mean matches the aggregator.
        raw_reset = dg.data.reset_index(names="_ts")
        raw_reset["week"] = raw_reset["_ts"].dt.to_period("W").dt.start_time
        manual = raw_reset.groupby(["region", "env", "week"])["sales"].mean().reset_index()
        agg_sorted = agg.sort_values(["region", "env"]).reset_index(drop=True)
        manual_sorted = manual.sort_values(["region", "env"]).reset_index(drop=True)
        np.testing.assert_allclose(
            agg_sorted["sales"].to_numpy(), manual_sorted["sales"].to_numpy()
        )

    def test_anomaly_label_or_rule_per_series_after_aggregation(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-07",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))
        dg.add_metric(
            "cpu",
            {LinearTrend(offset=10, slope=0, noise_level=0)},
            anomalies=[PointAnomaly(probability=0.5, magnitude=5, mode="additive")],
        )

        raw = dg.data
        agg = dg.aggregate("W")
        assert "cpu_anomaly" in agg.columns
        assert agg["cpu_anomaly"].dtype == bool

        # OR semantics per (region, week): True iff any raw row in that group is True.
        raw_reset = raw.reset_index(names="_ts")
        raw_reset["week"] = raw_reset["_ts"].dt.to_period("W").dt.start_time
        manual_any = raw_reset.groupby(["region", "week"])["cpu_anomaly"].any()
        assert int(agg["cpu_anomaly"].sum()) == int(manual_any.sum())


# ---------------------------------------------------------------------------
# Regression: anomaly labels hold per series (max/OR rule per metric.generate)
# ---------------------------------------------------------------------------


class TestExpandAnomalyLabelsPerSeries:
    def test_label_column_present_per_series(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-10",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))
        dg.add_metric(
            "cpu",
            {LinearTrend(offset=10, slope=0, noise_level=0)},
            anomalies=[PointAnomaly(probability=0.3, magnitude=5, mode="additive")],
        )
        df = dg.data
        assert "cpu_anomaly" in df.columns
        assert df["cpu_anomaly"].dtype == bool
        # Each combo's series has one label per timestamp.
        for _, group in df.groupby("region"):
            assert len(group) == 10
            assert len(group["cpu_anomaly"]) == 10

    def test_label_true_where_signal_differs_from_baseline_per_series(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-10",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))
        dg.add_metric(
            "cpu",
            {LinearTrend(offset=10, slope=0, noise_level=0)},
            anomalies=[PointAnomaly(probability=0.3, magnitude=5, mode="additive")],
        )
        df = dg.data
        # Label True exactly where signal != 10 (baseline offset, noise_level=0).
        changed = df["cpu"] != 10.0
        assert np.array_equal(df["cpu_anomaly"].to_numpy(), changed.to_numpy())


# ---------------------------------------------------------------------------
# MultiItems composition is deferred to #58 — clear error, no silent wrong data
# ---------------------------------------------------------------------------


class TestExpandMultiItemsGuard:
    def test_expand_with_multi_items_raises(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=1,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))
        dg.add_metric("sales", {LinearTrend(offset=1, noise_level=0)})
        # Both entry paths (add_multi_items and construction) raise the same
        # ConfigurationError naming multi_items / #58.
        with pytest.raises(ConfigurationError, match="multi"):
            dg.add_multi_items(["a", "b"], constant([1, 2]))

    def test_expand_with_multi_items_not_appended_on_error(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=1,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))
        dg.add_metric("sales", {LinearTrend(offset=1, noise_level=0)})
        with pytest.raises(ConfigurationError):
            dg.add_multi_items(["a", "b"], constant([1, 2]))
        # The rejected multi-item was not registered.
        assert dg.multi_items == {}

    def test_expand_with_multi_items_raises_on_construction(self) -> None:
        from ts_data_generator.schema.models import MultiItems

        mi = MultiItems(names=["a", "b"], function=constant([1, 2]))
        with pytest.raises(ConfigurationError, match="multi"):
            DataGen(
                multi_items=[mi],
                start_datetime="2024-01-01",
                end_datetime="2024-01-03",
                granularity=Granularity.DAILY,
                seed=1,
                expand_dimensions=True,
            )


# ---------------------------------------------------------------------------
# expand_dimensions property
# ---------------------------------------------------------------------------


class TestExpandDimensionsProperty:
    def test_default_off(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
        )
        assert dg.expand_dimensions is False

    def test_setter_reflected_in_output(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))
        dg.add_metric("sales", {LinearTrend(offset=10, noise_level=1)})
        off_rows = len(dg.data)
        dg.expand_dimensions = True
        on_rows = len(dg.data)
        assert off_rows == 3  # one per timestamp
        assert on_rows == 6  # 3 x 2
