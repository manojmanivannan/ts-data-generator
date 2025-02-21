from pydantic import BaseModel
from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar, Generator, Literal, Optional, Union, Set
from enum import Enum
from ..utils.functions import auto_generate_name
from ..utils.trends import Trends
import pandas as pd
import numpy as np

T = TypeVar("T")


class Granularity(Enum):
    FIVE_MIN = "5min"
    HOURLY = "h"
    DAILY = "D"
    ONE_MIN = "min"
    ONE_SECOND = "s"


class Metrics(ABC):
    def __init__(
        self,
        name: str = "default",
        trends: Set[Trends] = []
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
        self._trends = trends

    @property
    def name(self) -> str:
        """Get the name of the metric."""
        return self._name
    
    @property
    def trends(self) -> Set[Trends]:
        """Get the trends of the metric."""
        return self._trends

    def generate(self, timestamps) -> pd.DataFrame:
        """Generate data for this metric.

        Args:
            timestamps: List of timestamps from pd.date_range
        """

        data = np.zeros(len(timestamps))

        for t in self._trends:
            data += t.generate(timestamps)

        self._data = pd.DataFrame(data, columns=[self._name], index=timestamps)
        return self._data


    def __repr__(self):
        # drop few keys from the dictionary
        json_data = self.to_json()

        return str(json_data)

    # add a function to represent the metric in json format
    def to_json(self):
        return {
            "name": self._name,
            "trends": [t._name for t in self._trends],
        }


class Dimensions(ABC):
    def __init__(self, name: Union[str,list], function: Union[int, str, float, Generator]):
        """Initialize a dimension with a name and value generation function.

        Args:
            name: Name of the dimension
            function: Function that generates values for this dimension
        """
        self._name = name
        self._function = function
        self._data = None
        # self._position = position

    @property
    def data(self) -> pd.Series:
        return self._data

    @property
    def name(self) -> Union[str,list]:
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
            and not isinstance(value, list)
        ):
            raise ValueError(
                "function must be a generator object or int or str or float"
            )
        self._function = value

    def generate(self, timestamps) -> pd.DataFrame:
        """Create a generator that yields dimension values.

        """
        # try:
        data = [list(next(self._function)) if isinstance(self._name, list) else [next(self._function)]
                for _ in timestamps]

        columns = self._name if isinstance(self._name, list) else [self._name]
        # except TypeError:
        #     data = [next(self._function)  for _ in timestamps]


        self._data = pd.DataFrame(data, columns=columns, index=timestamps)
        return self._data

    def __eq__(self, other: object) -> bool:
        """Enable equality comparison for set operations."""
        if not isinstance(other, Dimensions):
            raise NotImplementedError
        return self._name == other.name

    def __hash__(self) -> int:
        """Enable hashing for set operations."""
        return hash(self._name)

    # add a function to represent the dimension in json format
    def to_json(self):
        return {"name": self.name, "function": self.function.__repr__().split(' at ')[0]}


class MultiItems(ABC):
    def __init__(self, names: list, function: Union[int, str, float, Generator]):
        """Initialize a dimension with a name and value generation function.

        Args:
            name: Name of the dimension
            function: Function that generates values for this dimension
        """
        self._names = names
        self._function = function
        self._data = None
        # self._position = position

    @property
    def data(self) -> pd.Series:
        return self._data

    @property
    def names(self) -> list:
        """Get the name of the dimension."""
        return self._names

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
            and not isinstance(value, list)
        ):
            raise ValueError(
                "function must be a generator object or int or str or float"
            )
        self._function = value

    def generate(self, timestamps) -> pd.DataFrame:
        """Create a generator that yields dimension values.

        """
        # try:
        data = [list(next(self._function)) for _ in timestamps]


        self._data = pd.DataFrame(data, columns=self._names, index=timestamps)
        return self._data

    def __eq__(self, other: object) -> bool:
        """Enable equality comparison for set operations."""
        if not isinstance(other, MultiItems):
            raise NotImplementedError
        return self._names == other.names

    def __hash__(self) -> int:
        """Enable hashing for set operations."""
        return hash(self._names)

    # add a function to represent the dimension in json format
    def to_json(self):
        return {"names": self.names, "function": self.function.__repr__().split(' at ')[0]}
