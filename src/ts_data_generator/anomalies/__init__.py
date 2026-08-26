"""Anomaly injection package.

Defines the abstract :class:`Anomaly` base and the built-in injectors:
:class:`PointAnomaly` (isolated value spikes), :class:`ConceptDrift`
(gradual distribution-level regime shifts via :class:`DriftSegment`),
and :class:`MissingData` (NaN gaps). Pass instances to
:meth:`~ts_data_generator.DataGen.add_metric` through ``anomalies=`` to
apply them after trend composition.
"""

from ts_data_generator.anomalies.base import Anomaly
from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment
from ts_data_generator.anomalies.missing import MissingData
from ts_data_generator.anomalies.point import PointAnomaly

__all__ = ["Anomaly", "ConceptDrift", "DriftSegment", "MissingData", "PointAnomaly"]
