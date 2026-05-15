"""
Tests for the DataGen class
"""

import pytest
import pandas as pd
import numpy as np
from ts_data_generator import DataGen
from ts_data_generator.exceptions import (
    MetricError,
    MultiItemError,
    ValidationError,
)
from ts_data_generator.schema.models import Granularity
from ts_data_generator.utils.functions import (
    random_choice,
    random_int,
)
from enum import Enum
from typing import Generator
from ts_data_generator.utils.trends import (
    ARNoiseTrend,
    SinusoidalTrend,
    LinearTrend,
    StockTrend,
    WeekendTrend,
)
from ts_data_generator.random import SeedableRNG


class TestDataGen5minGenerator:
    # Setup method to initialize the Calculator instance

    @pytest.fixture
    def data_gen_instance(self):
        """Fixture to create a DataGen instance"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01"
        data_gen.end_datetime = "2022-01-02"
        data_gen.granularity = Granularity.FIVE_MIN
        # Create function that will return random choice from list
        data_gen.add_dimension(name="protocol", function=random_choice(["TCP", "UDP"]))
        data_gen.add_dimension(name="port", function=random_int(1, 65536))

        metric1_trend = SinusoidalTrend(
            name="sine", amplitude=1, freq=24, phase=0, noise_level=1
        )
        data_gen.add_metric(name="sine1", trends={metric1_trend})

        metric4_trend = WeekendTrend(
            name="weekend", weekend_effect=10, direction="up", noise_level=0.5, limit=10
        )
        data_gen.add_metric(name="weekend_trend1", trends={metric4_trend})

        metric5_trend = StockTrend(
            name="stock", amplitude=10, direction="up", noise_level=0.5
        )
        metric5_linear = LinearTrend(name="Linear", offset=0, noise_level=1, limit=10)
        data_gen.add_metric(
            name="stock_like_trend1", trends={metric5_trend, metric5_linear}
        )

        return data_gen

    def test_generated_data_is_pandas_instance(self, data_gen_instance):
        assert isinstance(data_gen_instance.data, pd.DataFrame)

    def test_metric_generator_output(self, data_gen_instance):
        expected_length = (
            int(24 * 60 / 5) + 1
        )  # ( 24 hours * 12 five-minute intervals in 1 hour)+1 to include end date
        assert data_gen_instance.data.shape[0] == expected_length
        assert (
            data_gen_instance.data.shape[1] == 6
        )  # 6 columns: protocol, epoch, port, sine1, weekend_trend1, stock_like_trend1

    def test_remove_dimension(self, data_gen_instance):
        dimension_to_remove = "port"
        data_gen_instance.remove_dimension(name=dimension_to_remove)
        assert (
            not (dimension_to_remove in list(data_gen_instance.dimensions.keys()))
            is True
        )

    def test_remove_metric(self, data_gen_instance):
        metric_to_remove = "weekend_trend1"
        data_gen_instance.remove_metric(name=metric_to_remove)


class TestDataGenHourlyGenerator:
    # Setup method to initialize the Calculator instance

    @pytest.fixture
    def data_gen_instance(self):
        """Fixture to create a DataGen instance"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01"
        data_gen.end_datetime = "2022-01-02"
        data_gen.granularity = Granularity.HOURLY
        # Create function that will return random choice from list
        protocol_choices = random_choice(["TCP", "UDP"])
        data_gen.add_dimension(name="protocol", function=protocol_choices)
        metric1_trend = SinusoidalTrend(
            name="sine", amplitude=1, freq=24, phase=0, noise_level=1
        )
        data_gen.add_metric(name="metric1", trends={metric1_trend})
        return data_gen

    def test_invalid_dimension_set(self, data_gen_instance):

        with pytest.raises(ValidationError):
            data_gen_instance.add_dimension(name="random", function=[])


class TestDataGenDailyGenerator:
    # Setup method to initialize the Calculator instance

    @pytest.fixture
    def data_gen_instance(self):
        """Fixture to create a DataGen instance"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01"
        data_gen.end_datetime = "2022-01-02"
        data_gen.granularity = Granularity.DAILY
        # Create function that will return random choice from list
        protocol_choices = random_choice(["TCP", "UDP"])
        data_gen.add_dimension(name="protocol", function=protocol_choices)
        metric1_trend = SinusoidalTrend(
            name="sine", amplitude=1, freq=24, phase=0, noise_level=1
        )
        data_gen.add_metric(name="metric1", trends={metric1_trend})
        return data_gen

    def test_invalid_dimension_set(self, data_gen_instance):

        with pytest.raises(ValidationError):
            data_gen_instance.add_dimension(name="random", function=[])


class TestDataGenSecondlyGenerator:
    # Setup method to initialize the Calculator instance

    @pytest.fixture
    def data_gen_instance(self):
        """Fixture to create a DataGen instance"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01"
        data_gen.end_datetime = "2022-01-02"
        data_gen.granularity = Granularity.ONE_SECOND
        # Create function that will return random choice from list
        protocol_choices = random_choice(["TCP", "UDP"])
        data_gen.add_dimension(name="protocol", function=protocol_choices)
        metric1_trend = SinusoidalTrend(
            name="sine", amplitude=1, freq=24, phase=0, noise_level=1
        )
        data_gen.add_metric(name="metric1", trends={metric1_trend})
        return data_gen

    def test_granularity(self, data_gen_instance):
        assert data_gen_instance.granularity == "s"
        assert data_gen_instance.data["epoch"].iloc[1] - data_gen_instance.data[
            "epoch"
        ].iloc[0] == np.int64(1)


