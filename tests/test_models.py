"""Tests for Dimensions and MultiItems model classes."""

from __future__ import annotations

import pandas as pd
import pytest

from ts_data_generator.schema.models import Dimensions, MultiItems
from ts_data_generator.utils.functions import random_choice, random_int

# ── helpers ─────────────────────────────────────────────────────────────

def _timestamps(n: int = 10) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-01", periods=n, freq="h")


# ── Dimensions ──────────────────────────────────────────────────────────

class TestDimensionsInit:
    """Tests for Dimensions.__init__."""

    def test_accepts_generator(self) -> None:
        d = Dimensions(name="color", function=random_choice(["red", "blue"]))
        assert d.name == "color"

    def test_accepts_list_name(self) -> None:
        d = Dimensions(name=["lat", "lon"], function=random_choice(["a", "b"]))
        assert d.name == ["lat", "lon"]

    def test_initial_data_is_none(self) -> None:
        d = Dimensions(name="x", function=random_choice(["a", "b"]))
        assert d.data is None


class TestDimensionsGenerate:
    """Tests for Dimensions.generate()."""

    def test_returns_dataframe(self) -> None:
        d = Dimensions(name="protocol", function=random_choice(["TCP", "UDP"]))
        result = d.generate(_timestamps(5))
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["protocol"]

    def test_length_matches_timestamps(self) -> None:
        d = Dimensions(name="port", function=random_int(1, 10))
        ts = _timestamps(100)
        result = d.generate(ts)
        assert len(result) == 100

    def test_data_property_updated(self) -> None:
        d = Dimensions(name="val", function=random_int(1, 100))
        ts = _timestamps(10)
        d.generate(ts)
        assert d.data is not None
        assert len(d.data) == 10

    def test_multi_column_name_returns_multiple_columns(self) -> None:
        def multi_gen():
            while True:
                yield (1, 2, 3)

        d = Dimensions(name=["a", "b", "c"], function=multi_gen())
        result = d.generate(_timestamps(5))
        assert list(result.columns) == ["a", "b", "c"]
        assert len(result) == 5

    def test_multi_column_values(self) -> None:
        def multi_gen():
            while True:
                yield (10, 20)

        d = Dimensions(name=["x", "y"], function=multi_gen())
        result = d.generate(_timestamps(3))
        assert list(result["x"]) == [10, 10, 10]
        assert list(result["y"]) == [20, 20, 20]


class TestDimensionsFunctionSetter:
    """Tests for Dimensions.function setter."""

    def test_valid_types_accepted(self) -> None:
        d = Dimensions(name="x", function=random_choice(["a", "b"]))
        # Accepts int
        d.function = 5
        assert d.function == 5
        # Accepts str
        d.function = "hello"
        assert d.function == "hello"
        # Accepts float
        d.function = 3.14
        assert d.function == 3.14
        # Accepts list
        d.function = [1, 2, 3]
        assert d.function == [1, 2, 3]

    def test_invalid_type_raises(self) -> None:
        d = Dimensions(name="x", function=random_choice(["a", "b"]))
        with pytest.raises(ValueError, match="must be a generator"):
            d.function = {"key": "value"}  # dict is invalid


class TestDimensionsEquality:
    """Tests for Dimensions.__eq__ and __hash__."""

    def test_equal_by_name(self) -> None:
        d1 = Dimensions(name="store", function=random_choice(["A", "B"]))
        d2 = Dimensions(name="store", function=random_choice(["X", "Y"]))
        assert d1 == d2

    def test_not_equal(self) -> None:
        d1 = Dimensions(name="store", function=random_choice(["A", "B"]))
        d2 = Dimensions(name="region", function=random_choice(["A", "B"]))
        assert d1 != d2

    def test_not_equal_other_type(self) -> None:
        d = Dimensions(name="x", function=random_choice(["a", "b"]))
        assert d != "not a dimension"

    def test_hashable(self) -> None:
        d1 = Dimensions(name="store", function=random_choice(["A", "B"]))
        d2 = Dimensions(name="region", function=random_choice(["A", "B"]))
        s = {d1, d2}
        assert len(s) == 2

    def test_same_name_same_hash(self) -> None:
        d1 = Dimensions(name="store", function=random_choice(["A"]))
        d2 = Dimensions(name="store", function=random_choice(["B"]))
        assert hash(d1) == hash(d2)

    def test_list_name_hash(self) -> None:
        d1 = Dimensions(name=["a", "b"], function=random_choice(["X"]))
        d2 = Dimensions(name=["a", "b"], function=random_choice(["Y"]))
        assert hash(d1) == hash(d2)


class TestDimensionsToJson:
    """Tests for Dimensions.to_json()."""

    def test_returns_dict(self) -> None:
        d = Dimensions(name="port", function=random_int(1, 100))
        js = d.to_json()
        assert isinstance(js, dict)
        assert js["name"] == "port"
        assert "function" in js

    def test_includes_function_repr(self) -> None:
        d = Dimensions(name="protocol", function=random_choice(["TCP", "UDP"]))
        js = d.to_json()
        assert "random_choice" in js["function"]


