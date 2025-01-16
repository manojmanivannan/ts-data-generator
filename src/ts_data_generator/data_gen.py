"""
Core DataGen class implementation
"""

from typing import Optional, Union, Dict, Set, List, Generator
from .schema.models import Metrics, Dimensions, Granularity
from .utils.trends import Trends
import pandas as pd
from datetime import datetime


class DataGen:
    """Main class for generating synthetic data"""

    def __init__(
        self,
        dimensions: List[Dimensions] = None,
        metrics: List[Metrics] = None,
        start_datetime: Optional[str] = None,
        end_datetime: Optional[str] = None,
        granularity: Granularity = Granularity.FIVE_MIN,
    ):
        """Initialize DataGen with empty data"""

        self._dimensions = dimensions or []  # Initialize to an empty set if None
        self._metrics = metrics or []  # Initialize to an empty set if None
        self._start_datetime = start_datetime
        self._end_datetime = end_datetime
        self._granularity = granularity
        self.metric_data = None
        self.dimension_data = None
        self.data = None

    def __repr__(self):
        return f"""DataGen Class
            dimensions  = {[d.to_json() for d in self._dimensions]}, 
            metrics     = {[m.to_json() for m in self._metrics]}, 
            start_datetime  = {self.start_datetime}, 
            end_datetime    = {self.end_datetime}, 
            granularity = {self.granularity})
            """

    @property
    def start_datetime(self):
        return self._start_datetime

    @start_datetime.setter
    def start_datetime(self, value: str):
        """Set start_datetime and validate it.

        Args:
            value (str): Start date in ISO format (YYYY-MM-DD).
        """
        if value is not None:
            try:
                datetime.fromisoformat(value)
            except ValueError:
                raise ValueError("Dates must be in ISO format (YYYY-MM-DD)")
        self._start_datetime = value

    @property
    def end_datetime(self):
        return self._end_datetime

    @end_datetime.setter
    def end_datetime(self, value: str):
        """Set end_datetime and validate it.

        Args:
            value (str): End date in ISO format (YYYY-MM-DD).
        """
        if value is not None:
            try:
                datetime.fromisoformat(value)
            except ValueError:
                raise ValueError("Dates must be in ISO format (YYYY-MM-DD)")
        self._end_datetime = value

    @property
    def granularity(self):
        if isinstance(self._granularity, Granularity):
            return self._granularity.value
        return self._granularity

    @granularity.setter
    def granularity(self, value: Granularity):
        """Set granularity and validate it.

        Args:
            value (str): Granularity in "5min", "H", "D".
        """
        if value is not None:
            try:
                Granularity(value)
            except ValueError:
                raise ValueError("Granularity must be 5min, H or D")
        self._granularity = value

    @property
    def dimensions(self):
        return {d.name: d for d in self._dimensions}

    @property
    def metrics(self):
        return {m.name: m for m in self._metrics}
    
    @property
    def trends(self):
        return {m.name: {t.name: t for t in m._trends} for m in self._metrics}

    def _validate_metrics(self) -> None:
        """Validate metrics format and logic.

        Raises:
            ValueError: If metrics are invalid
        """
        if not self.metrics:
            raise ValueError("metrics must be set")

    def _validate_dimensions(self) -> None:
        """Validate dimensions format and logic.

        Raises:
            ValueError: If dimensions are invalid
        """
        if not self.dimensions:
            raise ValueError("dimensions must be set")

        for d in self._dimensions:
            if not isinstance(d.function, Generator):
                raise ValueError(
                    f"{d.name} dimension function must be a generator object"
                )

    def _validate_dates(self) -> None:
        """Validate start_datetime and end_datetime format and logic.

        Raises:
            ValueError: If dates are invalid or start_datetime is after end_datetime
        """
        if not self.start_datetime:
            raise ValueError("start_datetime must be set")

        if not self.end_datetime:
            raise ValueError("end_datetime must be set")

        if (self.start_datetime is None) != (self.end_datetime is None):
            raise ValueError(
                "Both start_datetime and end_datetime must be either set or None"
            )

        start = datetime.fromisoformat(self.start_datetime)
        end = datetime.fromisoformat(self.end_datetime)

        if start > end:
            raise ValueError("start_datetime cannot be after end_datetime")

    def add_dimension(self, name: str, function) -> None:
        """
        Add a new dimension to the collection.

        A dimension represents an additional attribute or aspect of the dataset. Each dimension is
        identified by a unique name and associated with a function that generates its values.

        Args:
            name (str): The unique name of the dimension.
            function (int | str | Generator): A callable (e.g., generator function) that produces values for the dimension.

        Raises:
            ValueError: If a dimension with the same name already exists in the collection.

        Example:
            >>> def sample_generator():
            ...     while True:
            ...         yield "sample_value"
            ...
            >>> my_object.add_dimension(name="category", function=sample_generator())
        """
        dimension = Dimensions(name=name, function=function)
        # Raise error if self._dimensions already contains a dimension with the same name
        if dimension in self._dimensions:
            raise ValueError(f"Dimension with name {name} already exists")
        self._dimensions.append(dimension)

    def update_dimension(self, name: str, function) -> None:
        """
        Update an existing dimension in the DataGen instance.

        Allows updating the function associated with a dimension. The dimension is identified by its name.

        Args:
            name (str): The unique name of the dimension to update.
            function (int | str | Generator): int or string or callable (e.g., generator function) that produces values for the dimension.
                If None, the function will remain unchanged.

        Raises:
            ValueError: If the dimension with the specified name does not exist.
            ValueError: If the provided function is not a callable object.

        Example:
            ```python
            # Updating an existing dimension
            def new_generator():
                while True:
                    yield "new_value"

            data_gen.update_dimension(name="category", function=new_generator())
            ```
        """
        if name not in self.dimensions:
            raise ValueError(f"Dimension with name '{name}' does not exist.")

        dimension = self.dimensions[name]

        if function is not None:
            if (
                not isinstance(function, Generator)
                and not isinstance(function, int)
                and not isinstance(function, str)
                and not isinstance(function, float)
            ):
                raise ValueError(
                    "Provided function must be callable or int or float or string."
                )
            dimension.function = function

    def add_metric(
        self,
        name: str,
        trends: Set[Trends]
    ) -> None:
        """
        Add a metric to the DataGen instance.

        This method allows you to add a new metric with specified characteristics to the DataGen instance.
        The `function_type` determines the type of data generation (e.g., sine wave, constant value, etc.).
        For sine or cosine metrics, additional parameters (`frequency_in_hour`, `offset_in_minutes`, and `scale`)
        must be provided. For constant metrics, only `scale` is required.

        Args:
            name (str): The unique name of the metric.
            function_type (str): The type of function used for data generation.
                Must be one of ["sine", "cosine", "constant", "generator"].
            frequency_in_hour (Optional[float]): The frequency of oscillation in hours.
                Required for "sine" and "cosine".
            offset_in_minutes (Optional[float]): The phase offset in minutes.
                Required for "sine" and "cosine".
            scale (Optional[float]): The amplitude of the wave or the constant value.
                Required for all function types.

        Raises:
            ValueError: If a metric with the same name already exists.
            ValueError: If required parameters for the specified `function_type` are missing.

        Example:
            ```python
            # Adding a sine metric
            data_gen.add_metric(
                name="sine_metric",
                function_type="sine",
                frequency_in_hour=1.0,
                offset_in_minutes=15.0,
                scale=10.0
            )

            # Adding a constant metric
            data_gen.add_metric(
                name="constant_metric",
                function_type="constant",
                scale=5.0
            )
            ```
        """
        metric = Metrics(
            name=name,
            trends=trends
        )
        # Raise error if self._metrics already contains a metric with the same name
        for m in self._metrics:
            if name == m.name:
                raise ValueError(f"Metric with name '{name}' already exists")
        self._metrics.append(metric)

    def update_metric(
        self,
        name: str,
        function_value: Optional[Generator] = None,
        frequency_in_hour: Optional[float] = None,
        offset_in_minutes: Optional[float] = None,
        scale: Optional[float] = None,
    ) -> None:
        """
        Update an existing metric in the DataGen instance.

        Allows updating the characteristics of a metric. The metric is identified by its name.

        Args:
            name (str): The unique name of the metric to update.
            function_value (Optional[Generator]): A new generator function for the metric.
                Required if `function_type` is "generator".
            frequency_in_hour (Optional[float]): The new frequency of oscillation in hours.
                Required if `function_type` is "sine" or "cosine".
            offset_in_minutes (Optional[float]): The new phase offset in minutes.
                Required if `function_type` is "sine" or "cosine".
            scale (Optional[float]): The new amplitude or constant value. If None, the scale remains unchanged.

        Raises:
            ValueError: If the metric with the specified name does not exist.
            ValueError: If required parameters for the specified `function_type` are missing.

        Example:
            ```python
            # Updating an existing metric
            data_gen.update_metric(
                name="sine_metric",
                frequency_in_hour=2.0,
                scale=15.0
            )
            ```
        """
        if name not in self.metrics:
            raise ValueError(f"Metric with name '{name}' does not exist.")

        metric = self.metrics[name]


        if metric._function_type == "generator" and function_value is not None:
            metric._function_value = function_value
        elif metric._function_type in {"sine", "cosine"}:
            if frequency_in_hour is None or offset_in_minutes is None or scale is None:
                raise ValueError(
                    "frequency_in_hour, offset_in_minutes, and scale are required for sine or cosine."
                )
            metric._frequency_in_hour = frequency_in_hour
            metric._offset_in_minutes = offset_in_minutes
            metric._scale = scale
        elif metric._function_type == "constant":
            if function_value is None:
                raise ValueError("function_value is required for constant.")
            metric._function_value = function_value

    def generate_data(self, dimension_name: Optional[Union[str, List[str]]] = None, metric_name: Optional[Union[str, List[str]]] = None) -> pd.DataFrame:
        """Generate a sample DataFrame with unique IDs and values.

        Args:
            rows: Number of rows to generate. Must be positive.

        Returns:
            pd.DataFrame: Generated data with 'id' and 'value' columns

        Raises:
            ValueError: If rows is less than or equal to 0
            TypeError: If rows cannot be converted to int
        """
        # Validate dates
        self._validate_dates()
        self._validate_dimensions()
        self._validate_metrics()

        self._timestamps = pd.date_range(
            start=self.start_datetime,
            end=self.end_datetime,
            freq=self.granularity,
        )

        # create an empty dataframe with timestamps as index
        if not self.metric_data:
            self.metric_data = pd.DataFrame(index=self._timestamps)
        
        if not self.dimension_data:
            self.dimension_data = pd.DataFrame(index=self._timestamps)
        
        if not self.data:
            self.data = pd.DataFrame(index=self._timestamps)


        # Generate metric data 
        for _, metric in self.metrics.items():
            # recursively concant the dataframe to self.data
            self.metric_data = pd.concat([self.metric_data, metric.generate(self._timestamps)], axis=1)



        # Generate dimension data directly using a dictionary comprehension
        self.dimension_data = pd.DataFrame(
            {
                column_name: [
                    next(dimension.function) if not isinstance(dimension.function, (int, str)) else dimension.function
                    for _ in range(len(self._timestamps))
                ]
                for column_name, dimension in self.dimensions.items()
            },
            index=self._timestamps,
    )

        self.data = pd.concat([self.data, self.dimension_data, self.metric_data], axis=1)

