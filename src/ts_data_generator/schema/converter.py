import numpy as np
import pandas as pd
import scipy.optimize

class SchemaConverter:
    def __init__(self, csv_file_path, index_col, column_names=None):
        self.csv_file_path = csv_file_path
        self.column_names = column_names
        self.index_col = index_col
        self.data = self._load_data()
        

    def _load_data(self):
        if self.column_names:
            return pd.read_csv(self.csv_file_path, names=self.column_names,index_col=self.index_col)
        else:
            return pd.read_csv(self.csv_file_path, index_col=self.index_col)

    def impute_schema(self):
        schema = {}
        for column in self.data.columns:
            dtype = str(self.data[column].dtype)
            schema[column] = dtype
        return schema

    def analyze_numeric_trends(self, dataframe=None, columns=None, top_freq=3):
        """
        Analyzes numeric trends in a dataframe.
        Detects linear and sinusoidal components for numeric columns.

        Args:
            dataframe (pd.DataFrame): The input dataframe.
            columns (list, optional): List of column names to analyze. If None, all columns are considered.
            top_freq (int): The number of top frequencies to consider for sinusoidal components.

        Returns:
            dict: A dictionary with detected trends for each numeric column, including linear coefficients
                and dominant frequencies for sinusoidal components.
        """
        if dataframe is None:
            if isinstance(self.data, pd.DataFrame):
                dataframe = self.data
            else:
                raise ValueError("No valid dataframe provided or available in the instance.")

        trends = {}

        # Determine columns to analyze
        if columns is None:
            columns = dataframe.columns

        for column in columns:
            if column not in dataframe.columns:
                raise ValueError(f"Column '{column}' does not exist in the dataframe.")

            data = dataframe[column]

            # Ensure the column is numeric
            if not np.issubdtype(data.dtype, np.number):
                trends[column] = "Non-numeric column, skipped"
                continue

            # Drop NaN values
            data = data.dropna()

            if len(data) < 2:
                trends[column] = "Insufficient data points for trend analysis"
                continue

            # Linear trend analysis (same as before)
            x = np.arange(len(data))
            linear_coeffs = np.polyfit(x, data, 1)  # First-degree polynomial fit
            column_trends = {
                'linear': {
                    'slope': linear_coeffs[0],
                    'intercept': linear_coeffs[1]
                }
            }

            # Sinusoidal trend analysis (modified approach)
            fft = np.fft.fft(data - np.mean(data))  # Remove mean for better frequency detection
            frequencies = np.fft.fftfreq(len(data))
            magnitudes = np.abs(fft)
            phases = np.angle(fft)

            # Find the top frequencies (excluding the zero frequency)
            positive_freqs = frequencies[:len(frequencies)//2]
            positive_magnitudes = magnitudes[:len(magnitudes)//2]
            positive_phases = phases[:len(phases)//2]

            # Sort the magnitudes and get the indices of the top `top_freq` frequencies
            sorted_indices = np.argsort(positive_magnitudes[1:])[::-1] + 1  # Exclude zero-frequency component
            top_indices = sorted_indices[:top_freq]

            # Initialize guess parameters for the fitting function
            guess = []
            for idx in top_indices:
                guess.append(positive_magnitudes[idx])  # Amplitude
                guess.append(2 * np.pi * positive_freqs[idx])  # Angular frequency
                guess.append(positive_phases[idx])  # Phase
            guess.append(np.mean(data))  # Offset

            # Define the sinusoidal function for curve fitting
            def sinfunc(t, *params):
                result = 0
                for i in range(top_freq):
                    A = params[i * 3]  # Amplitude
                    w = params[i * 3 + 1]  # Angular frequency
                    p = params[i * 3 + 2]  # Phase
                    result += A * np.sin(w * t + p)
                return result + params[-1]  # Add offset

            # Perform curve fitting
            try:
                popt, _ = scipy.optimize.curve_fit(sinfunc, x, data, p0=guess)
            except RuntimeError:
                trends[column] = "Fitting failed"
                continue

            # Store the sinusoidal trend information
            sinusoidal_trends = []
            for i in range(top_freq):
                A = popt[i * 3]  # Amplitude
                w = popt[i * 3 + 1]  # Angular frequency
                p = popt[i * 3 + 2]  # Phase
                sinusoidal_trends.append({
                    'angular_frequency': w,
                    'magnitude': A,
                    'phase_offset': p
                })
            column_trends['sinusoidal'] = sinusoidal_trends

            trends[column] = column_trends

        return trends


    def construct_trend_column(self, column_name, trend_info):
        """
        Constructs a new column in the dataframe based on the provided trend information.

        Args:
            column_name (str): Name of the column to base the trend calculation on.
            trend_info (dict): Trend information containing linear and sinusoidal components.

        Returns:
            pd.Series: A new series representing the trend values.
        """
        trend_column_name = f"{column_name}_constructed"
        
        if column_name not in self.data.columns:
            raise ValueError(f"Column '{column_name}' does not exist in the dataframe.")

        data_length = len(self.data)
        x = np.arange(data_length)

        # Initialize trend with linear component
        try:
            trend = (trend_info['linear']['slope'] * x + trend_info['linear']['intercept'])
        except Exception as e:
            print("WARNING: unable to reconstruct trend. Amplitude or Frequency too high\nTry analysis with lower or higher top_freq")
            #TODO iteratively find the right top_freq. for now, set to np.nan
            self.data[trend_column_name] = np.nan
            return

        # Add sinusoidal components
        for sinusoid in trend_info['sinusoidal']:
            trend += (sinusoid['magnitude'] * 
                      np.sin(sinusoid['angular_frequency'] * x + sinusoid['phase_offset']))

        # Add the trend column to the dataframe
        
        self.data[trend_column_name] = trend