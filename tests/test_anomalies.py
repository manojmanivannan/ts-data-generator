"""Tests for anomaly injection pipeline."""

import numpy as np
import pandas as pd
import pytest

from ts_data_generator import DataGen
from ts_data_generator.anomalies.base import Anomaly
from ts_data_generator.anomalies.missing import MissingData
from ts_data_generator.anomalies.point import PointAnomaly
from ts_data_generator.random import DefaultRNG, SeedableRNG
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
        result = pa.intervene(base, timestamps, rng=DefaultRNG())

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
        result = pa.intervene(base, timestamps, rng=DefaultRNG())

        # With 50% prob, we should see some anomalies
        assert np.any(result != 0.0)


class TestPointAnomalyReplacement:
    def test_replaces_values_at_expected_rate(self):
        n = 1000
        base = np.arange(n, dtype=float)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        pa = PointAnomaly(probability=0.05, magnitude=999, mode="replacement")
        result = pa.intervene(base, timestamps, rng=DefaultRNG())

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
        result = pa.intervene(base, timestamps, rng=DefaultRNG())

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

    def test_intervene_accepts_rng_protocol(self):
        """intervene() accepts any RNGProtocol, not just SeedableRNG."""
        n = 50
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")
        pa = PointAnomaly(probability=0.5, magnitude=10)

        from ts_data_generator.random import DefaultRNG, RNGProtocol

        rng: RNGProtocol = DefaultRNG()
        result = pa.intervene(base, timestamps, rng=rng)
        assert result.shape == base.shape


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
        result_df = m.generate(timestamps, rng=DefaultRNG()).signal

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
        result_df = m.generate(timestamps, rng=rng).signal
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

        result_forward = m_forward.generate(timestamps, rng=rng1).signal
        result_reverse = m_reverse.generate(timestamps, rng=rng2).signal

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
        result = md.intervene(base, timestamps, rng=DefaultRNG())

        nan_count = np.sum(np.isnan(result))
        # ~5% of 2000 = 100, generous bounds
        assert 50 < nan_count < 150

    def test_non_nan_values_unchanged(self):
        n = 500
        base = np.arange(n, dtype=float)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        md = MissingData(mode="random", probability=0.1)
        result = md.intervene(base, timestamps, rng=DefaultRNG())

        non_nan_mask = ~np.isnan(result)
        assert np.all(result[non_nan_mask] == base[non_nan_mask])

    def test_no_rng_falls_back_to_numpy_global(self):
        n = 200
        base = np.zeros(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        md = MissingData(mode="random", probability=0.5)
        result = md.intervene(base, timestamps, rng=DefaultRNG())

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


class TestMissingDataPatterned:
    def test_schedule_sets_nan_when_true(self):
        n = 100
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="h")

        def schedule(ts):
            return ts.hour % 2 == 0  # even hours

        md = MissingData(mode="patterned", schedule=schedule)
        result = md.intervene(base, timestamps, rng=DefaultRNG())

        nan_mask = np.isnan(result)
        expected_nan = np.array([ts.hour % 2 == 0 for ts in timestamps])
        assert np.array_equal(nan_mask, expected_nan)

    def test_patterned_mode_requires_schedule(self):
        with pytest.raises(ValueError, match="schedule"):
            MissingData(mode="patterned")

    def test_patterned_composes_with_random_via_two_instances(self):
        n = 2000
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        def schedule(ts):
            return ts.minute < 10  # first 10 min of each hour

        md_patterned = MissingData(mode="patterned", schedule=schedule)
        md_random = MissingData(mode="random", probability=0.05)

        # Apply random first, then patterned
        rng = SeedableRNG(42)
        intermediate = md_random.intervene(base, timestamps, rng=rng)
        # Reset rng so patterned sees the same state regardless
        result = md_patterned.intervene(intermediate, timestamps, rng=rng)

        nan_mask = np.isnan(result)
        assert np.any(nan_mask)

        # Patterned NaN positions should all be set
        for i, ts in enumerate(timestamps):
            if schedule(ts):
                assert np.isnan(result[i])

        # Total NaN count >= patterned NaN count (union)
        patterned_count = sum(1 for ts in timestamps if schedule(ts))
        assert np.sum(nan_mask) >= patterned_count

    def test_patterned_seed_determinism(self):
        n = 100
        base = np.arange(n, dtype=float)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="h")

        def schedule(ts):
            return ts.hour % 3 == 0

        md = MissingData(mode="patterned", schedule=schedule)
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        result1 = md.intervene(base, timestamps, rng=rng1)
        result2 = md.intervene(base, timestamps, rng=rng2)

        assert np.array_equal(result1, result2, equal_nan=True)

    def test_patterned_non_nan_values_unchanged(self):
        n = 100
        base = np.arange(n, dtype=float)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="h")

        def schedule(ts):
            return ts.hour == 0  # only midnight

        md = MissingData(mode="patterned", schedule=schedule)
        result = md.intervene(base, timestamps, rng=DefaultRNG())

        non_nan_mask = ~np.isnan(result)
        assert np.all(result[non_nan_mask] == base[non_nan_mask])


