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
    HolidayTrend,
    LinearTrend,
    SinusoidalTrend,
    StockTrend,
    WeekendTrend,
)


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


class TestHolidayTrend:
    """Tests for the HolidayTrend class."""

    @staticmethod
    def _make_timestamps(start: str, end: str) -> pd.DatetimeIndex:
        return pd.date_range(start=start, end=end, freq="D")

    def test_ramp_shape_upward(self):
        """Linear ramp: 0 at pre_window, peak at holiday, 0 at post_window."""
        holiday = HolidayTrend(
            name="xmas", dates=["2024-01-05"], effect=60, pre_window=3, post_window=2,
            direction="up",
        )
        timestamps = self._make_timestamps("2024-01-01", "2024-01-08")
        values = holiday.generate(timestamps)

        # 2024-01-02: holiday - 3 = 0
        assert values[1] == pytest.approx(0.0)
        # 2024-01-03: holiday - 2 = 60 * 1/3 = 20
        assert values[2] == pytest.approx(20.0)
        # 2024-01-04: holiday - 1 = 60 * 2/3 = 40
        assert values[3] == pytest.approx(40.0)
        # 2024-01-05: holiday = 60
        assert values[4] == pytest.approx(60.0)
        # 2024-01-06: holiday + 1 = 60 * 1/2 = 30
        assert values[5] == pytest.approx(30.0)
        # 2024-01-07: holiday + 2 = 0
        assert values[6] == pytest.approx(0.0)
        # 2024-01-01: before window
        assert values[0] == pytest.approx(0.0)
        # 2024-01-08: after window
        assert values[7] == pytest.approx(0.0)

    def test_ramp_shape_downward(self):
        """direction='down' produces negative ramps."""
        holiday = HolidayTrend(
            dates=["2024-06-15"], effect=30, pre_window=2, post_window=1,
            direction="down",
        )
        timestamps = self._make_timestamps("2024-06-13", "2024-06-16")
        values = holiday.generate(timestamps)

        # 2024-06-13: holiday - 2 = 0
        assert values[0] == pytest.approx(0.0)
        # 2024-06-14: holiday - 1 = -30 * 1/2 = -15
        assert values[1] == pytest.approx(-15.0)
        # 2024-06-15: holiday = -30
        assert values[2] == pytest.approx(-30.0)
        # 2024-06-16: holiday + 1 = 0
        assert values[3] == pytest.approx(0.0)

    def test_fallback_dates(self):
        """User-provided dates work without the holidays library."""
        holiday = HolidayTrend(
            dates=["2024-01-10"], effect=100, pre_window=1, post_window=1,
        )
        timestamps = self._make_timestamps("2024-01-09", "2024-01-11")
        values = holiday.generate(timestamps)

        assert values[0] == pytest.approx(0.0)    # holiday - 1
        assert values[1] == pytest.approx(100.0)   # holiday
        assert values[2] == pytest.approx(0.0)    # holiday + 1

    def test_window_overlap_sums_effects(self):
        """Overlapping holiday windows sum their contributions."""
        holiday = HolidayTrend(
            dates=["2024-03-15", "2024-03-16"],
            effect=50, pre_window=2, post_window=2, direction="up",
        )
        timestamps = self._make_timestamps("2024-03-13", "2024-03-18")
        values = holiday.generate(timestamps)

        # 2024-03-14: pre-window for holiday 1 only
        # holiday 1 (3/15): day -1 = 50 * 1/2 = 25
        assert values[1] == pytest.approx(25.0)
        # 2024-03-15: holiday 1 peak (50) + holiday 2 pre (-1) = 50 + 25 = 75
        assert values[2] == pytest.approx(75.0)
        # 2024-03-16: holiday 1 post (+1=25) + holiday 2 peak (50) = 75
        assert values[3] == pytest.approx(75.0)
        # 2024-03-17: holiday 2 post (+1) = 25
        assert values[4] == pytest.approx(25.0)

    def test_country_auto_resolve(self):
        """country='US' resolves holidays via the holidays library."""
        holiday = HolidayTrend(
            country="US", effect=100, pre_window=0, post_window=0, direction="up",
        )
        # Use 2024 where Christmas (12/25) is a federal holiday
        timestamps = self._make_timestamps("2024-12-24", "2024-12-26")
        values = holiday.generate(timestamps)

        # 2024-12-24: not a holiday
        assert values[0] == pytest.approx(0.0)
        # 2024-12-25: Christmas
        assert values[1] == pytest.approx(100.0)
        # 2024-12-26: not a holiday
        assert values[2] == pytest.approx(0.0)

    def test_graceful_error_no_holidays_no_dates(self):
        """ImportError when holidays library unavailable and no dates provided."""
        import builtins
        import sys
        from unittest import mock

        holiday = HolidayTrend(effect=50)
        timestamps = self._make_timestamps("2024-01-01", "2024-01-05")

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "holidays":
                raise ImportError("No module named 'holidays'")
            return real_import(name, *args, **kwargs)

        stale = [k for k in sys.modules if k == "holidays" or k.startswith("holidays.")]
        saved = {k: sys.modules.pop(k) for k in stale}
        try:
            with mock.patch("builtins.__import__", side_effect=mock_import):
                with pytest.raises(ImportError, match="holidays"):
                    holiday.generate(timestamps)
        finally:
            sys.modules.update(saved)

    def test_accepts_rng_parameter(self):
        """RNG parameter is accepted (no-op for now, but API-compatible)."""
        from ts_data_generator.random import SeedableRNG

        rng = SeedableRNG(42)
        holiday = HolidayTrend(dates=["2024-07-04"], effect=50)
        timestamps = self._make_timestamps("2024-07-03", "2024-07-05")
        values = holiday.generate(timestamps, rng=rng)
        assert len(values) == len(timestamps)

    def test_pre_window_zero(self):
        """pre_window=0 means the effect jumps immediately at the holiday."""
        holiday = HolidayTrend(dates=["2024-05-01"], effect=40, pre_window=0, post_window=1)
        timestamps = self._make_timestamps("2024-04-30", "2024-05-02")
        values = holiday.generate(timestamps)

        assert values[0] == pytest.approx(0.0)    # day before
        assert values[1] == pytest.approx(40.0)    # holiday
        assert values[2] == pytest.approx(0.0)    # day after

    def test_post_window_zero(self):
        """post_window=0 means the effect drops immediately after the holiday."""
        holiday = HolidayTrend(dates=["2024-05-01"], effect=40, pre_window=1, post_window=0)
        timestamps = self._make_timestamps("2024-04-30", "2024-05-02")
        values = holiday.generate(timestamps)

        assert values[0] == pytest.approx(0.0)    # pre-window start
        assert values[1] == pytest.approx(40.0)    # holiday
        assert values[2] == pytest.approx(0.0)    # day after

    def test_dates_across_years(self):
        """Fallback dates spanning multiple years."""
        holiday = HolidayTrend(
            dates=["2023-12-31", "2024-01-01"], effect=30,
            pre_window=0, post_window=0, direction="up",
        )
        timestamps = self._make_timestamps("2023-12-30", "2024-01-02")
        values = holiday.generate(timestamps)

        assert values[0] == pytest.approx(0.0)
        assert values[1] == pytest.approx(30.0)   # 2023-12-31
        assert values[2] == pytest.approx(30.0)   # 2024-01-01
        assert values[3] == pytest.approx(0.0)

    def test_sub_daily_timestamps(self):
        """Holiday effect applies to all sub-daily timestamps on affected days."""
        holiday = HolidayTrend(
            dates=["2024-06-01"], effect=60, pre_window=1, post_window=1, direction="up",
        )
        timestamps = pd.date_range(start="2024-05-31", end="2024-06-02", freq="h")
        values = holiday.generate(timestamps)

        # All 24 hourly timestamps on 2024-06-01 should have full effect
        june1_values = values[24:48]  # indices for June 1
        np.testing.assert_allclose(june1_values, 60.0)


