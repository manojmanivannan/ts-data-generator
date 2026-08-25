"""Tests for multi-series metric scaling under dimension expansion.

When expand_dimensions=True, metric series across different dimension
combinations can be scaled differently via:
1. Explicit per-dimension weights: e.g. weights={"US": 5.0, "EU": 2.0}
2. Direct dict dimension specification: e.g. {"enterprise": 10.0, "basic": 1.0}
3. Linked dimension tuple weights: e.g. weights={("NYC", "NY"): 3.0}
4. Stochastic auto-scaling via scale_variance (e.g. scale_variance=0.5)
5. Multiplicative composition of multiple dimension weights and variance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ts_data_generator import DataGen
from ts_data_generator.anomalies.point import PointAnomaly
from ts_data_generator.schema.models import AggregationType, Granularity
from ts_data_generator.utils.functions import ordered_choice, random_choice
from ts_data_generator.utils.trends import LinearTrend, SinusoidalTrend


class TestExplicitDimensionWeights:
    def test_single_dimension_explicit_weights(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension(
            "region",
            ordered_choice(["US", "EU"]),
            weights={"US": 5.0, "EU": 2.0},
        )
        dg.add_metric("sales", {LinearTrend(offset=10, slope=0, noise_level=0)})

        df = dg.data
        us_sales = df[df["region"] == "US"]["sales"].to_numpy()
        eu_sales = df[df["region"] == "EU"]["sales"].to_numpy()

        # US baseline: 10 * 5 = 50. EU baseline: 10 * 2 = 20.
        np.testing.assert_allclose(us_sales, [50.0, 50.0, 50.0])
        np.testing.assert_allclose(eu_sales, [20.0, 20.0, 20.0])

    def test_dict_as_dimension_function(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        # Passing a dict directly: keys become the domain, values become weights
        dg.add_dimension("tier", {"enterprise": 10.0, "pro": 3.0, "basic": 1.0})
        dg.add_metric("mrr", {LinearTrend(offset=100, slope=0, noise_level=0)})

        df = dg.data
        assert set(df["tier"]) == {"enterprise", "pro", "basic"}
        ent_mrr = df[df["tier"] == "enterprise"]["mrr"].to_numpy()
        pro_mrr = df[df["tier"] == "pro"]["mrr"].to_numpy()
        bas_mrr = df[df["tier"] == "basic"]["mrr"].to_numpy()

        np.testing.assert_allclose(ent_mrr, [1000.0, 1000.0, 1000.0])
        np.testing.assert_allclose(pro_mrr, [300.0, 300.0, 300.0])
        np.testing.assert_allclose(bas_mrr, [100.0, 100.0, 100.0])

    def test_multi_dimension_multiplicative_weights(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-02",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", ordered_choice(["US", "EU"]), weights={"US": 4.0, "EU": 2.0})
        dg.add_dimension("env", ordered_choice(["prod", "dev"]), weights={"prod": 3.0, "dev": 1.0})
        dg.add_metric("load", {LinearTrend(offset=10, slope=0, noise_level=0)})

        df = dg.data
        # (US, prod): 10 * 4 * 3 = 120
        # (US, dev):  10 * 4 * 1 = 40
        # (EU, prod): 10 * 2 * 3 = 60
        # (EU, dev):  10 * 2 * 1 = 20
        us_prod = df[(df["region"] == "US") & (df["env"] == "prod")]["load"].to_numpy()
        us_dev = df[(df["region"] == "US") & (df["env"] == "dev")]["load"].to_numpy()
        eu_prod = df[(df["region"] == "EU") & (df["env"] == "prod")]["load"].to_numpy()
        eu_dev = df[(df["region"] == "EU") & (df["env"] == "dev")]["load"].to_numpy()

        np.testing.assert_allclose(us_prod, [120.0, 120.0])
        np.testing.assert_allclose(us_dev, [40.0, 40.0])
        np.testing.assert_allclose(eu_prod, [60.0, 60.0])
        np.testing.assert_allclose(eu_dev, [20.0, 20.0])

    def test_partial_weights_default_to_one(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-02",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        # Only US is weighted; EU defaults to 1.0
        dg.add_dimension("region", ordered_choice(["US", "EU"]), weights={"US": 3.0})
        dg.add_metric("val", {LinearTrend(offset=10, slope=0, noise_level=0)})

        df = dg.data
        us_val = df[df["region"] == "US"]["val"].to_numpy()
        eu_val = df[df["region"] == "EU"]["val"].to_numpy()

        np.testing.assert_allclose(us_val, [30.0, 30.0])
        np.testing.assert_allclose(eu_val, [10.0, 10.0])


class TestMultiItemsDimensionWeights:
    def test_linked_dimensions_weights(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-02",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_multi_items(
            names=["city", "state"],
            function=[("NYC", "NY"), ("SFO", "CA")],
            weights={("NYC", "NY"): 4.0, ("SFO", "CA"): 2.0},
        )
        dg.add_metric("sales", {LinearTrend(offset=10, slope=0, noise_level=0)})

        df = dg.data
        nyc_sales = df[df["city"] == "NYC"]["sales"].to_numpy()
        sfo_sales = df[df["city"] == "SFO"]["sales"].to_numpy()

        np.testing.assert_allclose(nyc_sales, [40.0, 40.0])
        np.testing.assert_allclose(sfo_sales, [20.0, 20.0])

    def test_linked_and_scalar_dimension_weights_compose(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-02",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("tier", ordered_choice(["gold", "silver"]), weights={"gold": 2.0, "silver": 1.0})
        dg.add_multi_items(
            names=["city", "state"],
            function=[("NYC", "NY"), ("SFO", "CA")],
            weights={("NYC", "NY"): 5.0, ("SFO", "CA"): 3.0},
        )
        dg.add_metric("rev", {LinearTrend(offset=10, slope=0, noise_level=0)})

        df = dg.data
        # (gold, NYC): 10 * 2 * 5 = 100
        # (gold, SFO): 10 * 2 * 3 = 60
        # (silver, NYC): 10 * 1 * 5 = 50
        # (silver, SFO): 10 * 1 * 3 = 30
        gold_nyc = df[(df["tier"] == "gold") & (df["city"] == "NYC")]["rev"].to_numpy()
        gold_sfo = df[(df["tier"] == "gold") & (df["city"] == "SFO")]["rev"].to_numpy()
        silver_nyc = df[(df["tier"] == "silver") & (df["city"] == "NYC")]["rev"].to_numpy()
        silver_sfo = df[(df["tier"] == "silver") & (df["city"] == "SFO")]["rev"].to_numpy()

        np.testing.assert_allclose(gold_nyc, [100.0, 100.0])
        np.testing.assert_allclose(gold_sfo, [60.0, 60.0])
        np.testing.assert_allclose(silver_nyc, [50.0, 50.0])
        np.testing.assert_allclose(silver_sfo, [30.0, 30.0])


class TestStochasticScaleVariance:
    def test_scale_variance_differentiates_slices_with_zero_noise(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
            scale_variance=0.5,
        )
        dg.add_dimension("region", ordered_choice(["US", "EU", "APAC"]))
        dg.add_metric("sales", {LinearTrend(offset=100, slope=0, noise_level=0)})

        df = dg.data
        us_sales = df[df["region"] == "US"]["sales"].to_numpy()
        eu_sales = df[df["region"] == "EU"]["sales"].to_numpy()
        apac_sales = df[df["region"] == "APAC"]["sales"].to_numpy()

        # Each slice is a flat line (slope=0, noise=0), but at distinct scales!
        assert len(set(us_sales)) == 1
        assert len(set(eu_sales)) == 1
        assert len(set(apac_sales)) == 1

        # The three baseline levels must be distinct
        scales = {us_sales[0], eu_sales[0], apac_sales[0]}
        assert len(scales) == 3

    def test_scale_variance_determinism(self) -> None:
        def build(seed: int) -> DataGen:
            dg = DataGen(
                start_datetime="2024-01-01",
                end_datetime="2024-01-03",
                granularity=Granularity.DAILY,
                seed=seed,
                expand_dimensions=True,
                scale_variance=0.5,
            )
            dg.add_dimension("region", ordered_choice(["US", "EU"]))
            dg.add_metric("sales", {LinearTrend(offset=100, slope=1, noise_level=0)})
            return dg

        # Same seed produces exact same scaled DataFrame
        pd.testing.assert_frame_equal(build(42).data, build(42).data)

        # Different seed produces different scales
        assert not build(42).data["sales"].equals(build(99).data["sales"])

    def test_scale_variance_composes_with_explicit_weights(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
            scale_variance=0.3,
        )
        dg.add_dimension("region", ordered_choice(["US", "EU"]), weights={"US": 10.0, "EU": 1.0})
        dg.add_metric("sales", {LinearTrend(offset=10, slope=0, noise_level=0)})

        df = dg.data
        us_sales = df[df["region"] == "US"]["sales"].to_numpy()
        eu_sales = df[df["region"] == "EU"]["sales"].to_numpy()

        # US is roughly ~10x EU (scaled by 10 * stochastic_factor_us vs 1 * stochastic_factor_eu)
        assert us_sales[0] > eu_sales[0] * 3.0


class TestAnomalyLabelsWithScaling:
    def test_anomaly_labels_match_scaled_baseline_deviations(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-05",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", ordered_choice(["US", "EU"]), weights={"US": 5.0, "EU": 2.0})
        dg.add_metric(
            "cpu",
            {LinearTrend(offset=10, slope=0, noise_level=0)},
            anomalies=[PointAnomaly(probability=0.5, magnitude=50, mode="additive")],
        )

        df = dg.data
        assert "cpu_anomaly" in df.columns
        assert df["cpu_anomaly"].dtype == bool

        # US baseline is 10 * 5 = 50. EU baseline is 10 * 2 = 20.
        us_group = df[df["region"] == "US"]
        eu_group = df[df["region"] == "EU"]

        us_deviated = us_group["cpu"].to_numpy() != 50.0
        eu_deviated = eu_group["cpu"].to_numpy() != 20.0

        np.testing.assert_array_equal(us_group["cpu_anomaly"].to_numpy(), us_deviated)
        np.testing.assert_array_equal(eu_group["cpu_anomaly"].to_numpy(), eu_deviated)


class TestLinkedMetricsScaling:
    def test_linked_metrics_scaled_by_combination_scale(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-02",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", ordered_choice(["US", "EU"]), weights={"US": 3.0, "EU": 1.0})

        def fixed_pairs():
            while True:
                yield (10.0, 20.0)

        dg.add_multi_items(
            names=["m1", "m2"],
            function=fixed_pairs(),
            aggregation_type=[AggregationType.SUM, AggregationType.AVG],
        )

        df = dg.data
        us = df[df["region"] == "US"]
        eu = df[df["region"] == "EU"]

        # US (3x): m1 = 30, m2 = 60
        np.testing.assert_allclose(us["m1"].to_numpy(), [30.0, 30.0])
        np.testing.assert_allclose(us["m2"].to_numpy(), [60.0, 60.0])

        # EU (1x): m1 = 10, m2 = 20
        np.testing.assert_allclose(eu["m1"].to_numpy(), [10.0, 10.0])
        np.testing.assert_allclose(eu["m2"].to_numpy(), [20.0, 20.0])


class TestAggregationWithScaling:
    def test_aggregation_aggregates_scaled_values_per_combination(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01 00:00:00",
            end_datetime="2024-01-01 03:00:00",
            granularity=Granularity.HOURLY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", ordered_choice(["US", "EU"]), weights={"US": 2.0, "EU": 1.0})
        dg.add_metric(
            "sales",
            {LinearTrend(offset=10, slope=0, noise_level=0)},
            aggregation_type=AggregationType.SUM,
        )

        agg = dg.aggregate("D")
        us_agg = agg[agg["region"] == "US"]["sales"].values[0]
        eu_agg = agg[agg["region"] == "EU"]["sales"].values[0]

        # US: 4 hours x 20 = 80 (SUM)
        # EU: 4 hours x 10 = 40 (SUM)
        assert us_agg == 80.0
        assert eu_agg == 40.0


class TestBackwardsCompatibility:
    def test_default_scale_variance_is_zero(self) -> None:
        dg = DataGen()
        assert dg.scale_variance == 0.0

    def test_no_weights_and_zero_variance_unaltered(self) -> None:
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
            expand_dimensions=True,
        )
        dg.add_dimension("region", ordered_choice(["US", "EU"]))
        dg.add_metric("sales", {LinearTrend(offset=10, slope=0, noise_level=0)})

        df = dg.data
        us_sales = df[df["region"] == "US"]["sales"].to_numpy()
        eu_sales = df[df["region"] == "EU"]["sales"].to_numpy()

        np.testing.assert_allclose(us_sales, [10.0, 10.0, 10.0])
        np.testing.assert_allclose(eu_sales, [10.0, 10.0, 10.0])
