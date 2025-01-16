import numpy as np
from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar, Generator, Literal, Optional, Union
import pandas as pd

class Trends(ABC):
    def __init__(
            self,
            name: str = "default",

    ):
        """
        Initialize a Trends object.

        Args:
            name (str): Name of the trend.

        """
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def generate(
        self,
        timestamps: pd.DatetimeIndex,
    ) -> np.array:
        """
        Generate a time series trend.

        Args:
            start_datetime (Union[str, pd.Timestamp]): Start datetime of the trend.
            end_datetime (Union[str, pd.Timestamp]): End datetime of the trend.

        """
        pass

        
class SinusoidalTrend(Trends):
    def __init__(
        self,
        name: str = "default",
        amplitude: float = 1,
        freq: float = 1,
        phase: float = 0,
        noise_level: float = 0,
    ):
        """
        Initialize a SinusoidalTrend object.

        Args:
            name (str): Name of the trend.
            amplitude (float): Amplitude of the sinusoidal wave.
            freq (float): Frequency of the sinusoidal wave in days.
            phase (float): Phase offset of the sinusoidal wave in hours.
            noise_level (float): Standard deviation of the noise.
        """
        super().__init__(name)
        self._amplitude = amplitude
        self._freq = freq
        self._phase = phase
        self._noise_level = noise_level

    @property
    def amplitude(self) -> float:
        return self._amplitude
    
    @property
    def freq(self) -> float:
        return self._freq
    
    @property
    def phase(self) -> float:
        return self._phase
    
    @property
    def noise_level(self) -> float:
        return self._noise_level

    def generate(self, timestamps: pd.DatetimeIndex) -> np.ndarray:
        """
        Generate a sinusoidal wave with added noise.

        Args:
            timestamps (pd.DatetimeIndex): Array of timestamps.

        Returns:
            np.ndarray: Sinusoidal wave with noise.
        """
        # Calculate the time in fractional days
        time_in_days = (timestamps - timestamps[0]).total_seconds() / (24 * 3600)

        # Convert phase to fractional days
        phase_in_days = self._phase / 24.0

        # Calculate the sinusoidal wave
        base_wave = self._amplitude * np.sin(2 * np.pi * (1/self._freq) * (time_in_days + phase_in_days))

        # Add noise
        noise = np.random.normal(0, self._noise_level, len(timestamps))
        sinusoidal_wave = base_wave + noise

        return sinusoidal_wave
    
    

class LinearTrend(Trends):
    def __init__(
        self,
        name: str = "default",
        offset: float = 0.0,
        noise_level: float = 0.0,
        limit: float = 2.0,
    ):
        """
        Initialize a LinearTrend object.

        Args:
            name (str): Name of the trend.
            limit (float): Upper limit of the linear trend.
            offset (float): Intercept (b) of the linear trend.
            noise_level (float): Standard deviation of the noise.
        """
        super().__init__(name)

        self._offset = offset
        self._noise_level = noise_level
        # check if limit is within the range of 1 and 100
        if limit < 1 or limit > 1000:
            raise ValueError("Limit must be within the range of 1 and 100")
        self._limit = limit * 10

    @property
    def limit(self) -> float:
        return self._limit

    @property
    def offset(self) -> float:
        return self._offset

    @property
    def noise_level(self) -> float:
        return self._noise_level

    def generate(self, timestamps) -> np.ndarray:
        """
        Generate a linear trend with optional noise.

        Args:
            timestamps (pd.DatetimeIndex): Array of timestamps.

        Returns:
            np.ndarray: Generated linear trend values.
        """
        # Calculate time differences in the appropriate unit
        time_deltas = (timestamps - timestamps[0])

        if timestamps.freq == "5min":  # 5-minute granularity
            time_numeric = time_deltas.total_seconds() / 60.0  # Convert to minutes
        elif timestamps.freq == "H":  # Hourly granularity
            time_numeric = time_deltas.total_seconds() / 3600.0  # Convert to hours
        elif timestamps.freq == "D":  # Daily granularity
            time_numeric = time_deltas.days  # Use days directly
        else:
            raise ValueError("Unsupported granularity. Use 5T, H, or D.")

        self._coefficient = np.radians(np.sin(self._limit/len(time_numeric)))

        # Calculate the linear trend
        base_trend = self._coefficient * time_numeric + self._offset

        # Add noise
        noise = np.random.normal(0, self._noise_level, len(timestamps))
        trend_with_noise = base_trend + noise

        return trend_with_noise

