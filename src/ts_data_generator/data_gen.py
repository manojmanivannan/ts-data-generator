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
        self.metric_data = pd.DataFrame()
        self.dimension_data = pd.DataFrame()
        self.data = pd.DataFrame()

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
        if self._start_datetime and self._end_datetime:
            self._generate_data()

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
        if self._start_datetime and self._end_datetime:
            self._generate_data()

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
            function (int | float | str | Generator): A callable (e.g., generator function) that produces values for the dimension.

        Raises:
            ValueError: If a dimension with the same name already exists in the collection.

        Example:
            >>> def sample_generator():
            ...     while True:
            ...         yield "sample_value"
            ...
            >>> my_object.add_dimension(name="category", function=sample_generator())
        """
        # validate the function
        if not isinstance(function, Union[int,float,str,Generator]):
            raise ValueError(f'Function of the dimension {name} has to be int, float, str or generator object')
        
        dimension = Dimensions(name=name, function=function)
        # Raise error if self._dimensions already contains a dimension with the same name
        if dimension in self._dimensions:
            raise ValueError(f"Dimension with name {name} already exists")
        self._dimensions.append(dimension)
        self._generate_data()

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

    def remove_dimension(self, name: str) -> None:
        """
        Remove the dimension from the data generator by its name

        Args:
            name (str): The name of the dimension to remove.

        Raises:
            ValueError: If the dimension with the specified name does not exist.

        Example:
            ```python
            data_gen.remove_dimension(name="category")
            ```
        """
        if name in self.dimensions:
            # update the data
            self.data = self.data.drop([name],axis=1)
            

        # drop the dimension from dimension list
        self._dimensions = [d for d in self._dimensions if d.name != name]


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
        self._generate_data()

    def remove_metric(self, name: str) -> None:
        """
        Remove the metric from the data generator by its name

        Args:
            name (str): The name of the metric to remove.

        Raises:
            ValueError: If the metric with the specified name does not exist.

        Example:
            ```python
            data_gen.remove_metric(name="category")
            ```
        """
        if name in self.metrics:
            # update the data
            self.data = self.data.drop([name],axis=1)

        # drop the dimension from dimension list
        self._metrics = [d for d in self._metrics if d.name != name]



    def _generate_data(self, dimension_name: Optional[Union[str, List[str]]] = None, metric_name: Optional[Union[str, List[str]]] = None) -> pd.DataFrame:
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

        self._timestamps = pd.date_range(
            start=self.start_datetime,
            end=self.end_datetime,
            freq=self.granularity,
        )

        # create an empty dataframe with timestamps as index
        if self.metric_data.empty:
            self.metric_data = pd.DataFrame(index=self._timestamps)
        
        if self.dimension_data.empty:
            self.dimension_data = pd.DataFrame(index=self._timestamps)
        
        if self.data.empty:
            self.data = pd.DataFrame(index=self._timestamps)
        else:
            # if data present and if there is change in timestamp ranges, reset dimension, metric and data
            if len(self.data) != len(self._timestamps):
                # Clear existing data to ensure full regeneration
                self.metric_data = pd.DataFrame(index=self._timestamps)
                self.dimension_data = pd.DataFrame(index=self._timestamps)
                self.data = pd.DataFrame(index=self._timestamps)



        # Generate metric data 
        for _, metric in self.metrics.items():
            
            # only proceed if metric name is not in the dataset
            if (not metric.name in self.data.columns):
                # recursively concant the dataframe to self.data
                
                self.metric_data = pd.concat([self.metric_data, metric.generate(self._timestamps)], axis=1)

            
            # if the metric is already in dataset, ignore with an empty dataframe
            else:
                self.metric_data = pd.DataFrame(index=self._timestamps)

        dimension_data_dict = {}
        for column_name, dimension in self.dimensions.items():
            
            # only proceed if dimension name is not in the dataset
            if not column_name in self.data.columns:
                column_data = []
                for _ in range(len(self._timestamps)):

                    # if the dimension.function is generator object
                    if not isinstance(dimension.function, (int, str)):
                        column_data.append(next(dimension.function))
                    
                    else: # else the dimension.function is a constant integer or string
                        column_data.append(dimension.function)
                
                dimension_data_dict[column_name] = column_data
            

        self.dimension_data = pd.DataFrame(dimension_data_dict, index=self._timestamps)

        self.data = pd.concat([self.data, self.dimension_data, self.metric_data], axis=1)

    def plot(self, exclude: List[str] = [], include: List[str] = []):
        """
        Plots the data based on the specified inclusion and exclusion criteria.
        Parameters:
        exclude (List[str]): A list of strings specifying the data columns to exclude from the plot.
        include (List[str]): A list of strings specifying the data columns to include in the plot.
        Returns:
        None
        """

        if exclude and include:
            raise ValueError("Only one of 'exclude' or 'include' should be provided, not both.")
        
        if exclude:
            self.data.plot(y=[col for col in self.data.columns if col not in exclude])
        
        if include:
            self.data.plot(y=[col for col in self.data.columns if col in include])

