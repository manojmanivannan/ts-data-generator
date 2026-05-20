"""Tests for SeedableRNG determinism and seed propagation through DataGen."""

import numpy as np
import pandas as pd
import pytest

from ts_data_generator import DataGen
from ts_data_generator.random import SeedableRNG
from ts_data_generator.schema.models import Granularity
from ts_data_generator.utils.trends import (
    LinearTrend,
    SinusoidalTrend,
    StockTrend,
    WeekendTrend,
)


class TestSeedableRNG:
    def test_same_seed_produces_identical_normal(self):
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        a = rng1.normal(0, 1, size=100)
        b = rng2.normal(0, 1, size=100)
        np.testing.assert_array_equal(a, b)

    def test_same_seed_produces_identical_uniform(self):
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        a = rng1.uniform(0, 1, size=50)
        b = rng2.uniform(0, 1, size=50)
        np.testing.assert_array_equal(a, b)

    def test_same_seed_produces_identical_choice(self):
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        vals = [10, 20, 30, 40, 50]
        a = rng1.choice(vals, size=20)
        b = rng2.choice(vals, size=20)
        np.testing.assert_array_equal(a, b)

    def test_same_seed_produces_identical_random(self):
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        a = rng1.random(size=30)
        b = rng2.random(size=30)
        np.testing.assert_array_equal(a, b)

    def test_different_seeds_produce_different_output(self):
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(99)
        a = rng1.normal(0, 1, size=100)
        b = rng2.normal(0, 1, size=100)
        assert not np.array_equal(a, b)

    def test_sequence_is_deterministic_across_methods(self):
        rng = SeedableRNG(7)
        # Draw from each method in sequence, twice
        first_normal = rng.normal(size=5)
        first_uniform = rng.uniform(size=5)
        first_choice = rng.choice([1, 2, 3], size=5)

        rng2 = SeedableRNG(7)
        second_normal = rng2.normal(size=5)
        second_uniform = rng2.uniform(size=5)
        second_choice = rng2.choice([1, 2, 3], size=5)

        np.testing.assert_array_equal(first_normal, second_normal)
        np.testing.assert_array_equal(first_uniform, second_uniform)
        np.testing.assert_array_equal(first_choice, second_choice)

    def test_seed_property(self):
        rng = SeedableRNG(123)
        assert rng.seed == 123


class TestTrendsWithRNG:
    """Verify all four trend classes accept rng and produce deterministic output."""

    @pytest.fixture
    def timestamps(self):
        return pd.date_range("2024-01-01", "2024-01-07", freq="h")

    def test_sinusoidal_with_rng_is_deterministic(self, timestamps):
        trend = SinusoidalTrend(amplitude=5, freq=24, noise_level=0.5)
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        a = trend.generate(timestamps, rng=rng1)
        b = trend.generate(timestamps, rng=rng2)
        np.testing.assert_array_equal(a, b)

    def test_sinusoidal_without_rng_still_works(self, timestamps):
        trend = SinusoidalTrend(amplitude=5, freq=24, noise_level=0.5)
        result = trend.generate(timestamps)
        assert len(result) == len(timestamps)

    def test_linear_with_rng_is_deterministic(self, timestamps):
        trend = LinearTrend(offset=10, noise_level=2, slope=30)
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        a = trend.generate(timestamps, rng=rng1)
        b = trend.generate(timestamps, rng=rng2)
        np.testing.assert_array_equal(a, b)

    def test_linear_without_rng_still_works(self, timestamps):
        trend = LinearTrend(offset=10, noise_level=2, slope=30)
        result = trend.generate(timestamps)
        assert len(result) == len(timestamps)

    def test_weekend_with_rng_is_deterministic(self, timestamps):
        trend = WeekendTrend(weekend_effect=8, noise_level=1)
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        a = trend.generate(timestamps, rng=rng1)
        b = trend.generate(timestamps, rng=rng2)
        np.testing.assert_array_equal(a, b)

    def test_weekend_without_rng_still_works(self, timestamps):
        trend = WeekendTrend(weekend_effect=8, noise_level=1)
        result = trend.generate(timestamps)
        assert len(result) == len(timestamps)

    def test_stock_with_rng_is_deterministic(self, timestamps):
        trend = StockTrend(amplitude=15, noise_level=0.5)
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        a = trend.generate(timestamps, rng=rng1)
        b = trend.generate(timestamps, rng=rng2)
        np.testing.assert_array_equal(a, b)

    def test_stock_without_rng_still_works(self, timestamps):
        trend = StockTrend(amplitude=15, noise_level=0.5)
        result = trend.generate(timestamps)
        assert len(result) == len(timestamps)


class TestDataGenSeed:
    """Verify DataGen(seed=...) produces identical DataFrames."""

    def test_seeded_datagen_produces_identical_dataframes(self):
        dg1 = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-05",
            granularity=Granularity.HOURLY,
            seed=42,
        )
        dg1.add_metric("m1", {SinusoidalTrend(amplitude=5, freq=24, noise_level=0.5)})
        dg1.add_metric("m2", {LinearTrend(offset=10, noise_level=1, slope=20)})

        dg2 = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-05",
            granularity=Granularity.HOURLY,
            seed=42,
        )
        dg2.add_metric("m1", {SinusoidalTrend(amplitude=5, freq=24, noise_level=0.5)})
        dg2.add_metric("m2", {LinearTrend(offset=10, noise_level=1, slope=20)})

        pd.testing.assert_frame_equal(dg1.data, dg2.data)

    def test_different_seeds_produce_different_dataframes(self):
        dg1 = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-05",
            granularity=Granularity.HOURLY,
            seed=42,
        )
        dg1.add_metric("m", {SinusoidalTrend(amplitude=5, freq=24, noise_level=0.5)})

        dg2 = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-05",
            granularity=Granularity.HOURLY,
            seed=99,
        )
        dg2.add_metric("m", {SinusoidalTrend(amplitude=5, freq=24, noise_level=0.5)})

        with pytest.raises(AssertionError):
            pd.testing.assert_frame_equal(dg1.data, dg2.data)

    def test_seeded_datagen_with_stock_and_weekend_trends(self):
        dg1 = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-10",
            granularity=Granularity.DAILY,
            seed=42,
        )
        dg1.add_metric("stock", {StockTrend(amplitude=15, noise_level=0.5)})
        dg1.add_metric("weekend", {WeekendTrend(weekend_effect=8, noise_level=1)})

        dg2 = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-10",
            granularity=Granularity.DAILY,
            seed=42,
        )
        dg2.add_metric("stock", {StockTrend(amplitude=15, noise_level=0.5)})
        dg2.add_metric("weekend", {WeekendTrend(weekend_effect=8, noise_level=1)})

        pd.testing.assert_frame_equal(dg1.data, dg2.data)

    def test_no_seed_still_produces_data(self):
        dg = DataGen(
            start_datetime="2024-01-01",
            end_datetime="2024-01-02",
            granularity=Granularity.HOURLY,
        )
        dg.add_metric("m", {SinusoidalTrend(amplitude=5, freq=24, noise_level=0.5)})
        assert "m" in dg.data.columns
        assert len(dg.data) > 0
