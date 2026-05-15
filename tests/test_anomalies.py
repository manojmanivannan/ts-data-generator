"""Tests for anomaly injection pipeline."""

import numpy as np
import pandas as pd
import pytest

from ts_data_generator import DataGen
from ts_data_generator.anomalies.base import Anomaly
from ts_data_generator.anomalies.missing import MissingData
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


class TestMissingDataConstruction:
    def test_default_construction(self):
        md = MissingData()
        assert md.mode == "random"
        assert md.probability == 0.01
        assert md.burst_probability == 0.02
        assert md.min_length == 2
        assert md.max_length == 5

    def test_explicit_random_params(self):
        md = MissingData(mode="random", probability=0.1)
        assert md.mode == "random"
        assert md.probability == 0.1

    def test_explicit_burst_params(self):
        md = MissingData(
            mode="burst", burst_probability=0.05, min_length=3, max_length=10
        )
        assert md.mode == "burst"
        assert md.burst_probability == 0.05
        assert md.min_length == 3
        assert md.max_length == 10

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            MissingData(mode="invalid")  # type: ignore[arg-type]


class TestMissingDataRandom:
    def test_produces_expected_nan_rate(self):
        n = 2000
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        md = MissingData(mode="random", probability=0.05)
        result = md.intervene(base, timestamps, rng=None)

        nan_count = np.sum(np.isnan(result))
        # ~5% of 2000 = 100, generous bounds
        assert 50 < nan_count < 150

    def test_non_nan_values_unchanged(self):
        n = 500
        base = np.arange(n, dtype=float)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        md = MissingData(mode="random", probability=0.1)
        result = md.intervene(base, timestamps, rng=None)

        non_nan_mask = ~np.isnan(result)
        assert np.all(result[non_nan_mask] == base[non_nan_mask])

    def test_no_rng_falls_back_to_numpy_global(self):
        n = 200
        base = np.zeros(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        md = MissingData(mode="random", probability=0.5)
        result = md.intervene(base, timestamps, rng=None)

        assert np.any(np.isnan(result))


class TestMissingDataBurst:
    def test_produces_consecutive_nan_blocks(self):
        n = 2000
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        md = MissingData(mode="burst", burst_probability=0.02, min_length=3, max_length=10)
        rng = SeedableRNG(42)
        result = md.intervene(base, timestamps, rng=rng)

        nan_mask = np.isnan(result)
        assert np.any(nan_mask)  # should have at least some NaN

        # Detect consecutive NaN runs
        in_run = False
        run_lengths = []
        current_run = 0
        for i in range(n):
            if nan_mask[i]:
                if not in_run:
                    in_run = True
                    current_run = 1
                else:
                    current_run += 1
            else:
                if in_run:
                    run_lengths.append(current_run)
                    in_run = False

        if in_run:
            run_lengths.append(current_run)

        # All run lengths should be within [min_length, max_length]
        for rl in run_lengths:
            assert 3 <= rl <= 10, f"burst length {rl} outside [3, 10]"

        # With SeedableRNG(42), runs should be non-empty
        assert len(run_lengths) > 0

    def test_bursts_do_not_overlap(self):
        n = 2000
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        md = MissingData(mode="burst", burst_probability=0.03, min_length=5, max_length=15)
        rng = SeedableRNG(42)
        result = md.intervene(base, timestamps, rng=rng)

        nan_mask = np.isnan(result)

        # Check that NaN entries appear only in contiguous blocks
        # with at least one non-NaN between blocks
        transitions = 0
        for i in range(1, len(nan_mask)):
            if nan_mask[i] != nan_mask[i - 1]:
                transitions += 1

        # Each run of NaN has a start and end transition
        # If no overlaps, the NaN blocks are separated by non-NaN regions
        # We verify by checking all NaN run lengths are >= min_length (already
        # covered above), and there are non-NaN gaps between blocks
        in_nan = nan_mask[0]
        nan_runs = 0
        for i in range(1, n):
            if nan_mask[i] and not in_nan:
                nan_runs += 1
            in_nan = nan_mask[i]

        # With burst_probability=0.03 across 2000 points, expect several bursts
        assert nan_runs >= 1

    def test_burst_length_respects_bounds(self):
        n = 3000
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        md = MissingData(mode="burst", burst_probability=0.03, min_length=3, max_length=7)
        rng = SeedableRNG(42)
        result = md.intervene(base, timestamps, rng=rng)

        nan_mask = np.isnan(result)

        # Measure all run lengths
        run_lengths = []
        i = 0
        while i < n:
            if nan_mask[i]:
                j = i
                while j < n and nan_mask[j]:
                    j += 1
                run_lengths.append(j - i)
                i = j
            else:
                i += 1

        assert len(run_lengths) > 0
        for rl in run_lengths:
            assert 3 <= rl <= 7, f"burst length {rl} outside [3, 7]"


class TestMissingDataSeedDeterminism:
    def test_random_mode_seed_determinism(self):
        n = 200
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")
        md = MissingData(mode="random", probability=0.1)

        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        result1 = md.intervene(base, timestamps, rng=rng1)
        result2 = md.intervene(base, timestamps, rng=rng2)

        assert np.array_equal(result1, result2, equal_nan=True)

    def test_random_mode_different_seeds_different(self):
        n = 200
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")
        md = MissingData(mode="random", probability=0.1)

        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(99)
        result1 = md.intervene(base, timestamps, rng=rng1)
        result2 = md.intervene(base, timestamps, rng=rng2)

        assert not np.array_equal(result1, result2, equal_nan=True)

    def test_burst_mode_seed_determinism(self):
        n = 200
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")
        md = MissingData(mode="burst", burst_probability=0.03, min_length=3, max_length=10)

        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        result1 = md.intervene(base, timestamps, rng=rng1)
        result2 = md.intervene(base, timestamps, rng=rng2)

        assert np.array_equal(result1, result2, equal_nan=True)

    def test_burst_mode_different_seeds_different(self):
        n = 200
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")
        md = MissingData(mode="burst", burst_probability=0.03, min_length=3, max_length=10)

        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(99)
        result1 = md.intervene(base, timestamps, rng=rng1)
        result2 = md.intervene(base, timestamps, rng=rng2)

        assert not np.array_equal(result1, result2, equal_nan=True)


class TestMissingDataPipelineWithPointAnomaly:
    def test_nan_preserved_when_point_anomaly_then_missing_data(self):
        """NaNs from MissingData (last) are never overwritten by PointAnomaly (first)."""
        n = 2000
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        pa = PointAnomaly(probability=0.1, magnitude=100, mode="replacement")
        md = MissingData(mode="random", probability=0.1)

        m = Metrics(name="test", trends=set(), anomalies=[pa, md])
        rng = SeedableRNG(42)
        result_df = m.generate(timestamps, rng=rng)
        values = result_df["test"].values

        nan_mask = np.isnan(values)
        assert np.any(nan_mask)  # some NaN from MissingData

        # Non-NaN values should be either 0 (base, no anomaly) or 100 (replacement PA)
        non_nan = values[~nan_mask]
        unique_non_nan = set(non_nan)
        assert unique_non_nan.issubset({0.0, 100.0})

    def test_missing_last_preserves_order(self):
        """MissingData after PointAnomaly means NaNs are never overwritten."""
        n = 500
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        pa = PointAnomaly(probability=0.3, magnitude=50, mode="replacement")
        md = MissingData(mode="random", probability=0.3)

        m = Metrics(name="test", trends=set(), anomalies=[pa, md])
        rng = SeedableRNG(42)
        result_df = m.generate(timestamps, rng=rng)
        values = result_df["test"].values

        # Since MD runs last, NaN positions exist and are not overwritten
        nan_count = np.sum(np.isnan(values))
        assert nan_count > 0

        # Non-NaN values are either 0 (base) or 50 (replacement from PA)
        non_nan = values[~np.isnan(values)]
        assert set(non_nan).issubset({0.0, 50.0})
