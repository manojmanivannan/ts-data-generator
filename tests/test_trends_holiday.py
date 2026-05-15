"""Tests for HolidayTrend implementation."""

import numpy as np
import pandas as pd
import pytest

from ts_data_generator.random import SeedableRNG
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

    def test_overlapping_holiday_windows_sum(self):
        """Overlapping holiday windows should sum their effects."""
        trend = HolidayTrend(
            name="test",
            dates=["2023-01-02", "2023-01-03"],
            effect=10.0,
            pre_window=2,
            post_window=2,
            noise_level=0.0,
            direction="up",
        )
        timestamps = pd.date_range("2023-01-01", periods=5, freq="D")
        values = trend.generate(timestamps)
        # Both holidays have overlapping ramp windows on Jan 02 and Jan 03
        # Jan 01: only first holiday's pre_window (diff=-1, coeff=0.5) = 5
        assert values[0] == pytest.approx(5.0)
        # Jan 02: first holiday peak (10) + second holiday pre_window (diff=-1, coeff=0.5 => 5) = 15
        assert values[1] == pytest.approx(15.0)
        # Jan 03: first holiday post_window (diff=1, coeff=0.5 => 5) + second holiday peak (10) = 15
        assert values[2] == pytest.approx(15.0)

    def test_accepts_rng_parameter(self):
        """HolidayTrend with rng should produce deterministic output."""
        trend = HolidayTrend(
            name="test",
            dates=["2023-01-02"],
            effect=10.0,
            noise_level=0.5,
            direction="up",
        )
        timestamps = pd.date_range("2023-01-01", periods=3, freq="D")
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        out1 = trend.generate(timestamps, rng=rng1)
        out2 = trend.generate(timestamps, rng=rng2)
        np.testing.assert_array_equal(out1, out2)

    def test_error_when_country_without_holidays_library(self):
        """HolidayTrend with country but no holidays library should raise RuntimeError."""
        trend = HolidayTrend(
            name="test",
            country="US",
            effect=10.0,
        )
        timestamps = pd.date_range("2023-01-01", periods=3, freq="D")
        # The holidays library is not necessarily installed; if it isn't,
        # we should get a RuntimeError. If it IS installed, this test
        # won't raise and that's also fine.
        try:
            import holidays  # noqa: F401
            holidays_installed = True
        except ImportError:
            holidays_installed = False

        if not holidays_installed:
            with pytest.raises(RuntimeError, match="holidays library is required"):
                trend.generate(timestamps)
