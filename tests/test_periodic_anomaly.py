"""Tests for the periodic burst anomaly and its shared event schedule."""

import numpy as np
import pandas as pd
import pytest

from ts_data_generator import DataGen
from ts_data_generator.anomalies import EventSchedule, PeriodicBurstAnomaly
from ts_data_generator.random import DefaultRNG, SeedableRNG
from ts_data_generator.utils.trends import LinearTrend


class TestEventScheduleConstruction:
    def test_default_construction(self):
        sched = EventSchedule(period=100)
        assert sched.period == 100
        assert sched.windows == []

    def test_rejects_non_positive_period(self):
        with pytest.raises(ValueError):
            EventSchedule(period=0)

    def test_rejects_invalid_skip_probability(self):
        with pytest.raises(ValueError):
            EventSchedule(period=10, skip_probability=1.5)

    def test_rejects_small_max_skip_periods(self):
        with pytest.raises(ValueError):
            EventSchedule(period=10, max_skip_periods=1)

    def test_rejects_negative_jitter(self):
        with pytest.raises(ValueError):
            EventSchedule(period=10, jitter=-1)

    def test_rejects_negative_phase(self):
        with pytest.raises(ValueError):
            EventSchedule(period=10, phase=-1)


class TestEventScheduleBuild:
    def test_fixed_period_produces_evenly_spaced_windows(self):
        sched = EventSchedule(period=100, duration=20, phase=250)
        rng = SeedableRNG(0)
        mask = sched.build(n=1000, rng=rng)

        starts = [s for s, _ in sched.windows]
        assert starts == [250, 350, 450, 550, 650, 750, 850, 950]
        assert mask.sum() == len(starts) * 20

    def test_windows_do_not_exceed_array_bounds(self):
        sched = EventSchedule(period=100, duration=20, phase=990)
        rng = SeedableRNG(0)
        mask = sched.build(n=1000, rng=rng)

        assert len(mask) == 1000
        _, last_end = sched.windows[-1]
        assert last_end == 999

    def test_build_is_idempotent_for_same_n(self):
        sched = EventSchedule(period=50, duration=5, skip_probability=0.5)
        rng = SeedableRNG(1)
        mask1 = sched.build(n=500, rng=rng)
        windows1 = list(sched.windows)

        # Even with a fresh rng, a second build() call for the same n must
        # return the cached result so metrics sharing this schedule agree.
        mask2 = sched.build(n=500, rng=SeedableRNG(999))
        assert np.array_equal(mask1, mask2)
        assert sched.windows == windows1

    def test_skip_probability_creates_longer_gaps(self):
        sched = EventSchedule(
            period=100, duration=10, phase=0, skip_probability=1.0, max_skip_periods=3
        )
        rng = SeedableRNG(2)
        sched.build(n=2000, rng=rng)

        starts = [s for s, _ in sched.windows]
        diffs = np.diff(starts)
        # skip_probability=1.0 forces every gap to be a multiple (2 or 3) of period
        assert np.all(diffs >= 200)

    def test_zero_skip_probability_never_skips(self):
        sched = EventSchedule(period=30, duration=5, skip_probability=0.0)
        rng = SeedableRNG(3)
        sched.build(n=900, rng=rng)

        starts = [s for s, _ in sched.windows]
        diffs = np.diff(starts)
        assert np.all(diffs == 30)

    def test_jitter_shifts_start_within_bounds(self):
        sched = EventSchedule(period=100, duration=5, phase=250, jitter=5)
        rng = SeedableRNG(4)
        sched.build(n=1000, rng=rng)

        for start, _ in sched.windows:
            nearest_grid = round((start - 250) / 100) * 100 + 250
            assert abs(start - nearest_grid) <= 5

    def test_duration_tuple_samples_within_range(self):
        sched = EventSchedule(period=50, duration=(5, 10))
        rng = SeedableRNG(5)
        sched.build(n=2000, rng=rng)

        for start, end in sched.windows:
            length = end - start + 1
            assert 5 <= length <= 10


