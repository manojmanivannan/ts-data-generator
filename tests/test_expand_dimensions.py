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
from ts_data_generator.exceptions import ExpandError, ValidationError
from ts_data_generator.expand import combination_seed
from ts_data_generator.schema.models import AggregationType, Granularity
from ts_data_generator.utils.functions import (
    auto_generate_name,
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
# MultiItems composition (#58, decision #50): linked metrics + linked dimensions
# ---------------------------------------------------------------------------


class TestExpandLinkedMetrics:
    """Linked metrics (aggregation_type set) regenerate once per combination."""

    def test_linked_metrics_regenerate_per_combination(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))

        def correlated_metrics_gen():
            import random as r
            while True:
                a = r.uniform(10, 20)
                b = a * 2.0
                yield (a, b)

        dg.add_multi_items(
            names=["m1", "m2"],
            function=correlated_metrics_gen(),
            aggregation_type=["mean", "sum"],
        )

        df = dg.data
        # 3 timestamps x 2 regions = 6 rows
        assert len(df) == 6
        assert "m1" in df.columns
        assert "m2" in df.columns

        # Within each combo, correlation holds exactly: m2 == m1 * 2
        assert np.allclose(df["m2"].to_numpy(), df["m1"].to_numpy() * 2.0)

        # Across combinations, the metric series are independently regenerated
        us_m1 = df[df["region"] == "US"]["m1"].to_numpy()
        eu_m1 = df[df["region"] == "EU"]["m1"].to_numpy()
        assert not np.array_equal(us_m1, eu_m1)

    def test_linked_metrics_with_regular_metrics_and_dimensions(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=100,
            expand_dimensions=True,
        )
        dg.add_dimension("env", random_choice(["dev", "prod"]))
        dg.add_metric("cpu", {LinearTrend(offset=50, slope=1, noise_level=0)})

        def metric_pair():
            import random as r
            while True:
                reqs = r.randint(100, 500)
                errs = reqs * 0.05
                yield (reqs, errs)

        dg.add_multi_items(
            names=["requests", "errors"],
            function=metric_pair(),
            aggregation_type=["sum", "sum"],
        )

        df = dg.data
        assert len(df) == 6
        for _, group in df.groupby("env"):
            assert len(group) == 3
            assert np.allclose(group["errors"].to_numpy(), group["requests"].to_numpy() * 0.05)