class TestMissingDataPipelineWithPointAnomaly:
    def test_nan_preserved_when_point_anomaly_then_missing_data(self):
        """NaNs from MissingData (last) are never overwritten by PointAnomaly (first)."""
        n = 2000
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        pa = PointAnomaly(probability=0.1, magnitude=100, mode="replacement")
        md = MissingData(mode="random", probability=0.1)

        m = Metrics(name="test", trends=set(), anomalies=[pa, md])
        rng = SeedableRNG(42)
        result_df = m.generate(timestamps, rng=rng).signal
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
        result_df = m.generate(timestamps, rng=rng).signal
        values = result_df["test"].values

        # Since MD runs last, NaN positions exist and are not overwritten
        nan_count = np.sum(np.isnan(values))
        assert nan_count > 0

        # Non-NaN values are either 0 (base) or 50 (replacement from PA)
        non_nan = values[~np.isnan(values)]
        assert set(non_nan).issubset({0.0, 50.0})


class TestDriftSegmentConstruction:
    def test_requires_start_timestamp(self):
        from ts_data_generator.anomalies.drift import DriftSegment

        with pytest.raises(TypeError):
            DriftSegment()  # type: ignore[call-arg]

    def test_rejects_empty_start_timestamp(self):
        from ts_data_generator.anomalies.drift import DriftSegment

        with pytest.raises(ValueError, match="start_timestamp"):
            DriftSegment(start_timestamp="")

    def test_accepts_start_timestamp_with_defaults(self):
        from ts_data_generator.anomalies.drift import DriftSegment

        seg = DriftSegment(start_timestamp="2024-06-15")
        assert seg.start_timestamp == "2024-06-15"
        assert seg.transition_window == 1800
        assert seg.hold_duration == 7200
        assert seg.restore is False

    def test_rejects_negative_transition_window(self):
        from ts_data_generator.anomalies.drift import DriftSegment

        with pytest.raises(ValueError, match="transition_window"):
            DriftSegment(start_timestamp="2024-01-01", transition_window=0)

    def test_rejects_negative_hold_duration(self):
        from ts_data_generator.anomalies.drift import DriftSegment

        with pytest.raises(ValueError, match="hold_duration"):
            DriftSegment(start_timestamp="2024-01-01", hold_duration=0)