class TestPeriodicBurstAnomalyConstruction:
    def test_requires_schedule_or_period(self):
        with pytest.raises(ValueError):
            PeriodicBurstAnomaly()

    def test_rejects_both_schedule_and_period(self):
        sched = EventSchedule(period=10)
        with pytest.raises(ValueError):
            PeriodicBurstAnomaly(schedule=sched, period=10)

    def test_rejects_invalid_mode(self):
        with pytest.raises(ValueError):
            PeriodicBurstAnomaly(period=10, mode="bogus")  # type: ignore[arg-type]

    def test_rejects_negative_decay(self):
        with pytest.raises(ValueError):
            PeriodicBurstAnomaly(period=10, decay=-0.1)

    def test_rejects_negative_tail_length(self):
        with pytest.raises(ValueError):
            PeriodicBurstAnomaly(period=10, tail_length=-1)

    def test_standalone_period_builds_internal_schedule(self):
        anomaly = PeriodicBurstAnomaly(period=10, duration=3)
        assert isinstance(anomaly.schedule, EventSchedule)
        assert anomaly.schedule.period == 10


class TestPeriodicBurstAnomalyIntervene:
    def test_additive_mode_adds_peak_at_burst_onset(self):
        n = 500
        base = np.zeros(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="s")
        anomaly = PeriodicBurstAnomaly(
            period=100, duration=10, phase=50, peak_magnitude=5.0, decay=0.0, mode="additive"
        )
        result = anomaly.intervene(base, timestamps, rng=SeedableRNG(0))

        start, end = anomaly.schedule.windows[0]
        assert np.allclose(result[start : end + 1], 5.0)
        assert result[end + 1] == 0.0

    def test_replacement_mode_overwrites_baseline(self):
        n = 300
        base = np.full(n, 42.0)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="s")
        anomaly = PeriodicBurstAnomaly(
            period=50, duration=5, peak_magnitude=1.0, decay=0.0, mode="replacement"
        )
        result = anomaly.intervene(base, timestamps, rng=SeedableRNG(0))

        start, end = anomaly.schedule.windows[0]
        assert np.all(result[start : end + 1] == 1.0)

    def test_flag_pattern_produces_clean_binary_column(self):
        """decay=0, tail_length=0, replacement, magnitude=1 => a 0/1 event flag."""
        n = 1000
        base = np.zeros(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="100ms")
        flag = PeriodicBurstAnomaly(
            period=100,
            duration=20,
            phase=250,
            peak_magnitude=1.0,
            decay=0.0,
            tail_length=0,
            mode="replacement",
        )
        result = flag.intervene(base, timestamps, rng=SeedableRNG(0))

        assert set(np.unique(result)) <= {0.0, 1.0}
        expected_mask = flag.schedule.build(n, SeedableRNG(0))
        assert np.array_equal(result == 1.0, expected_mask)

    def test_decay_tail_extends_past_burst_window_and_decreases(self):
        n = 300
        base = np.zeros(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="s")
        anomaly = PeriodicBurstAnomaly(
            period=100,
            duration=10,
            phase=20,
            peak_magnitude=10.0,
            decay=0.3,
            tail_length=15,
            mode="additive",
        )
        result = anomaly.intervene(base, timestamps, rng=SeedableRNG(0))

        start, end = anomaly.schedule.windows[0]
        # Value right after the flagged window is still elevated above baseline...
        assert result[end + 1] > 0.0
        # ...and decays monotonically through the tail.
        tail = result[end + 1 : end + 1 + 15]
        assert np.all(np.diff(tail) < 0)
        # Fully decayed well beyond the tail.
        assert result[end + 1 + 15 + 50] == pytest.approx(0.0, abs=1e-6)

    def test_no_rng_falls_back_to_numpy_global(self):
        n = 200
        base = np.zeros(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="s")
        anomaly = PeriodicBurstAnomaly(period=20, duration=3, peak_magnitude=2.0)
        result = anomaly.intervene(base, timestamps, rng=DefaultRNG())
        assert np.any(result != 0.0)

    def test_magnitude_tuple_sampled_per_burst(self):
        n = 1000
        base = np.zeros(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="s")
        anomaly = PeriodicBurstAnomaly(
            period=100, duration=5, peak_magnitude=(1.0, 2.0), decay=0.0, mode="replacement"
        )
        result = anomaly.intervene(base, timestamps, rng=SeedableRNG(0))

        peaks = {result[s] for s, _ in anomaly.schedule.windows}
        assert all(1.0 <= p <= 2.0 for p in peaks)
        assert len(peaks) > 1  # different bursts got different sampled peaks