# ── MultiItems ──────────────────────────────────────────────────────────

class TestMultiItemsInit:
    """Tests for MultiItems.__init__."""

    def test_accepts_generator(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        mi = MultiItems(names=["a", "b"], function=gen())
        assert mi.names == ["a", "b"]

    def test_initial_data_is_none(self) -> None:
        def gen():
            while True:
                yield (1,)

        mi = MultiItems(names=["x"], function=gen())
        assert mi.data is None

    def test_with_aggregation_types(self) -> None:
        from ts_data_generator.schema.models import AggregationType

        def gen():
            while True:
                yield (1, 2)

        mi = MultiItems(
            names=["a", "b"],
            function=gen(),
            aggregation_type=[AggregationType.SUM, AggregationType.AVG],
        )
        assert mi.aggregation_type == [AggregationType.SUM, AggregationType.AVG]

    def test_aggregation_types_as_strings(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        mi = MultiItems(names=["a", "b"], function=gen(), aggregation_type=["sum", "avg"])
        assert mi.aggregation_type == ["sum", "avg"]

    def test_aggregation_type_none_by_default(self) -> None:
        def gen():
            while True:
                yield (1,)

        mi = MultiItems(names=["x"], function=gen())
        assert mi.aggregation_type is None


class TestMultiItemsGenerate:
    """Tests for MultiItems.generate()."""

    def test_returns_dataframe(self) -> None:
        def gen():
            while True:
                yield (10, 20)

        mi = MultiItems(names=["a", "b"], function=gen())
        result = mi.generate(_timestamps(5))
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["a", "b"]

    def test_length_matches_timestamps(self) -> None:
        def gen():
            idx = 0
            while True:
                yield (idx,)
                idx += 1

        mi = MultiItems(names=["counter"], function=gen())
        ts = _timestamps(100)
        result = mi.generate(ts)
        assert len(result) == 100

    def test_values_match_generator(self) -> None:
        def gen():
            while True:
                yield (1, 2, 3)

        mi = MultiItems(names=["a", "b", "c"], function=gen())
        result = mi.generate(_timestamps(3))
        assert list(result["a"]) == [1, 1, 1]
        assert list(result["b"]) == [2, 2, 2]
        assert list(result["c"]) == [3, 3, 3]

    def test_data_property_updated(self) -> None:
        def gen():
            while True:
                yield (42,)

        mi = MultiItems(names=["answer"], function=gen())
        mi.generate(_timestamps(10))
        assert mi.data is not None
        assert len(mi.data) == 10


class TestMultiItemsFunctionSetter:
    """Tests for MultiItems.function setter."""

    def test_valid_types_accepted(self) -> None:
        def gen():
            while True:
                yield (1,)

        mi = MultiItems(names=["x"], function=gen())
        mi.function = 42
        assert mi.function == 42
        mi.function = "hello"
        assert mi.function == "hello"

    def test_invalid_type_raises(self) -> None:
        def gen():
            while True:
                yield (1,)

        mi = MultiItems(names=["x"], function=gen())
        with pytest.raises(ValueError, match="must be a generator"):
            mi.function = {"key": "val"}


class TestMultiItemsEquality:
    """Tests for MultiItems.__eq__ and __hash__."""

    def test_equal_by_names(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        m1 = MultiItems(names=["a", "b"], function=gen())
        m2 = MultiItems(names=["a", "b"], function=gen())
        assert m1 == m2

    def test_not_equal(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        m1 = MultiItems(names=["a", "b"], function=gen())
        m2 = MultiItems(names=["c", "d"], function=gen())
        assert m1 != m2

    def test_not_equal_other_type(self) -> None:
        def gen():
            while True:
                yield (1,)

        m = MultiItems(names=["x"], function=gen())
        assert m != "not a multi item"

    def test_hashable(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        m1 = MultiItems(names=["a", "b"], function=gen())
        m2 = MultiItems(names=["c", "d"], function=gen())
        s = {m1, m2}
        assert len(s) == 2

    def test_same_names_same_hash(self) -> None:
        def gen_a():
            while True:
                yield (1, 2)

        def gen_b():
            while True:
                yield (3, 4)

        m1 = MultiItems(names=["a", "b"], function=gen_a())
        m2 = MultiItems(names=["a", "b"], function=gen_b())
        assert hash(m1) == hash(m2)


class TestMultiItemsToJson:
    """Tests for MultiItems.to_json()."""

    def test_returns_dict(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        mi = MultiItems(names=["a", "b"], function=gen())
        js = mi.to_json()
        assert isinstance(js, dict)
        assert js["names"] == ["a", "b"]
        assert "function" in js
