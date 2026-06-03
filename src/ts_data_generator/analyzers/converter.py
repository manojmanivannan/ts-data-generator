"""Schema analysis and reverse-engineering from existing CSV data.

The :class:`SchemaConverter` reads a CSV file and can:
- Impute column schemas (dtypes).
- Detect linear and sinusoidal trends via FFT and curve fitting.
- Construct new columns from detected trend parameters.
"""

import logging
import warnings

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SchemaConverter:
    """Read a CSV and analyze its schema and numeric trends.

    Args:
        csv_file_path: Path to the CSV file.
        index_col: Column index or name to use as the row index.
        column_names: Optional list of column names if the CSV has no header.

    Example:
        >>> converter = SchemaConverter("data.csv", index_col=0)
        >>> schema = converter.impute_schema()
        >>> trends = converter.analyze_numeric_trends(columns=["sales"])
    """

    def __init__(
        self,
        csv_file_path: str,
        index_col: int | str,
        column_names: list[str] | None = None,
    ) -> None:
        self.csv_file_path = csv_file_path
        self.column_names = column_names
        self.index_col = index_col
        self.data = self._load_data()

    def _load_data(self) -> pd.DataFrame:
        """Load the CSV into a DataFrame."""
        kwargs: dict = {"index_col": self.index_col}
        if self.column_names:
            kwargs["names"] = self.column_names
        return pd.read_csv(self.csv_file_path, **kwargs)

    def impute_schema(self) -> dict[str, str]:
        """Return a mapping of column name to pandas dtype string.

        Returns:
            Dict like ``{"product": "object", "sales": "float64"}``.
        """
        return {col: str(self.data[col].dtype) for col in self.data.columns}

    def analyze_numeric_trends(
        self,
        dataframe: pd.DataFrame | None = None,
        columns: list[str] | None = None,
        top_freq: int = 3,
    ) -> dict:
        """Detect linear and sinusoidal components in numeric columns.

        Uses FFT to identify dominant frequencies and scipy's curve_fit
        to fit a sum-of-sines model.

        Args:
            dataframe: DataFrame to analyze; defaults to ``self.data``.
            columns: Column names to analyze; defaults to all columns.
            top_freq: Number of top FFT frequencies to use as initial guess.

        Returns:
            Dict mapping column name to either a trend dict (with ``linear``
            and ``sinusoidal`` keys) or an error message string.
        """
        df = dataframe if dataframe is not None else self.data
        if not isinstance(df, pd.DataFrame):
            raise ValueError("No valid DataFrame provided or available.")

        if columns is None:
            columns = list(df.columns)

        trends: dict = {}
        for column in columns:
            if column not in df.columns:
                raise ValueError(f"Column {column!r} does not exist in the DataFrame.")

            data = df[column]
            if not np.issubdtype(data.dtype, np.number):
                trends[column] = "Non-numeric column, skipped"
                continue

            data = data.dropna()
            if len(data) < 2:
                trends[column] = "Insufficient data points for trend analysis"
                continue

            try:
                column_trends = self._fit_column(data.values, top_freq)
                trends[column] = column_trends
            except Exception:
                logger.exception("Trend fitting failed for column %r.", column)
                trends[column] = "Fitting failed"

        return trends

    def _fit_column(self, values: np.ndarray, top_freq: int) -> dict:
        """Fit linear + sinusoidal model to a 1-D numeric array.

        Args:
            values: 1-D array of numeric values.
            top_freq: Number of top frequencies to use.

        Returns:
            Dict with ``linear`` and ``sinusoidal`` keys.
        """
        try:
            import scipy.optimize  # lazy import — scipy is optional
        except ImportError:
            raise ImportError(
                "The 'scipy' library is required for this operation. "
                "Install with: uv add 'ts-data-generator[imputer]'"
            ) from None

        n = len(values)
        x = np.arange(n)
        linear_coeffs = np.polyfit(x, values, 1)
        column_trends: dict = {
            "linear": {
                "slope": float(linear_coeffs[0]),
                "intercept": float(linear_coeffs[1]),
            }
        }

        demeaned = values - np.mean(values)
        fft = np.fft.fft(demeaned)
        frequencies = np.fft.fftfreq(n)
        magnitudes = np.abs(fft)
        phases = np.angle(fft)

        half = n // 2
        pos_freqs = frequencies[:half]
        pos_mags = magnitudes[:half]
        pos_phases = phases[:half]

        sorted_indices = np.argsort(pos_mags[1:])[::-1] + 1
        top_indices = sorted_indices[:top_freq]

        guess = []
        for idx in top_indices:
            guess.extend([pos_mags[idx], 2 * np.pi * pos_freqs[idx], pos_phases[idx]])
        guess.append(np.mean(values))

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", scipy.optimize.OptimizeWarning)
                warnings.simplefilter("ignore", RuntimeWarning)
                popt, _ = scipy.optimize.curve_fit(self._sinfunc, x, values, p0=guess, maxfev=10000)
        except (RuntimeError, TypeError):
            raise

        num_fitted = (len(popt) - 1) // 3
        sinusoidal_trends = []
        for i in range(num_fitted):
            sinusoidal_trends.append(
                {
                    "angular_frequency": float(popt[i * 3 + 1]),
                    "magnitude": float(popt[i * 3]),
                    "phase_offset": float(popt[i * 3 + 2]),
                }
            )
        column_trends["sinusoidal"] = sinusoidal_trends

        return column_trends

    @staticmethod
    def _sinfunc(t: np.ndarray, *params: float) -> np.ndarray:
        """Sum-of-sines with offset: Σ A_i sin(w_i t + p_i) + offset."""
        result = np.zeros_like(t, dtype=float)
        num_components = len(params) // 3
        for i in range(num_components):
            a = params[i * 3]
            w = params[i * 3 + 1]
            p = params[i * 3 + 2]
            result += a * np.sin(w * t + p)
        return result + params[-1]

    def construct_trend_column(self, column_name: str, trend_info: dict) -> None:
        """Build a new column from trend parameters.

        Creates ``{column_name}_constructed`` with values from the linear
        and sinusoidal components.

        Args:
            column_name: Base column name.
            trend_info: Dict with ``linear`` and optional ``sinusoidal`` keys.

        Raises:
            ValueError: If ``column_name`` doesn't exist in the DataFrame.
        """
        trend_column_name = f"{column_name}_constructed"

        if column_name not in self.data.columns:
            raise ValueError(f"Column {column_name!r} does not exist in the DataFrame.")

        n = len(self.data)
        x = np.arange(n)

        try:
            linear = trend_info.get("linear", {})
            trend = np.asarray(
                linear.get("slope", 0) * x + linear.get("intercept", 0),
                dtype=float,
            )
        except Exception:
            logger.warning(
                "Unable to reconstruct linear trend for column %r. "
                "Amplitude or frequency may be too high. "
                "Try a different top_freq value.",
                column_name,
            )
            self.data[trend_column_name] = np.nan
            return

        for sinusoid in trend_info.get("sinusoidal", []):
            trend += sinusoid["magnitude"] * np.sin(
                sinusoid["angular_frequency"] * x + sinusoid["phase_offset"]
            )

        self.data[trend_column_name] = trend
