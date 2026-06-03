"""Custom exception classes for the ts-data-generator library."""


class DataGeneratorError(Exception):
    """Base exception for all data generator errors."""


class DimensionError(DataGeneratorError):
    """Raised when a dimension operation fails (add, update, remove, validate)."""


class MetricError(DataGeneratorError):
    """Raised when a metric operation fails (add, remove, validate)."""


class MultiItemError(DataGeneratorError):
    """Raised when a multi-item operation fails (add, remove, validate)."""


class ValidationError(DataGeneratorError):
    """Raised when input validation fails (dates, granularity, function types)."""


class AggregationError(DataGeneratorError):
    """Raised when data aggregation fails (invalid granularity, unsupported operation)."""


class ConfigurationError(DataGeneratorError):
    """Raised when configuration is invalid (missing fields, bad JSON)."""


class RegistryError(DataGeneratorError):
    """Raised when a registry lookup fails (missing name, wrong base class)."""
