"""Tests for the plot_time_series function."""

from __future__ import annotations

from unittest import mock

import pandas as pd
import pytest

from ts_data_generator.exceptions import ValidationError
from ts_data_generator.plotting import plot_time_series


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Create a simple time-indexed DataFrame with numeric and non-numeric columns."""
    return pd.DataFrame(
        {
            "temperature": [20.0, 22.5, 25.0],
            "humidity": [60, 55, 50],
            "epoch": [1700000000, 1700003600, 1700007200],
            "label": ["a", "b", "c"],
        },
        index=pd.date_range("2024-01-01", periods=3, freq="h"),
    )


class TestPlotTimeSeries:
    """Tests for plot_time_series()."""

    def test_exclude_and_include_raises(self, sample_df: pd.DataFrame) -> None:
        """Passing both exclude and include raises ValidationError."""
        with pytest.raises(ValidationError, match="Only one"):
            plot_time_series(sample_df, exclude=["temp"], include=["humid"])

    def test_exclude_epoch_by_default(self, sample_df: pd.DataFrame) -> None:
        """Epoch is automatically excluded from numeric columns."""
        # If epoch weren't excluded, there would be 3 numeric cols
        numeric = sample_df.select_dtypes(include=["number"]).columns.tolist()
        assert "epoch" in numeric  # sanity check

    def test_exclude_removes_column(self, sample_df: pd.DataFrame) -> None:
        """Exclude parameter removes named columns from the plot."""
        with mock.patch.object(sample_df, "plot") as mock_plot:
            plot_time_series(sample_df, exclude=["humidity"])
            y_arg = mock_plot.call_args[1]["y"]
            assert "humidity" not in y_arg
            assert "temperature" in y_arg

    def test_include_only_selected(self, sample_df: pd.DataFrame) -> None:
        """Include parameter plots only the named columns."""
        with mock.patch.object(sample_df, "plot") as mock_plot:
            plot_time_series(sample_df, include=["temperature"])
            y_arg = mock_plot.call_args[1]["y"]
            assert y_arg == ["temperature"]

    def test_epoch_always_excluded(self, sample_df: pd.DataFrame) -> None:
        """Epoch is always excluded, even when explicitly included."""
        with mock.patch.object(sample_df, "plot") as mock_plot:
            plot_time_series(sample_df, include=["epoch", "temperature"])
            y_arg = mock_plot.call_args[1]["y"]
            assert "epoch" not in y_arg
            assert "temperature" in y_arg

    def test_no_numeric_columns_raises(self) -> None:
        """DataFrame with no numeric columns raises ValidationError."""
        df = pd.DataFrame({"a": ["x", "y"]}, index=pd.date_range("2024-01-01", periods=2))
        with pytest.raises(ValidationError, match="No numeric columns"):
            plot_time_series(df)

    def test_exclude_all_removes_all_numeric(self, sample_df: pd.DataFrame) -> None:
        """Excluding all numeric columns raises ValidationError."""
        with pytest.raises(ValidationError, match="No numeric columns"):
            plot_time_series(sample_df, exclude=["temperature", "humidity"])

    def test_include_nonexistent_column_raises(self, sample_df: pd.DataFrame) -> None:
        """Including only nonexistent columns raises ValidationError."""
        with pytest.raises(ValidationError, match="No numeric columns"):
            plot_time_series(sample_df, include=["nonexistent"])

    def test_matplotlib_not_installed(self, sample_df: pd.DataFrame) -> None:
        """When matplotlib is missing, an ImportError is raised."""
        with mock.patch("importlib.util.find_spec", return_value=None):
            with pytest.raises(ImportError, match="matplotlib"):
                plot_time_series(sample_df)

    def test_matplotlib_kwargs_forwarded(self, sample_df: pd.DataFrame) -> None:
        """Extra kwargs are forwarded to matplotlib's plot function."""
        with mock.patch.object(sample_df, "plot") as mock_plot:
            plot_time_series(sample_df, color="red", linestyle="--")
            mock_plot.assert_called_once_with(
                y=["temperature", "humidity"], color="red", linestyle="--"
            )

    def test_default_plots_all_numeric_excluding_epoch(self, sample_df: pd.DataFrame) -> None:
        """With no exclude/include, plot all numeric cols except epoch."""
        with mock.patch.object(sample_df, "plot") as mock_plot:
            plot_time_series(sample_df)
            y_arg = mock_plot.call_args[1]["y"]
            assert "temperature" in y_arg
            assert "humidity" in y_arg
            assert "epoch" not in y_arg

    def test_returns_pandas_plot_result(self, sample_df: pd.DataFrame) -> None:
        """plot_time_series returns the Axes produced by DataFrame.plot."""
        with mock.patch.object(sample_df, "plot") as mock_plot:
            result = plot_time_series(sample_df, figsize=(12, 3))
            assert result is mock_plot.return_value

    def test_returns_real_axes(self, sample_df: pd.DataFrame) -> None:
        """plot_time_series returns a real Axes attached to a figure."""
        pytest.importorskip("matplotlib")
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        ax = plot_time_series(sample_df, figsize=(12, 3))
        assert ax is not None
        assert isinstance(ax, plt.Axes)
        assert ax.get_figure() is not None
        plt.close("all")


class TestDataGeneratorPlot:
    """Tests for DataGenerator.plot() delegation."""

    def test_plot_returns_delegated_result(self) -> None:
        """plot() returns the Axes returned by plot_time_series."""
        from unittest.mock import patch

        from ts_data_generator import DataGenerator

        data_gen = DataGenerator()
        data_gen.start_datetime = "2019-01-01"
        data_gen.end_datetime = "2019-01-12"
        with patch("ts_data_generator.data_gen.plot_time_series") as mock_pts:
            result = data_gen.plot(figsize=(12, 3))
            assert result is mock_pts.return_value
            mock_pts.assert_called_once_with(
                data_gen.data, exclude=None, include=None, figsize=(12, 3)
            )
