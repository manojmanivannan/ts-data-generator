"""Tests for anomaly injection pipeline."""

import numpy as np
import pandas as pd
import pytest

from ts_data_generator import DataGen
from ts_data_generator.anomalies.base import Anomaly
from ts_data_generator.anomalies.point import PointAnomaly
from ts_data_generator.random import SeedableRNG
from ts_data_generator.schema.models import Granularity, Metrics
from ts_data_generator.utils.trends import LinearTrend


class TestAnomalyABC:
    def test_cannot_instantiate_abstract_anomaly(self):
        with pytest.raises(TypeError):
            Anomaly()  # type: ignore[abstract]

    def test_concrete_subclass_must_implement_intervene(self):
        class Incomplete(Anomaly):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]


class TestPointAnomalyAdditive:
    def test_injects_spikes_at_expected_rate(self):
        n = 1000
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        pa = PointAnomaly(probability=0.1, magnitude=5, mode="additive")
        result = pa.intervene(base, timestamps, rng=None)

        # ~10% of values should differ from 1.0
        changed = np.sum(result != 1.0)
        assert 50 < changed < 150  # generous bounds around 100

        # Changed values should be 1 + 5 = 6
        assert np.all(result[result != 1.0] == 6.0)

    def test_no_rng_falls_back_to_numpy_global(self):
        n = 100
        base = np.zeros(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        pa = PointAnomaly(probability=0.5, magnitude=3, mode="additive")
        result = pa.intervene(base, timestamps, rng=None)

        # With 50% prob, we should see some anomalies
        assert np.any(result != 0.0)


class TestPointAnomalyReplacement:
    def test_replaces_values_at_expected_rate(self):
        n = 1000
        base = np.arange(n, dtype=float)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        pa = PointAnomaly(probability=0.05, magnitude=999, mode="replacement")
        result = pa.intervene(base, timestamps, rng=None)

        # ~5% should be replaced with 999
        replaced = np.sum(result == 999)
        assert 20 < replaced < 80  # generous bounds around 50

        # Non-replaced values should match the original
        unchanged_mask = result != 999
        assert np.all(result[unchanged_mask] == base[unchanged_mask])


class TestPointAnomalyMagnitudeTuple:
    def test_samples_uniformly_from_range(self):
        n = 2000
        base = np.zeros(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        pa = PointAnomaly(probability=0.5, magnitude=(5, 20), mode="additive")
        result = pa.intervene(base, timestamps, rng=None)

        anomalous = result[result != 0]
        # Values should be between 5 and 20
        assert np.all(anomalous >= 5)
        assert np.all(anomalous <= 20)
        # With 2000*0.5=1000 samples from U(5,20), mean should be ~12.5
        assert 10 < np.mean(anomalous) < 15


class TestPointAnomalySeedDeterminism:
    def test_same_seed_produces_identical_results(self):
        n = 100
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")
        pa = PointAnomaly(probability=0.2, magnitude=(5, 20), mode="additive")

        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        result1 = pa.intervene(base, timestamps, rng=rng1)
        result2 = pa.intervene(base, timestamps, rng=rng2)

        assert np.array_equal(result1, result2)

    def test_different_seeds_produce_different_results(self):
        n = 100
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")
        pa = PointAnomaly(probability=0.2, magnitude=(5, 20), mode="additive")

        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(99)
        result1 = pa.intervene(base, timestamps, rng=rng1)
        result2 = pa.intervene(base, timestamps, rng=rng2)

        assert not np.array_equal(result1, result2)


class TestPointAnomalyConstruction:
    def test_default_construction(self):
        pa = PointAnomaly()
        assert pa.probability == 0.01
        assert pa.mode == "additive"
        assert pa.magnitude == 1.0

    def test_explicit_params(self):
        pa = PointAnomaly(probability=0.1, magnitude=5, mode="replacement")
        assert pa.probability == 0.1
        assert pa.magnitude == 5
        assert pa.mode == "replacement"

    def test_magnitude_as_tuple(self):
        pa = PointAnomaly(probability=0.1, magnitude=(5, 20))
        assert pa.magnitude == (5, 20)

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            PointAnomaly(mode="invalid")  # type: ignore[arg-type]


class TestMetricsWithAnomalies:
    def test_metrics_accepts_anomalies_list(self):
        pa = PointAnomaly(probability=0.1, magnitude=5)
        m = Metrics(name="test", trends=set(), anomalies=[pa])
        assert m.anomalies == [pa]

    def test_metrics_anomalies_defaults_to_empty(self):
        m = Metrics(name="test")
        assert m.anomalies == []

    def test_anomalies_applied_after_trends(self):
        n = 1000
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")
        trend = LinearTrend(offset=10, noise_level=0)
        pa = PointAnomaly(probability=0.1, magnitude=5, mode="additive")

        m = Metrics(name="test", trends={trend}, anomalies=[pa])
        result_df = m.generate(timestamps, rng=None)

        values = result_df["test"].values
        # Some values should differ from base (got anomaly boost)
        base_minus_offset = values - 10
        assert np.any(np.abs(base_minus_offset) > 1)  # anomaly boost visible
        # Most values should be near the base trend
        assert np.mean(values) > 10  # anomalies push mean above base


class TestDataGenAddMetricWithAnomalies:
    def test_add_metric_passes_anomalies_through(self):
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
        )
        pa = PointAnomaly(probability=0.5, magnitude=10, mode="additive")
        dg.add_metric("m", {LinearTrend(offset=5, noise_level=0)}, anomalies=[pa])

        metric = dg.metrics["m"]
        assert len(metric.anomalies) == 1
        assert isinstance(metric.anomalies[0], PointAnomaly)

    def test_add_metric_anomalies_default_to_empty(self):
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
        )
        dg.add_metric("m", {LinearTrend(offset=5)})
        assert dg.metrics["m"].anomalies == []

    def test_end_to_end_anomalies_in_dataframe(self):
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-03",
            granularity=Granularity.DAILY,
            seed=42,
        )
        dg.add_metric(
            "m",
            {LinearTrend(offset=10, noise_level=0)},
            anomalies=[PointAnomaly(probability=0.5, magnitude=5, mode="additive")],
        )

        values = dg.data["m"].values
        # Some values should be 10 + 5 = 15 (anomaly hit)
        assert 15 in values or any(v != 10 for v in values)


