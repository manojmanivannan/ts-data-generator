from pydantic import BaseModel
from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar, Generator, Literal, Optional, Union
from enum import Enum
from ..utils.functions import auto_generate_name
from ..utils.trends import generate_time_series_wave_with_noise

T = TypeVar("T")


class Granularity(Enum):
    FIVE_MIN = "5min"
    HOURLY = "H"
    DAILY = "D"


class Metrics(ABC):
    def __init__(
        self,
        name: str = "default",
        function_type: Literal["sine", "cosine", "constant", "generator"] = "sine",
        function_value: Optional[Union[int, str, Generator]] = None,
        frequency_in_hour: Optional[int] = 24,
        offset_in_minutes: Optional[int] = 0,
        scale: Optional[float] = 1,
    ):
        """
        Initialize a Metrics object.

        Args:
            name (str): Name of the metric.
            function_type (Literal): Type of function to generate data (e.g., "sine", "cosine", "constant", "generator").
            function_value (Optional[Generator]): A generator function for this metric; required if function_type is "generator".
            frequency_in_hour (Optional[str]): Frequency of trend to oscillate in hours; required if function_type in [sine, cosine].
            offset_in_minutes (Optional[str]): Phase offset of trend in minutes; required if function_type in [sine, cosine].
            scale (Optional[float]): Amplitude of the wave; required if function_type in [sine, cosine].
        """
        self._name = (
            auto_generate_name(category="metric") if name == "default" else name
        )
        self._function_type = function_type

        # Validate required arguments for sine and cosine
        if function_type in {"sine", "cosine"}:
            if frequency_in_hour is None or offset_in_minutes is None or scale is None:
                raise ValueError(
                    "frequency_in_hour, offset_in_minutes, and scale are required for sine or cosine"
                )
            self._frequency_in_hour = frequency_in_hour
            self._offset_in_minutes = offset_in_minutes
            self._scale = scale
            self._function_value = None

        elif function_type == "generator":
            if function_value is None:
                raise ValueError("function_value is required for generator")
            self._function_value = function_value
            self._frequency_in_hour = None
            self._offset_in_minutes = None
            self._scale = None

        elif function_type == "constant":
            if function_value is None:
                raise ValueError("scale is required for constant")
            if not isinstance(function_value, (int, float)):
                raise ValueError("function_value must be an integer or float")
            self._function_value = function_value

            self._frequency_in_hour = None
            self._offset_in_minutes = None
            self._scale = None

    def generate_wave_data(self, timestamps, function_type):
        """Generate data for this metric.

        Args:
            timestamps: List of timestamps from pd.date_range
        """

        self._timestamps, self._data = generate_time_series_wave_with_noise(
            amplitude=self._scale,
            freq=self._frequency_in_hour,
            phase=self._offset_in_minutes,
            timestamps=timestamps,
            noise_level=self._scale,
        )

    def _create_generator(self, timestamps) -> Generator[float, None, None]:
        """Create a generator that yields time series data.

        The generator creates a sinusoidal wave with the following characteristics:
        - Period: Based on frequency_in_hour (e.g., 1 hour per oscillation)
        - Phase: Based on offset_in_minutes
        - Amplitude: Based on scale
        - Added noise: 10% of scale

        Returns:
            Generator yielding (time_array, values_array)
        """
        if self._function_type in ["sine", "cosine"]:
            self.generate_wave_data(timestamps, self._function_type)

        elif self._function_type == "constant":
            self._timestamps = timestamps
            self._data = [self._function_value] * len(timestamps)

        elif self._function_type == "generator":
            self._timestamps = timestamps
            self._data = self._function_value
            # return self

        # TODO: Maybe this generator() function and return statement is not required.
        def generator():
            while True:
                for y in self._data:
                    yield y

        return generator()

    @property
    def name(self):
        return self._name

    @property
    def frequency_in_hour(self):
        return self._frequency_in_hour

    @property
    def offset_in_minutes(self):
        return self._offset_in_minutes

    @property
    def scale(self):
        return self._scale

    @property
    def generator(self):
        """Get the time series generator."""
        return self._generator

    def __repr__(self):
        # drop few keys from the dictionary
        json_data = self.to_json()
        json_data.pop("data")

        return str(json_data)

    # add a function to represent the metric in json format
    def to_json(self):
        return {
            "name": self.name,
            "function_type": self._function_type,
            "function_value": self._function_value,
            "frequency_in_hour": self.frequency_in_hour,
            "offset_in_minutes": self.offset_in_minutes,
            "scale": self.scale,
            "data": self._data,
        }


class Dimensions(ABC):
    def __init__(self, name: str, function: Union[int, str, float, Generator]):
        """Initialize a dimension with a name and value generation function.

        Args:
            name: Name of the dimension
            function: Function that generates values for this dimension
        """
        self._name = name
        self._function = function

    @property
    def name(self) -> str:
        """Get the name of the dimension."""
        return self._name

    @property
    def function(self) -> Union[int, str, float, Generator]:
        """Get the value generation function."""
        return self._function

    @function.setter
    def function(self, value: Union[int, str, float, Generator]) -> None:
        """Set the value generation function.

        Args:
            value: Function that generates values for this dimension. Should be a generator object
        """
        # validate if value is a generator object
        if (
            not isinstance(value, int)
            and not isinstance(value, str)
            and not isinstance(value, float)
            and not isinstance(value, Generator)
        ):
            raise ValueError(
                "function must be a generator object or int or str or float"
            )
        self._function = value

    def _create_generator(self, timestamps) -> Generator[T, None, None]:
        """Create a generator that yields dimension values.

        Args:
            timestamps: List of timestamps from pd.date_range

        """
        pass

    def __eq__(self, other: object) -> bool:
        """Enable equality comparison for set operations."""
        if not isinstance(other, Dimensions):
            return NotImplemented
        return self._name == other.name

    def __hash__(self) -> int:
        """Enable hashing for set operations."""
        return hash(self._name)

    # add a function to represent the dimension in json format
    def to_json(self):
        return {"name": self.name, "function": self.function.__repr__()}