class TestDataScaleGenerator:
    # Setup method to initialize the Calculator instance

    @pytest.fixture
    def data_gen_instance(self):
        """Fixture to create a DataGen instance"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01"
        data_gen.end_datetime = "2022-01-02"
        data_gen.granularity = Granularity.HOURLY
        # Create function that will return random choice from list
        data_gen.add_dimension(
            name="protocol", function=random_choice("TCP UDP".split())
        )
        data_gen.add_dimension(name="interface", function="X Y Z".split())
        metric1_trend = SinusoidalTrend(
            name="sine", amplitude=1, freq=24, phase=0, noise_level=1
        )
        data_gen.add_metric(name="metric1", trends={metric1_trend})
        return data_gen

    def test_granularity(self, data_gen_instance):
        assert data_gen_instance.data["epoch"].iloc[1] - data_gen_instance.data[
            "epoch"
        ].iloc[0] == np.int64(3600)

    def test_scale(self, data_gen_instance):
        with pytest.raises(ValidationError):
            data_gen_instance.normalize(method="invalid")

        saved = data_gen_instance.data["metric1"].iloc[0]

        data_gen_instance.normalize()
        assert data_gen_instance.data["metric1"].min() == 0
        assert data_gen_instance.data["metric1"].max() == 1
        assert data_gen_instance.data["metric1"].iloc[0] != pytest.approx(saved)

        data_gen_instance.denormalize()
        assert data_gen_instance.data["metric1"].iloc[0] == pytest.approx(saved)

    def test_linked_dimension(self, data_gen_instance):
        import random

        def my_custom_function():
            while True:
                val1 = random.randint(1, 100)
                val2 = random.randint(1, 100)
                val3 = val1 + val2
                yield (val1, val2, val3)

        data_gen_instance.add_multi_items(
            names=["dim1", "dim2", "dim3"], function=my_custom_function()
        )
        assert np.True_ is (
            (
                data_gen_instance.data["dim1"] + data_gen_instance.data["dim2"]
                == data_gen_instance.data["dim3"]
            ).values.all()
        )
        with pytest.raises(MultiItemError):
            data_gen_instance.add_multi_items(
                names="dim1 dim2".split(), function=my_custom_function()
            )

        with pytest.raises(MultiItemError):
            data_gen_instance.add_multi_items(
                names="dim1 dim5 dim6".split(), function=my_custom_function()
            )

        data_gen_instance.remove_multi_item(["dim1"])
        assert "dim2" not in data_gen_instance.data.columns


class TestDataAggregation:
    # Setup method to initialize the Calculator instance

    @pytest.fixture
    def data_gen_instance(self):
        """Fixture to create a DataGen instance"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01 00:00:00"
        data_gen.end_datetime = "2022-01-01 00:15:00"
        data_gen.granularity = Granularity.FIVE_MIN
        # Create function that will return random choice from list
        data_gen.add_dimension(
            name="protocol", function=random_choice("TCP UDP".split())
        )
        data_gen.add_dimension(name="interface", function="X Y Z".split())

        def my_custom_function():
            while True:
                for x, y, z in zip(range(1, 10), range(2, 11), range(3, 12)):
                    yield (x, y, z)

        data_gen.add_multi_items(
            names="val1 val2 val3".split(),
            function=my_custom_function(),
            aggregation_type="sum mean max".split(),
        )
        return data_gen

    def test_aggregate(self, data_gen_instance):
        print(data_gen_instance.data)
        print(data_gen_instance.aggregate("W"))
        print(data_gen_instance.data)


def test_add_metric_duplicate_trends():
    data_gen = DataGen(
        start_datetime="2023-01-01",
        end_datetime="2023-01-02",
        granularity=Granularity.DAILY,
    )
    trend = LinearTrend(offset=0.5)

    # Should work without error
    data_gen.add_metric(name="metric_unique", trends=[trend])

    # Should raise error with duplicate trends
    with pytest.raises(MetricError, match="Duplicate trends are present"):
        data_gen.add_metric(name="metric_duplicate", trends=[trend, trend])