class TestARNoiseTrend:
    """Tests for the ARNoiseTrend class."""

    @staticmethod
    def _make_timestamps(n: int) -> pd.DatetimeIndex:
        return pd.date_range(start="2024-01-01", periods=n, freq="D")

    def test_explicit_coefficients_order_2(self):
        """ARNoiseTrend with explicit coefficients produces AR(2) noise."""
        from ts_data_generator.utils.trends import ARNoiseTrend

        trend = ARNoiseTrend(coefficients=[0.5, -0.2], noise_std=0.5)
        timestamps = self._make_timestamps(500)
        values = trend.generate(timestamps)

        assert len(values) == 500
        assert np.all(np.isfinite(values))
        # AR(2) with these coefficients should not explode
        assert np.std(values) < 10.0

    def test_decay_auto_generates_coefficients(self):
        """decay + order auto-generates stable coefficients."""
        from ts_data_generator.utils.trends import ARNoiseTrend

        trend = ARNoiseTrend(decay=0.8, order=3, noise_std=0.5)
        timestamps = self._make_timestamps(1000)
        values = trend.generate(timestamps)

        assert len(values) == 1000
        assert trend.order == 3
        assert len(trend.coefficients) == 3
        assert np.all(np.isfinite(values))

    def test_auto_coefficients_stationarity(self):
        """Auto-generated coefficients have roots inside the unit circle."""
        from ts_data_generator.utils.trends import ARNoiseTrend

        for decay in [0.3, 0.5, 0.8]:
            for order in [1, 2, 3, 5]:
                trend = ARNoiseTrend(decay=decay, order=order)
                coeffs = trend.coefficients

                # Build companion matrix and check eigenvalues
                if order == 1:
                    roots = np.abs(coeffs)
                else:
                    companion = np.zeros((order, order))
                    companion[0, :] = coeffs
                    for i in range(1, order):
                        companion[i, i - 1] = 1.0
                    roots = np.abs(np.linalg.eigvals(companion))

                assert np.all(roots < 1.0), (
                    f"Non-stationary for decay={decay}, order={order}: max|root|={roots.max()}"
                )

    def test_explicit_coefficients_acceptance(self):
        """Explicit coefficients are stored and used as-is."""
        from ts_data_generator.utils.trends import ARNoiseTrend

        coeffs = [0.7, -0.3, 0.1]
        trend = ARNoiseTrend(coefficients=coeffs)
        np.testing.assert_array_almost_equal(trend.coefficients, coeffs)
        assert trend.order == 3

    def test_seed_determinism(self):
        """With a fixed rng seed, output is deterministic."""
        from ts_data_generator.random import SeedableRNG
        from ts_data_generator.utils.trends import ARNoiseTrend

        coeffs = [0.5, -0.2]
        timestamps = self._make_timestamps(100)

        rng1 = SeedableRNG(42)
        values1 = ARNoiseTrend(coefficients=coeffs).generate(timestamps, rng=rng1)

        rng2 = SeedableRNG(42)
        values2 = ARNoiseTrend(coefficients=coeffs).generate(timestamps, rng=rng2)

        np.testing.assert_array_equal(values1, values2)

    def test_warmup_correct_output_count(self):
        """Warm-up produces exactly len(timestamps) output values."""
        from ts_data_generator.utils.trends import ARNoiseTrend

        for n in [10, 50, 100, 1000]:
            for order in [1, 3, 5]:
                trend = ARNoiseTrend(coefficients=[0.5] * order)
                timestamps = self._make_timestamps(n)
                values = trend.generate(timestamps)
                assert len(values) == n

    def test_autocorrelation_matches_coefficients(self):
        """Output exhibits autocorrelation consistent with AR(1) coefficient."""
        from ts_data_generator.utils.trends import ARNoiseTrend

        # AR(1): value[t] = phi * value[t-1] + noise
        # Theoretical lag-1 autocorrelation ≈ phi
        phi = 0.7
        trend = ARNoiseTrend(coefficients=[phi], noise_std=0.5)
        timestamps = self._make_timestamps(5000)
        values = trend.generate(timestamps)

        # Compute sample lag-1 autocorrelation
        centered = values - values.mean()
        lag1_corr = np.corrcoef(centered[1:], centered[:-1])[0, 1]

        # Should be close to phi for a long series
        assert abs(lag1_corr - phi) < 0.05, f"Expected ~{phi}, got {lag1_corr}"

    def test_noise_std_controls_variance(self):
        """Higher noise_std produces proportionally larger variance."""
        from ts_data_generator.utils.trends import ARNoiseTrend

        timestamps = self._make_timestamps(2000)

        std_low = np.std(
            ARNoiseTrend(coefficients=[0.5], noise_std=0.1).generate(timestamps)
        )
        std_high = np.std(
            ARNoiseTrend(coefficients=[0.5], noise_std=1.0).generate(timestamps)
        )

        # Higher noise_std should yield higher output std (roughly proportional)
        assert std_high > std_low * 5

    def test_decay_deterministic_coefficients(self):
        """Same decay+order always produces same coefficients."""
        from ts_data_generator.utils.trends import ARNoiseTrend

        coeffs1 = ARNoiseTrend(decay=0.8, order=4).coefficients
        coeffs2 = ARNoiseTrend(decay=0.8, order=4).coefficients

        np.testing.assert_array_equal(coeffs1, coeffs2)

    def test_invalid_args_raise(self):
        """Invalid argument combinations raise ValueError."""
        from ts_data_generator.utils.trends import ARNoiseTrend

        # Missing both
        with pytest.raises(ValueError, match="Either"):
            ARNoiseTrend()

        # Both provided
        with pytest.raises(ValueError, match="Provide either"):
            ARNoiseTrend(coefficients=[0.5], decay=0.8)

        # decay out of range
        with pytest.raises(ValueError, match="decay must be in"):
            ARNoiseTrend(decay=1.5, order=3)

        with pytest.raises(ValueError, match="decay must be in"):
            ARNoiseTrend(decay=-0.5, order=3)