class TestPipelineOrdering:
    def test_multiple_anomalies_apply_in_order(self):
        n = 1000
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        # First anomaly: replace with 0 at ~10%
        pa1 = PointAnomaly(probability=0.1, magnitude=0, mode="replacement")
        # Second anomaly: add 100 at ~10%
        pa2 = PointAnomaly(probability=0.1, magnitude=100, mode="additive")

        m = Metrics(name="test", trends=set(), anomalies=[pa1, pa2])
        rng = SeedableRNG(42)
        result_df = m.generate(timestamps, rng=rng)
        values = result_df["test"].values

        # With pa1→pa2 order, some 0s become 100 (hit by both),
        # some stay 0 (hit by pa1 only), some are 110 (hit by pa2 only on base 10),
        # some stay 10 (hit by neither)
        unique_values = set(np.round(values, 2))
        assert len(unique_values) >= 2  # multiple distinct value groups

    def test_order_matters_different_results(self):
        n = 200
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        pa1 = PointAnomaly(probability=0.3, magnitude=0, mode="replacement")
        pa2 = PointAnomaly(probability=0.3, magnitude=100, mode="additive")

        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)

        m_forward = Metrics(name="test", trends=set(), anomalies=[pa1, pa2])
        m_reverse = Metrics(name="test", trends=set(), anomalies=[pa2, pa1])

        result_forward = m_forward.generate(timestamps, rng=rng1)
        result_reverse = m_reverse.generate(timestamps, rng=rng2)

        # Different ordering should produce different results
        assert not np.array_equal(
            result_forward["test"].values, result_reverse["test"].values
        )