class TestToGranularity:
    @pytest.fixture
    def data_gen_instance(self):
        """Fixture to create a DataGen instance"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01"
        data_gen.end_datetime = "2022-01-02"
        return data_gen

    def test_to_granularity_with_enum(self, data_gen_instance):
        data_gen_instance.to_granularity(Granularity.HOURLY)
        assert data_gen_instance.granularity == "h"

    def test_to_granularity_with_string(self, data_gen_instance):
        data_gen_instance.to_granularity("5min")
        assert data_gen_instance.granularity == "5min"

    def test_to_granularity_invalid_string(self, data_gen_instance):
        with pytest.raises(ValueError):
            data_gen_instance.to_granularity("invalid")


class TestARNoiseTrend:
    """Tests for ARNoiseTrend — autoregressive noise model."""

    @staticmethod
    def _make_timestamps(n: int = 100) -> pd.DatetimeIndex:
        return pd.date_range("2023-01-01", periods=n, freq="h")

    def test_explicit_coefficients_basic(self):
        """ARNoiseTrend with explicit coefficients produces output of correct length."""
        timestamps = self._make_timestamps(50)
        trend = ARNoiseTrend(coefficients=[0.5, -0.2], noise_std=0.5)
        output = trend.generate(timestamps)
        assert len(output) == 50
        assert isinstance(output, np.ndarray)

    def test_auto_generated_coefficients(self):
        """decay + order auto-generates stable coefficients and produces output."""
        timestamps = self._make_timestamps(50)
        trend = ARNoiseTrend(decay=0.8, order=3, noise_std=0.5)
        output = trend.generate(timestamps)
        assert len(output) == 50
        # Auto-generated coefficients must satisfy sum(|c|) < 1 (stationarity)
        assert np.sum(np.abs(trend.coefficients)) < 1.0

    def test_determinism_with_fixed_seed(self):
        """Same seed produces identical output."""
        timestamps = self._make_timestamps(30)
        trend = ARNoiseTrend(coefficients=[0.5], noise_std=0.5)
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        out1 = trend.generate(timestamps, rng=rng1)
        out2 = trend.generate(timestamps, rng=rng2)
        np.testing.assert_array_equal(out1, out2)

    def test_different_seeds_produce_different_output(self):
        """Different seeds produce different output."""
        timestamps = self._make_timestamps(30)
        trend = ARNoiseTrend(coefficients=[0.5], noise_std=0.5)
        out1 = trend.generate(timestamps, rng=SeedableRNG(1))
        out2 = trend.generate(timestamps, rng=SeedableRNG(2))
        assert not np.allclose(out1, out2)

    def test_autocorrelation_positive_coefficient(self):
        """AR(1) with large positive c1 should exhibit positive lag-1 autocorrelation."""
        timestamps = self._make_timestamps(500)
        trend = ARNoiseTrend(coefficients=[0.9], noise_std=0.1)
        rng = SeedableRNG(123)
        output = trend.generate(timestamps, rng=rng)
        # Compute lag-1 autocorrelation
        corr = np.corrcoef(output[:-1], output[1:])[0, 1]
        assert corr > 0.3  # strong positive serial correlation

    def test_autocorrelation_negative_coefficient(self):
        """AR(1) with negative c1 should exhibit negative lag-1 autocorrelation."""
        timestamps = self._make_timestamps(500)
        trend = ARNoiseTrend(coefficients=[-0.7], noise_std=0.1)
        rng = SeedableRNG(123)
        output = trend.generate(timestamps, rng=rng)
        corr = np.corrcoef(output[:-1], output[1:])[0, 1]
        assert corr < -0.2  # negative serial correlation

    def test_noise_std_zero_is_deterministic_ar(self):
        """With noise_std=0 and a single coefficient, AR process follows exact recurrence."""
        timestamps = self._make_timestamps(20)
        trend = ARNoiseTrend(coefficients=[0.5], noise_std=0.0)
        rng = SeedableRNG(99)
        output = trend.generate(timestamps, rng=rng)
        # After warmup, value[t] = 0.5 * value[t-1] exactly (noise=0)
        # Check that the recurrence holds after the warmup period
        for t in range(3, len(output)):
            expected = 0.5 * output[t - 1]
            assert output[t] == pytest.approx(expected)

    def test_validation_requires_coefficients_or_decay_order(self):
        """Must provide either coefficients or both decay and order."""
        with pytest.raises(ValueError, match="Provide either coefficients"):
            ARNoiseTrend(noise_std=0.5)

    def test_validation_decay_range(self):
        """decay must be in (0, 1)."""
        with pytest.raises(ValueError, match="decay must be"):
            ARNoiseTrend(decay=1.5, order=3)

    def test_validation_empty_coefficients(self):
        """coefficients must not be empty."""
        with pytest.raises(ValueError, match="at least one value"):
            ARNoiseTrend(coefficients=[])