class TestPeriodicBurstAnomalySeedDeterminism:
    def test_same_seed_produces_identical_results(self):
        n = 1000
        base = np.zeros(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="s")

        def make():
            return PeriodicBurstAnomaly(
                period=100,
                duration=10,
                skip_probability=0.1,
                peak_magnitude=(1.0, 5.0),
                decay=0.2,
                tail_length=5,
            )

        r1 = make().intervene(base, timestamps, rng=SeedableRNG(42))
        r2 = make().intervene(base, timestamps, rng=SeedableRNG(42))
        assert np.array_equal(r1, r2)

    def test_different_seeds_produce_different_results(self):
        n = 1000
        base = np.zeros(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="s")

        def make():
            return PeriodicBurstAnomaly(
                period=100, duration=10, skip_probability=0.2, peak_magnitude=(1.0, 5.0)
            )

        r1 = make().intervene(base, timestamps, rng=SeedableRNG(1))
        r2 = make().intervene(base, timestamps, rng=SeedableRNG(2))
        assert not np.array_equal(r1, r2)


class TestSharedScheduleCorrelatesMetrics:
    def test_two_anomalies_sharing_a_schedule_align_windows(self):
        n = 1000
        shared = EventSchedule(period=100, duration=15, phase=250, skip_probability=0.05)

        bler = PeriodicBurstAnomaly(schedule=shared, peak_magnitude=0.05, decay=0.3, tail_length=8)
        flag = PeriodicBurstAnomaly(
            schedule=shared, peak_magnitude=1.0, decay=0.0, tail_length=0, mode="replacement"
        )

        base = np.zeros(n)
        timestamps = pd.date_range("2024-01-01", periods=n, freq="100ms")

        # Different rngs (as would happen across two different metrics in a
        # pipeline) must not desynchronize the shared burst windows.
        bler_result = bler.intervene(base, timestamps, rng=SeedableRNG(11))
        flag_result = flag.intervene(base, timestamps, rng=SeedableRNG(22))

        flagged = flag_result == 1.0
        assert flagged.sum() > 0
        # Every flagged sample must be inside a bler burst window (bler bursts
        # only ever equal the flagged windows plus a decaying tail after).
        for start, end in shared.windows:
            assert np.all(flagged[start : end + 1])
            assert np.any(bler_result[start : end + 1] > 0.0)


class TestDataGenWithPeriodicBurstAnomaly:
    def test_end_to_end_in_dataframe(self):
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-01 00:30:00",
            granularity="min",
            seed=7,
        )
        shared = EventSchedule(period=20, duration=3, phase=5)
        dg.add_metric(
            "signal",
            {LinearTrend(offset=10.0, slope=0.0)},
            anomalies=[
                PeriodicBurstAnomaly(schedule=shared, peak_magnitude=5.0, mode="additive")
            ],
        )
        dg.add_metric(
            "event_flag",
            {LinearTrend(offset=0.0, slope=0.0)},
            anomalies=[
                PeriodicBurstAnomaly(
                    schedule=shared, peak_magnitude=1.0, decay=0.0, mode="replacement"
                )
            ],
        )

        df = dg.data
        assert "signal" in df.columns
        assert "event_flag" in df.columns
        assert df["event_flag"].isin([0.0, 1.0]).all()
        assert (df["event_flag"] == 1.0).sum() > 0
        # Wherever the shared flag is on, the signal metric must be elevated.
        on = df["event_flag"] == 1.0
        assert (df.loc[on, "signal"] > 10.0).all()
