"""ts-data-generator — Synthetic time series data generation library.

Generate realistic time series datasets with configurable dimensions,
metrics, and trends. Provides both a Python API (:class:`DataGen`)
and a CLI (``tsdata``).

Quickstart::

    from ts_data_generator import DataGen
    from ts_data_generator.utils.trends import SinusoidalTrend
    from ts_data_generator.utils.functions import random_choice

    dg = DataGen()
    dg.start_datetime = "2024-01-01"
    dg.end_datetime = "2024-01-07"
    dg.to_granularity("h")
    dg.add_dimension("region", random_choice(["US", "EU", "AP"]))
    dg.add_metric("temperature", {SinusoidalTrend(amplitude=10, freq=24)})
    print(dg.data.head())
"""

from ts_data_generator._version import __version__
from ts_data_generator.data_gen import DataGen

__all__ = ["DataGen", "__version__"]
