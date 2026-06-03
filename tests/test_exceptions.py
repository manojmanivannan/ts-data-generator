"""Tests for custom exception classes."""

from __future__ import annotations

import pytest

from ts_data_generator.exceptions import (
    AggregationError,
    ConfigurationError,
    DataGeneratorError,
    DimensionError,
    MetricError,
    MultiItemError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Every custom exception inherits from DataGeneratorError."""

    @pytest.mark.parametrize("exc_cls,msg", [
        (DimensionError, "dimension error"),
        (MetricError, "metric error"),
        (MultiItemError, "multi item error"),
        (ValidationError, "validation error"),
        (AggregationError, "aggregation error"),
        (ConfigurationError, "config error"),
    ])
    def test_subclass_of_data_generator_error(self, exc_cls: type, msg: str) -> None:
        assert issubclass(exc_cls, DataGeneratorError)

    def test_data_generator_error_is_subclass_of_exception(self) -> None:
        assert issubclass(DataGeneratorError, Exception)


class TestExceptionMessage:
    """Testing message propagation."""

    @pytest.mark.parametrize("exc_cls,msg", [
        (DataGeneratorError, "base error"),
        (DimensionError, "dimension 'x' not found"),
        (MetricError, "metric 'y' not found"),
        (MultiItemError, "multi-item 'z' already exists"),
        (ValidationError, "invalid date format"),
        (AggregationError, "cannot aggregate to coarser granularity"),
        (ConfigurationError, "missing 'type' field in config"),
    ])
    def test_message_preserved(self, exc_cls: type, msg: str) -> None:
        exc = exc_cls(msg)
        assert str(exc) == msg

    def test_empty_message(self) -> None:
        exc = DataGeneratorError()
        assert str(exc) == ""


class TestExceptionCatch:
    """Catching the base exception catches all subclasses."""

    def test_catch_base_catches_dimension_error(self) -> None:
        try:
            raise DimensionError("test")
        except DataGeneratorError as e:
            assert isinstance(e, DimensionError)

    def test_catch_base_catches_metric_error(self) -> None:
        try:
            raise MetricError("test")
        except DataGeneratorError as e:
            assert isinstance(e, MetricError)

    def test_catch_base_catches_multi_item_error(self) -> None:
        try:
            raise MultiItemError("test")
        except DataGeneratorError as e:
            assert isinstance(e, MultiItemError)

    def test_catch_base_catches_validation_error(self) -> None:
        try:
            raise ValidationError("test")
        except DataGeneratorError as e:
            assert isinstance(e, ValidationError)

    def test_catch_base_catches_aggregation_error(self) -> None:
        try:
            raise AggregationError("test")
        except DataGeneratorError as e:
            assert isinstance(e, AggregationError)

    def test_catch_base_catches_configuration_error(self) -> None:
        try:
            raise ConfigurationError("test")
        except DataGeneratorError as e:
            assert isinstance(e, ConfigurationError)

    def test_base_exception_not_caught_by_exception_general(self) -> None:
        """A plain Exception handler catches it (since it's a subclass)."""
        try:
            raise DimensionError("test")
        except Exception as e:
            assert isinstance(e, DimensionError)


class TestExceptionIsolation:
    """Each exception type catches only its own domain."""

    def test_base_is_not_subclass_of_subclasses(self) -> None:
        assert not issubclass(DataGeneratorError, DimensionError)
        assert not issubclass(DataGeneratorError, MetricError)

    def test_subclasses_not_related_to_each_other(self) -> None:
        assert not issubclass(DimensionError, MetricError)
        assert not issubclass(MetricError, MultiItemError)
        assert not issubclass(MultiItemError, ValidationError)

    def test_dimension_does_not_catch_metric(self) -> None:
        with pytest.raises(MetricError):
            raise MetricError("only metric")
        with pytest.raises(DataGeneratorError):
            raise MetricError("also base")


class TestExceptionInstantiation:
    """Various instantiation patterns."""

    def test_no_args(self) -> None:
        for cls in (DataGeneratorError, DimensionError, MetricError, MultiItemError,
                     ValidationError, AggregationError, ConfigurationError):
            exc = cls()
            assert exc.args == ()

    def test_multiple_args(self) -> None:
        exc = DimensionError("msg1", "msg2")
        assert exc.args == ("msg1", "msg2")
        assert str(exc) == "('msg1', 'msg2')"

    def test_format_string_with_args(self) -> None:
        exc = ValidationError("Column '{}' not found".format("sales"))
        assert "sales" in str(exc)
