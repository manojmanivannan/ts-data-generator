"""Anomaly injection package."""

from ts_data_generator.anomalies.base import Anomaly
from ts_data_generator.anomalies.point import PointAnomaly

__all__ = ["Anomaly", "PointAnomaly"]