class WeekendTrend(Trends):
    def __init__(
        self,
        name: str = "default",
        weekend_effect: float = 1.0,
        direction: Literal["up", "down"] = "up",
        noise_level: float = 0.0,
        limit: float = 10.0,
    ):
        """
        Initialize a WeekendTrend object.

        Args:
            name (str): Name of the trend.
            weekend_effect (float): Magnitude of the weekend effect.
            direction (Literal["up", "down"]): Direction of the weekend effect.
            noise_level (float): Standard deviation of the noise.
            limit (float): Maximum value for the weekend effect.
        """
        super().__init__(name)
        self._weekend_effect = weekend_effect
        self._direction = direction
        self._noise_level = noise_level
        self._limit = limit

    @property
    def weekend_effect(self) -> float:
        return self._weekend_effect

    @property
    def direction(self) -> str:
        return self._direction

    @property
    def noise_level(self) -> float:
        return self._noise_level

    @property
    def limit(self) -> float:
        return self._limit

    def generate(self, timestamps: pd.DatetimeIndex) -> np.ndarray:
        """
        Generate a weekend-specific trend.

        Args:
            timestamps (pd.DatetimeIndex): Array of timestamps.

        Returns:
            np.ndarray: Trend values with weekend effect.
        """
        # Initialize the trend with zeros
        trend = np.zeros(len(timestamps))

        # Determine if each timestamp falls on a weekend (Saturday or Sunday)
        is_weekend = timestamps.weekday >= 5

        # Apply the weekend effect
        weekend_adjustment = self._weekend_effect if self._direction == "up" else -self._weekend_effect
        trend[is_weekend] = weekend_adjustment


        # Clip the trend to the specified limit
        trend = np.clip(trend, -self._limit, self._limit)

        # Add noise
        noise = np.random.normal(0, self._noise_level, len(timestamps))
        trend += noise

        return trend

class StockTrend(Trends):
    def __init__(
        self,
        name: str = "default",
        amplitude: float = 15.0,
        direction: Literal["up", "down"] = "up",
        noise_level: float = 0.0,
    ):
        """
        Initialize a StockTrend object.

        Args:
            name (str): Name of the trend.
            amplitude (float): Amplitude of the trend.
            direction (str): Direction of the trend ('up' or 'down').
            noise_level (float): Standard deviation of the noise.

        Raises:
            ValueError: If the end value is not consistent with the direction.
        """
        super().__init__(name)
        self._amplitude = amplitude
        self._direction = direction
        self._noise_level = noise_level


    @property
    def amplitude(self) -> float:
        return self._amplitude

    @property
    def direction(self) -> str:
        return self._direction

    @property
    def noise_level(self) -> float:
        return self._noise_level


    def generate(self, timestamps: pd.DatetimeIndex) -> np.ndarray:
        """
        Generate a stock price-like trend.

        Args:
            timestamps (pd.DatetimeIndex): Array of timestamps.

        Returns:
            np.ndarray: Generated stock price trend values.
        """
        # Initialize the trend array
        num_steps = len(timestamps)
        trend = np.zeros(num_steps)
        trend[0] = 0

        # Calculate the drift per step to guide the trend toward the end value
        drift_per_step = self._amplitude / num_steps

        # Generate the trend using a random walk
        for i in range(1, num_steps):
            # Calculate random fluctuation (volatility)
            volatility = np.random.normal(0, self._noise_level)

            # Add drift and volatility to the previous value
            step = drift_per_step + volatility
            trend[i] = trend[i - 1] + step


        time_in_days = (timestamps - timestamps[0]).total_seconds() / (24 * 3600)
        base_wave = (
                    self._amplitude * np.sin(2 * np.pi * (time_in_days/5)) - self._amplitude +
                    2*self._amplitude * np.sin(2 * np.pi * (time_in_days/30)) - self._amplitude + 
                    2*self._amplitude * np.sin(2 * np.pi * (time_in_days/45))+ 
                    3*self._amplitude * np.sin(2 * np.pi * (time_in_days/180))
                )
        if self._direction =='down':
            base_wave = base_wave[::-1]

        return base_wave + trend
    