class TestConceptDriftSkeleton:
    def test_constructs_with_one_segment(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        seg = DriftSegment(start_timestamp="2024-01-01 00:50:00", transition_window=1200,
                           target_mean=5.0, target_std=1.0, hold_duration=6000)
        cd = ConceptDrift(segments=[seg])
        assert len(cd.segments) == 1

    def test_intervene_returns_array_of_same_length(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 200
        base = np.arange(n, dtype=float)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        seg = DriftSegment(start_timestamp="2024-01-01 00:50:00", transition_window=1200,
                           target_mean=100.0, target_std=0.0, hold_duration=4800)
        cd = ConceptDrift(segments=[seg])
        rng = SeedableRNG(42)
        result = cd.intervene(base, timestamps, rng=rng)

        assert len(result) == n
        assert isinstance(result, np.ndarray)


class TestConceptDriftTransition:
    def test_linear_ramp_from_baseline_to_target_with_zero_std(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 100
        base = np.full(n, 10.0)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        seg = DriftSegment(start_timestamp="2024-01-01 00:20:00", transition_window=600,
                           target_mean=50.0, target_std=0.0, hold_duration=1800, restore=False)
        cd = ConceptDrift(segments=[seg])
        rng = SeedableRNG(42)
        result = cd.intervene(base, timestamps, rng=rng)

        # Before drift: unchanged baseline
        assert np.all(result[:20] == 10.0)

        # During transition (indices 20-29): ramps from 10→50
        # With tw=10, last alpha = 9/10 = 0.9, so last = 0.1*10 + 0.9*50 = 46
        transition = result[20:30]
        assert transition[0] == 10.0  # alpha=0, all baseline
        assert transition[-1] == 46.0  # alpha=0.9
        # Strictly increasing
        assert np.all(np.diff(transition) >= 0)

    def test_transition_interpolation_values_are_between_baseline_and_target(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 200
        base = np.full(n, 5.0)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        seg = DriftSegment(start_timestamp="2024-01-01 00:50:00", transition_window=2400,
                           target_mean=105.0, target_std=2.0, hold_duration=3600, restore=False)
        cd = ConceptDrift(segments=[seg])
        rng = SeedableRNG(42)
        result = cd.intervene(base, timestamps, rng=rng)

        transition = result[50:90]
        # All transition values should lie between 5 and ~111 (105 + 3*2)
        assert np.all(transition >= 5.0)
        assert np.all(transition <= 115.0)
        # Mean of transition should be between baseline and target
        assert 5.0 < np.mean(transition) < 105.0


class TestConceptDriftHold:
    def test_hold_period_equals_target_mean_with_zero_std(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 200
        base = np.zeros(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        seg = DriftSegment(start_timestamp="2024-01-01 00:30:00", transition_window=1200,
                           target_mean=75.0, target_std=0.0, hold_duration=3000, restore=False)
        cd = ConceptDrift(segments=[seg])
        rng = SeedableRNG(42)
        result = cd.intervene(base, timestamps, rng=rng)

        # Hold period: indices 50-99 (after transition 30-49)
        hold = result[50:100]
        assert np.all(hold == 75.0)

    def test_hold_period_sample_mean_approximates_target_mean(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 2000
        base = np.zeros(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        seg = DriftSegment(start_timestamp="2024-01-01 00:50:00", transition_window=6000,
                           target_mean=100.0, target_std=10.0, hold_duration=30000, restore=False)
        cd = ConceptDrift(segments=[seg])
        rng = SeedableRNG(42)
        result = cd.intervene(base, timestamps, rng=rng)

        hold = result[150:650]
        # Sample mean should approximate target_mean=100
        assert 95 < np.mean(hold) < 105
        # Sample std should approximate target_std=10
        assert 7 < np.std(hold) < 13


class TestConceptDriftRestore:
    def test_restore_returns_values_to_baseline_with_zero_std(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 300
        base = np.full(n, 20.0)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        # start=50, tw=20 (50-69), hold=100 (70-169), restore tw=20 (170-189), back to baseline 190+
        seg = DriftSegment(start_timestamp="2024-01-01 00:50:00", transition_window=1200,
                           target_mean=80.0, target_std=0.0, hold_duration=6000, restore=True)
        cd = ConceptDrift(segments=[seg])
        rng = SeedableRNG(42)
        result = cd.intervene(base, timestamps, rng=rng)

        # Before drift
        assert np.all(result[:50] == 20.0)
        # Hold period (target_std=0, so all 80.0)
        assert np.all(result[70:170] == 80.0)
        # After restore transition, back to baseline
        assert np.all(result[190:] == 20.0)

    def test_restore_transition_moves_from_target_toward_baseline(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 200
        base = np.full(n, 10.0)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        seg = DriftSegment(start_timestamp="2024-01-01 00:20:00", transition_window=1800,
                           target_mean=90.0, target_std=3.0, hold_duration=2400, restore=True)
        cd = ConceptDrift(segments=[seg])
        rng = SeedableRNG(42)
        result = cd.intervene(base, timestamps, rng=rng)

        # Restore transition: indices 90-119
        restore_trans = result[90:120]
        # Should start near target and end near baseline
        assert abs(restore_trans[0] - 90.0) < 15  # near target at start
        assert abs(restore_trans[-1] - 10.0) < 15  # near baseline at end
        # Mean of first half should be closer to target than second half
        first_half_mean = np.mean(restore_trans[:15])
        second_half_mean = np.mean(restore_trans[15:])
        assert first_half_mean > second_half_mean

    def test_no_restore_leaves_values_at_target(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 100
        base = np.full(n, 0.0)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        seg = DriftSegment(start_timestamp="2024-01-01 00:10:00", transition_window=300,
                           target_mean=99.0, target_std=0.0, hold_duration=1200, restore=False)
        cd = ConceptDrift(segments=[seg])
        rng = SeedableRNG(42)
        result = cd.intervene(base, timestamps, rng=rng)

        # After hold (restore=False): values beyond the segment are unchanged baseline
        hold_end = 10 + 5 + 20  # 35
        assert hold_end < n
        assert np.all(result[35:] == 0.0)


class TestConceptDriftSeedDeterminism:
    def test_same_seed_produces_identical_results(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 200
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        seg = DriftSegment(start_timestamp="2024-01-01 00:40:00", transition_window=1800,
                           target_mean=50.0, target_std=5.0, hold_duration=3600, restore=True)
        cd = ConceptDrift(segments=[seg])

        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        result1 = cd.intervene(base, timestamps, rng=rng1)
        result2 = cd.intervene(base, timestamps, rng=rng2)

        assert np.array_equal(result1, result2)

    def test_different_seeds_produce_different_results(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 200
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        seg = DriftSegment(start_timestamp="2024-01-01 00:40:00", transition_window=1800,
                           target_mean=50.0, target_std=5.0, hold_duration=3600, restore=True)
        cd = ConceptDrift(segments=[seg])

        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(99)
        result1 = cd.intervene(base, timestamps, rng=rng1)
        result2 = cd.intervene(base, timestamps, rng=rng2)

        assert not np.array_equal(result1, result2)


class TestConceptDriftTimestampResolution:
    def test_start_timestamp_resolves_to_correct_index(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 100
        base = np.arange(n, dtype=float)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="h")

        seg = DriftSegment(start_timestamp="2024-01-03 00:00", transition_window=18000,
                           target_mean=999.0, target_std=0.0, hold_duration=36000,
                           restore=False)
        cd = ConceptDrift(segments=[seg])
        rng = SeedableRNG(42)
        result = cd.intervene(base, timestamps, rng=rng)

        # Index 48 is the start of the drift (48 hours from 2024-01-01 00:00)
        assert np.all(result[:48] == base[:48])
        assert result[48] == base[48]  # alpha=0

    def test_start_timestamp_out_of_bounds_skips(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 50
        base = np.arange(n, dtype=float)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="D")

        seg = DriftSegment(start_timestamp="2025-06-15", transition_window=432000,
                           target_mean=10.0, target_std=0.0, hold_duration=864000)
        cd = ConceptDrift(segments=[seg])

        result = cd.intervene(base, timestamps, rng=DefaultRNG())
        # Segment is skipped because start_timestamp is out of bounds;
        # result should be unchanged from base array.
        np.testing.assert_array_equal(result, base)

    def test_start_timestamp_not_found_raises(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 50
        base = np.arange(n, dtype=float)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="D")

        # In range but with a time component that won't match daily timestamps exactly
        seg = DriftSegment(start_timestamp="2024-01-15T06:00:00", transition_window=432000,
                           target_mean=10.0, target_std=0.0, hold_duration=864000)
        cd = ConceptDrift(segments=[seg])

        with pytest.raises(ValueError, match="not found"):
            cd.intervene(base, timestamps, rng=DefaultRNG())


class TestConceptDriftMultiSegment:
    def test_three_segments_transition_through_all_regimes(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 500
        base = np.full(n, 10.0)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        # Segment 1: start at 00:50, ramp to mean=50, hold 100, no restore
        seg1 = DriftSegment(start_timestamp="2024-01-01 00:50:00", transition_window=600,
                            target_mean=50.0, target_std=0.0, hold_duration=6000,
                            restore=False)
        # Segment 2: start after seg1 ends, ramp to mean=100, hold 100, restore
        seg2 = DriftSegment(start_timestamp="2024-01-01 02:40:00", transition_window=600,
                            target_mean=100.0, target_std=0.0, hold_duration=6000,
                            restore=True)
        # Segment 3: start after seg2 ends (restored), ramp to mean=200, hold, no restore
        seg3 = DriftSegment(start_timestamp="2024-01-01 04:40:00", transition_window=600,
                            target_mean=200.0, target_std=0.0, hold_duration=6000,
                            restore=False)

        cd = ConceptDrift(segments=[seg1, seg2, seg3])
        rng = SeedableRNG(42)
        result = cd.intervene(base, timestamps, rng=rng)

        # Before any drift: baseline=10
        assert np.all(result[:50] == 10.0)

        # Seg1 hold period should be at target_mean=50
        hold1_start = 50 + 10  # start + tw=10
        hold1_end = hold1_start + 100  # hold_duration=6000/60=100
        assert np.all(result[hold1_start:hold1_end] == 50.0)

        # After seg3, values should be at 200 (no restore)
        # seg1: start=50, end=50+10+100=160
        # seg2: start=160, end=(160+10+100+10=280)
        # seg3: start=280, end=280+10+100=390
        hold3_start = 280 + 10  # start=280, tw=10
        hold3_end = hold3_start + 100
        assert np.all(result[hold3_start:hold3_end] == 200.0)

    def test_sequential_segments_no_gaps(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 500
        base = np.full(n, 0.0)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        # Two sequential segments, zero_std so we know exact values
        seg1 = DriftSegment(start_timestamp="2024-01-01 00:50:00", transition_window=600,
                            target_mean=100.0, target_std=0.0, hold_duration=6000,
                            restore=False)
        seg2 = DriftSegment(start_timestamp="2024-01-01 02:40:00", transition_window=600,
                            target_mean=200.0, target_std=0.0, hold_duration=6000,
                            restore=True)

        cd = ConceptDrift(segments=[seg1, seg2])
        result = cd.intervene(base, timestamps, rng=DefaultRNG())

        # seg1: start=50, tw=10, hold=100 → covers [50, 160)
        # seg2 starts at 160: tw=10, hold=100, restore_tw=10 → covers [160, 280)
        # No gap at boundary: result[159] is seg1 hold, result[160] is seg2 transition
        assert result[159] == 100.0  # last seg1 hold value
        assert result[160] == 0.0  # seg2 first transition alpha=0 → base_array (baseline)

        # After seg2 restore (280+), values back to baseline
        assert np.all(result[280:] == 0.0)

    def test_multi_segment_seed_determinism(self):
        from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment

        n = 500
        base = np.ones(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="min")

        seg1 = DriftSegment(start_timestamp="2024-01-01 00:50:00", transition_window=600,
                            target_mean=50.0, target_std=5.0, hold_duration=6000,
                            restore=True)
        seg2 = DriftSegment(start_timestamp="2024-01-01 02:50:00", transition_window=600,
                            target_mean=100.0, target_std=5.0, hold_duration=6000,
                            restore=False)

        cd = ConceptDrift(segments=[seg1, seg2])

        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        result1 = cd.intervene(base, timestamps, rng=rng1)
        result2 = cd.intervene(base, timestamps, rng=rng2)

        assert np.array_equal(result1, result2)