class TestExpandLinkedDimensions:
    """Linked dimensions (aggregation_type=None) expand over distinct-tuple domain."""

    def test_linked_dim_expands_over_distinct_tuple_domain(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("env", random_choice(["dev", "prod"]))
        dg.add_multi_items(
            names=["city", "country"],
            function=[("New York", "US"), ("London", "UK"), ("Tokyo", "JP")],
        )
        dg.add_metric("sales", {LinearTrend(offset=10, slope=2, noise_level=0)})

        df = dg.data
        # 3 timestamps x 2 envs x 3 (city, country) tuples = 18 rows
        assert len(df) == 18

        # Tuples move as a unit: New York always with US, London with UK, Tokyo with JP
        valid_pairs = {("New York", "US"), ("London", "UK"), ("Tokyo", "JP")}
        for _, row in df.iterrows():
            assert (row["city"], row["country"]) in valid_pairs

        # Each combo is a complete, intact sequential series of 3 timestamps
        for _, group in df.groupby(["env", "city", "country"]):
            assert len(group) == 3
            assert group.index.is_monotonic_increasing

    def test_multiple_linked_dimensions_cross_independently(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-02",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        # Regular dim: 2 values
        dg.add_dimension("env", random_choice(["dev", "prod"]))
        # Linked dim 1: 2 tuples
        dg.add_multi_items(
            names=["city", "state"],
            function=[("NYC", "NY"), ("SFO", "CA")],
        )
        # Linked dim 2: 2 tuples
        dg.add_multi_items(
            names=["dept", "floor"],
            function=[("Engineering", 3), ("HR", 2)],
        )
        dg.add_metric("sales", {LinearTrend(offset=10, noise_level=0)})

        df = dg.data
        # 2 timestamps x (2 envs x 2 locations x 2 depts) = 2 x 8 = 16 rows
        assert len(df) == 16

        combos = df.groupby(["env", "city", "state", "dept", "floor"]).ngroups
        assert combos == 8

    def test_filtering_by_linked_dim_yields_complete_series(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-05",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["North", "South"]))
        dg.add_multi_items(
            names=["make", "model"],
            function=[("Toyota", "Corolla"), ("Honda", "Civic")],
        )
        dg.add_metric("speed", {LinearTrend(offset=60, noise_level=0)})

        df = dg.data
        # Filter by component column 'make' == 'Toyota'
        toyota_df = df[df["make"] == "Toyota"]
        # 5 timestamps x 2 regions = 10 rows
        assert len(toyota_df) == 10
        for _, group in toyota_df.groupby("region"):
            assert len(group) == 5
            assert list(group["model"]) == ["Corolla"] * 5

    def test_linked_dim_static_list_of_lists(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-02",
            granularity=Granularity.DAILY,
            seed=1,
            expand_dimensions=True,
        )
        dg.add_multi_items(["c1", "c2"], [[1, "a"], [2, "b"]])
        dg.add_metric("m", {LinearTrend(offset=1, noise_level=0)})
        df = dg.data
        assert len(df) == 4  # 2 timestamps x 2 tuples

    def test_linked_dim_with_explicit_domain_escape_hatch(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-02",
            granularity=Granularity.DAILY,
            seed=1,
            expand_dimensions=True,
        )

        def custom_tuple_gen():
            while True:
                yield ("A", 1)

        dg.add_multi_items(
            names=["letter", "num"],
            function=custom_tuple_gen(),
            domain=[("A", 1), ("B", 2)],
        )
        dg.add_metric("m", {LinearTrend(offset=1, noise_level=0)})
        df = dg.data
        assert len(df) == 4  # 2 timestamps x 2 tuples from declared domain


class TestExpandCompoundKeySeedAndOrdering:
    """Compound key is atomic in seed and in ordering."""

    def test_compound_key_atomic_in_seed(self) -> None:
        from ts_data_generator.expand import combination_seed

        # The compound key contributes one ("city,state", tuple_value) pair
        base_seed = 42
        seed1 = combination_seed(base_seed, [("region", "US"), ("city,state", ("NYC", "NY"))])
        seed2 = combination_seed(base_seed, [("city,state", ("NYC", "NY")), ("region", "US")])
        # Order-insensitive in combination list
        assert seed1 == seed2

        # Different tuple gives different seed
        seed3 = combination_seed(base_seed, [("region", "US"), ("city,state", ("SFO", "CA"))])
        assert seed1 != seed3

    def test_compound_key_ordering_slot_and_declared_component_order(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-02",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        # "z_region" sorts after "beta,alpha" compound name
        dg.add_dimension("z_region", random_choice(["US", "EU"]))
        # Declared component order is beta first, then alpha
        dg.add_multi_items(
            names=["beta", "alpha"],
            function=[(2, "B"), (1, "A")],
        )
        dg.add_metric("sales", {LinearTrend(offset=10, noise_level=0)})

        df = dg.data
        # Column order: epoch, beta, alpha, z_region, sales
        # "beta,alpha" compound key is before "z_region"; within group, beta before alpha
        assert list(df.columns) == ["epoch", "beta", "alpha", "z_region", "sales"]

    def test_order_insensitivity_to_add_order(self) -> None:
        # dg1: add dimension first, then multi-items
        dg1 = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg1.add_dimension("region", random_choice(["US", "EU"]))
        dg1.add_multi_items(["city", "state"], [("NYC", "NY"), ("SFO", "CA")])
        dg1.add_metric("sales", {LinearTrend(offset=10, noise_level=0)})

        # dg2: add multi-items first, then dimension
        dg2 = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg2.add_multi_items(["city", "state"], [("NYC", "NY"), ("SFO", "CA")])
        dg2.add_dimension("region", random_choice(["US", "EU"]))
        dg2.add_metric("sales", {LinearTrend(offset=10, noise_level=0)})

        # Identical row values, row ordering, and column ordering
        pd.testing.assert_frame_equal(dg1.data, dg2.data)


class TestExpandLinkedDimensionsErrorHandling:
    """Enumerable / error rule applies to tuple domains."""

    def test_opaque_generator_without_domain_raises_expand_error(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-02",
            granularity=Granularity.DAILY,
            seed=1,
            expand_dimensions=True,
        )

        def custom_gen():
            while True:
                yield (1, 2)

        with pytest.raises(ExpandError, match="dimension 'a,b' cannot be expanded"):
            dg.add_multi_items(["a", "b"], custom_gen())

    def test_non_enumerable_carrier_raises_expand_error(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-02",
            granularity=Granularity.DAILY,
            seed=1,
            expand_dimensions=True,
        )
        with pytest.raises(ExpandError):
            dg.add_multi_items(["id"], auto_generate_name("id"))

    def test_domain_supplied_to_carrier_raises_validation_error(self) -> None:
        dg = DataGen()
        carrier = constant([(1, 2)])
        with pytest.raises(ValidationError, match="domain= is only for opaque generators"):
            dg.add_multi_items(["a", "b"], carrier, domain=[(1, 2)])

    def test_expand_false_on_non_enumerable_linked_dim(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))

        def counter_pair():
            i = 0
            while True:
                i += 1
                yield (i, i * 10)

        # expand=False opts out of product and regenerates within-series
        dg.add_multi_items(["c1", "c2"], counter_pair(), expand=False)
        dg.add_metric("sales", {LinearTrend(offset=10, noise_level=0)})
        df = dg.data
        assert len(df) == 6  # 3 timestamps x 2 regions
        assert "c1" in df.columns
        assert "c2" in df.columns


class TestExpandMultiItemsAggregationAndAnomalies:
    """Aggregation and anomaly labels hold per series across MultiItems composition."""

    def test_aggregation_with_linked_dims_and_linked_metrics(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01 00:00:00",
            end_datetime="2024-01-01 03:00:00",
            granularity=Granularity.HOURLY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))
        dg.add_multi_items(
            names=["city", "state"],
            function=[("NYC", "NY"), ("SFO", "CA")],
        )
        dg.add_metric(
            "sales",
            {LinearTrend(offset=10, slope=0, noise_level=0)},
            aggregation_type=AggregationType.SUM,
        )

        def metric_pair():
            while True:
                yield (5.0, 10.0)

        dg.add_multi_items(
            names=["m1", "m2"],
            function=metric_pair(),
            aggregation_type=[AggregationType.SUM, AggregationType.AVG],
        )

        agg = dg.aggregate("D")
        # 4 combos (2 regions x 2 locations) aggregated over 4 hourly points into 1 day
        assert len(agg) == 4
        assert "region" in agg.columns
        assert "city" in agg.columns
        assert "state" in agg.columns
        assert "sales" in agg.columns
        assert "m1" in agg.columns
        assert "m2" in agg.columns
        # sales: 4 hours x 10 = 40 (SUM)
        assert (agg["sales"] == 40.0).all()
        # m1: 4 hours x 5 = 20 (SUM)
        assert (agg["m1"] == 20.0).all()
        # m2: AVG of 10.0 = 10.0 (AVG)
        assert (agg["m2"] == 10.0).all()

    def test_anomaly_labels_with_multi_items(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-05",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))
        dg.add_multi_items(["city", "state"], [("NYC", "NY"), ("SFO", "CA")])
        dg.add_metric(
            "cpu",
            {LinearTrend(offset=10, slope=0, noise_level=0)},
            anomalies=[PointAnomaly(probability=0.5, magnitude=50, mode="additive")],
        )

        df = dg.data
        # 5 timestamps x 2 regions x 2 cities = 20 rows
        assert len(df) == 20
        assert "cpu_anomaly" in df.columns
        # Each combo has boolean cpu_anomaly column matching signal deviation from baseline (10.0)
        for _, group in df.groupby(["region", "city", "state"]):
            assert len(group) == 5
            anom_flags = group["cpu_anomaly"].to_numpy()
            assert isinstance(anom_flags[0], (bool, np.bool_))
            deviated = group["cpu"].to_numpy() != 10.0
            assert np.array_equal(anom_flags, deviated)


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


# ---------------------------------------------------------------------------
# Per-dimension expand control (#57) — inherit / override / escape hatch
# ---------------------------------------------------------------------------


def _counter_gen():
    """A stateful opaque generator: yields 1, 2, 3, ... — no carried domain.

    Used to assert non-expanding dimensions regenerate one-value-per-timestamp
    *within* each series and advance *across* combos (varying independently),
    deterministically.
    """

    def gen():
        i = 0
        while True:
            i += 1
            yield i

    return gen()


class TestPerDimensionExpand:
    """``add_dimension(..., expand=None|True|False)`` resolves against the global
    flag: ``None`` inherits, ``True``/``False`` overrides (#57, decision #52)."""

    def test_expand_none_inherits_global_on(self) -> None:
        # expand=None (default) + global on -> expanding (unchanged #54 behavior).
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))  # expand=None
        dg.add_metric("sales", {LinearTrend(offset=10, noise_level=0)})
        assert len(dg.data) == 6  # 3 timestamps x 2 regions

    def test_expand_true_forces_expansion_when_global_off(self) -> None:
        # expand=True overrides a False global flag -> forces expansion.
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=False,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]), expand=True)
        dg.add_metric("sales", {LinearTrend(offset=10, noise_level=0)})
        assert len(dg.data) == 6  # expanded even though the global flag is off

    def test_expand_false_on_enumerable_opts_out(self) -> None:
        # expand=False on an enumerable dim opts it out of the product; it becomes
        # a within-series field instead of a broadcast combo key.
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]), expand=False)
        dg.add_dimension("env", ordered_choice(["prod", "dev"]))  # expanding
        dg.add_metric("sales", {LinearTrend(offset=10, noise_level=0)})
        df = dg.data
        # Only env expands: 3 timestamps x 2 envs = 6 rows (region is within-series).
        assert len(df) == 6
        # region is NOT a broadcast combo key: it varies within each env combo.
        for _, group in df.groupby("env"):
            assert len(group) == 3
            assert group["env"].nunique() == 1

    def test_expand_false_escape_hatch_on_non_enumerable(self) -> None:
        # expand=False on a non-enumerable dim excludes it from the product and
        # does NOT error, even with the global flag on (#57 sharpens spec #5).
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=1,
            expand_dimensions=True,
        )
        dg.add_dimension("port", random_int(1, 100), expand=False)  # no error
        dg.add_dimension("region", random_choice(["US", "EU"]))  # expanding
        dg.add_metric("sales", {LinearTrend(offset=10, noise_level=0)})
        df = dg.data
        # 3 timestamps x 2 regions = 6 rows; port regenerated within each series.
        assert len(df) == 6
        assert "port" in df.columns

    def test_error_fires_only_for_actually_expanding_non_enumerable(self) -> None:
        # A non-enumerable dim that inherits expansion (expand=None, global on)
        # IS actually expanding -> raises. The escape hatch above is what avoids it.
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=1,
            expand_dimensions=True,
        )
        with pytest.raises(ExpandError, match="port"):
            dg.add_dimension("port", random_int(1, 100))  # expand=None -> inherit True

    def test_non_expanding_dim_varies_within_series_across_combos(self) -> None:
        # A non-expanding dimension regenerates one-value-per-timestamp within each
        # series and varies independently across combos (a categorical within-series
        # field, not a broadcast) — Shape 1 in the #52 decision.
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]))  # expanding
        dg.add_dimension("seq", _counter_gen(), expand=False)  # within-series
        dg.add_metric("sales", {LinearTrend(offset=10, noise_level=0)})
        df = dg.data
        assert len(df) == 6  # 3 timestamps x 2 regions
        # The counter advanced across combos: each combo is strictly increasing
        # within its series, the two combos are disjoint, and the union is six
        # consecutive integers (the counter yields one value per timestamp per
        # combo, advancing across combos — robust to how many regenerations ran).
        seq_values = set(df["seq"])
        assert len(seq_values) == 6
        assert max(seq_values) - min(seq_values) == 5
        for _, group in df.groupby("region"):
            assert list(group.sort_index()["seq"]) == sorted(group["seq"])
        us = set(df[df["region"] == "US"]["seq"])
        eu = set(df[df["region"] == "EU"]["seq"])
        assert us.isdisjoint(eu)

    def test_all_dims_opt_out_falls_back_to_one_row_per_timestamp(self) -> None:
        # Global on but every dim expand=False -> nothing expands -> normal path.
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", random_choice(["US", "EU"]), expand=False)
        dg.add_metric("sales", {LinearTrend(offset=10, noise_level=0)})
        assert len(dg.data) == 3  # one row per timestamp, no expansion

    def test_dimension_exposes_expand_attribute(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
        )
        dg.add_dimension("a", random_choice(["x", "y"]))
        dg.add_dimension("b", random_choice(["x", "y"]), expand=False)
        dg.add_dimension("c", random_choice(["x", "y"]), expand=True)
        assert dg.dimensions["a"].expand is None
        assert dg.dimensions["b"].expand is False
        assert dg.dimensions["c"].expand is True
