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
            freq (float): Frequency of the sinusoidal wave.
            phase (float): Phase offset of the sinusoidal wave.
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

    def generate(self, timestamps) -> np.ndarray:
        """
        Generate a sinusoidal wave with added noise.
        
        Parameters:
            amplitude (float): Amplitude of the sinusoidal wave.
            freq (float): Frequency of the sinusoidal wave.
            phase (float): Phase offset of the sinusoidal wave.
            noise_level (float): Standard deviation of the noise.
            
        Returns:
            y (numpy.ndarray): Sinusoidal wave with noise.
        """

        # frequency is in hours, phase is in minutes,
        # convert frequency to period
        frequency = 1/self._freq  # Set frequency to oscillate once every hour
        phase_hours = self._phase / 60  # Convert phase to hours
        noise_level = self._noise_level * 0.1 # Add 10% noise

        base_wave = np.zeros(len(timestamps))

        # Convert phase from minutes to hours
        
        base_wave += self._amplitude *np.sin(2 * np.pi * frequency * (timestamps.hour + timestamps.minute / 60)) + phase_hours

    
        noise = np.random.normal(0, noise_level, len(timestamps))  # Generate noise
        base_wave += noise  # Add noise to the wave
        
        # Add noise to the wave
        y = base_wave #+ noise
        
        return y
    

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
        if limit < 1 or limit > 100:
            raise ValueError("Limit must be within the range of 1 and 100")
        self._limit = limit

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

        if timestamps.freq == "5T":  # 5-minute granularity
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

