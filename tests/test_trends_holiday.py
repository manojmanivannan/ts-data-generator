"""Tests for HolidayTrend implementation."""

import pandas as pd
import numpy as np
import pytest
from ts_data_generator.utils.trends import HolidayTrend

# Helper to compare arrays with tolerance

def assert_array_equal(a, b, tol=1e-7):
    assert isinstance(a, np.ndarray)
    assert isinstance(b, np.ndarray)
    assert a.shape == b.shape
    assert np.allclose(a, b, atol=tol)


class TestHolidayTrend:
    def test_effect_on_holiday_day_up(self):
        """HolidayTrend should apply full effect on holiday day for direction up."""
        trend = HolidayTrend(
            name="test",
            dates=["2023-01-02"],
            effect=10.0,
            noise_level=0.0,
            direction="up",
        )
        timestamps = pd.date_range("2023-01-02", periods=3, freq="D")
        values = trend.generate(timestamps)
        assert_array_equal(values, np.array([10.0, 0.0, 0.0]))

    def test_effect_on_holiday_day_down(self):
        """HolidayTrend should apply full negative effect on holiday day for direction down."""
        trend = HolidayTrend(
            name="test",
            dates=["2023-01-02"],
            effect=10.0,
            noise_level=0.0,
            direction="down",
        )
        timestamps = pd.date_range("2023-01-02", periods=3, freq="D")
        values = trend.generate(timestamps)
        assert_array_equal(values, np.array([-10.0, 0.0, 0.0]))

    def test_pre_window_ramp_up(self):
        """HolidayTrend should ramp effect up over pre_window days."""
        trend = HolidayTrend(
            name="test",
            dates=["2023-01-02"],
            effect=10.0,
            pre_window=2,
            post_window=0,
            noise_level=0.0,
            direction="up",
        )
        # timestamps: day before, holiday day, day after
        timestamps = pd.date_range("2023-01-01", periods=3, freq="D")
        values = trend.generate(timestamps)
        # Day before holiday: 5.0, holiday day:10.0, day after:0.0
        assert_array_equal(values, np.array([5.0, 10.0, 0.0]))

    def test_post_window_ramp_down(self):
        """HolidayTrend should ramp effect down after holiday day over post_window days."""
        trend = HolidayTrend(
            name="test",
            dates=["2023-01-02"],
            effect=10.0,
            pre_window=0,
            post_window=2,
            noise_level=0.0,
            direction="up",
        )
        timestamps = pd.date_range("2023-01-02", periods=3, freq="D")
        # But we need day after holiday too: create 4 days
        timestamps = pd.date_range("2023-01-02", periods=4, freq="D")
        values = trend.generate(timestamps)
        # 2023-01-02: 10.0, 2023-01-03: 5.0, 2023-01-04:0
        assert_array_equal(values, np.array([10.0, 5.0, 0.0, 0.0]))

    def test_direction_down(self):
        """HolidayTrend should apply negative effect for direction down."""
        trend = HolidayTrend(
            name="test",
            dates=["2023-01-02"],
            effect=10.0,
            pre_window=0,
            post_window=0,
            noise_level=0.0,
            direction="down",
        )
        timestamps = pd.date_range("2023-01-02", periods=3, freq="D")
        values = trend.generate(timestamps)
        assert_array_equal(values, np.array([-10.0, 0.0, 0.0]))

    def test_error_when_no_dates_or_country(self):
        """HolidayTrend should raise ValueError if no dates and no country provided."""
        with pytest.raises(ValueError, match="Either country or dates must be provided"):
            HolidayTrend(name="test")

    def test_error_negative_pre_window(self):
        """HolidayTrend should raise ValueError if pre_window negative."""
        with pytest.raises(ValueError, match="pre_window"):
            HolidayTrend(name="test", dates=["2023-01-01"], pre_window=-1)

    def test_error_negative_post_window(self):
        """HolidayTrend should raise ValueError if post_window negative."""
        with pytest.raises(ValueError, match="post_window"):
            HolidayTrend(name="test", dates=["2023-01-01"], post_window=-1)