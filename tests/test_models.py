"""Tests for Dimensions, MultiItems, and Metrics model classes."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ts_data_generator.anomalies.point import PointAnomaly
from ts_data_generator.functions import random_choice, random_int
from ts_data_generator.random import DefaultRNG, SeedableRNG
from ts_data_generator.schema.models import Dimension, Metric, MultiItem
from ts_data_generator.trends import LinearTrend

# ── helpers ─────────────────────────────────────────────────────────────


def _timestamps(n: int = 10) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-01", periods=n, freq="h")


# ── Dimensions ──────────────────────────────────────────────────────────


class TestDimensionsInit:
    """Tests for Dimensions.__init__."""

    def test_accepts_generator(self) -> None:
        d = Dimension(name="color", function=random_choice(["red", "blue"]))
        assert d.name == "color"

    def test_accepts_list_name(self) -> None:
        d = Dimension(name=["lat", "lon"], function=random_choice(["a", "b"]))
        assert d.name == ["lat", "lon"]

    def test_initial_data_is_none(self) -> None:
        d = Dimension(name="x", function=random_choice(["a", "b"]))
        assert d.data is None


class TestDimensionsGenerate:
    """Tests for Dimensions.generate()."""

    def test_returns_dataframe(self) -> None:
        d = Dimension(name="protocol", function=random_choice(["TCP", "UDP"]))
        result = d.generate(_timestamps(5))
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["protocol"]

    def test_length_matches_timestamps(self) -> None:
        d = Dimension(name="port", function=random_int(1, 10))
        ts = _timestamps(100)
        result = d.generate(ts)
        assert len(result) == 100

    def test_data_property_updated(self) -> None:
        d = Dimension(name="val", function=random_int(1, 100))
        ts = _timestamps(10)
        d.generate(ts)
        assert d.data is not None
        assert len(d.data) == 10

    def test_multi_column_name_returns_multiple_columns(self) -> None:
        def multi_gen():
            while True:
                yield (1, 2, 3)

        d = Dimension(name=["a", "b", "c"], function=multi_gen())
        result = d.generate(_timestamps(5))
        assert list(result.columns) == ["a", "b", "c"]
        assert len(result) == 5

    def test_multi_column_values(self) -> None:
        def multi_gen():
            while True:
                yield (10, 20)

        d = Dimension(name=["x", "y"], function=multi_gen())
        result = d.generate(_timestamps(3))
        assert list(result["x"]) == [10, 10, 10]
        assert list(result["y"]) == [20, 20, 20]

    def test_generate_accepts_rng_protocol(self) -> None:
        d = Dimension(name="port", function=random_int(1, 100))
        result = d.generate(_timestamps(5), rng=DefaultRNG())
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5


class TestDimensionsFunctionSetter:
    """Tests for Dimensions.function setter."""

    def test_valid_types_accepted(self) -> None:
        d = Dimension(name="x", function=random_choice(["a", "b"]))
        # Accepts int
        d.function = 5
        assert d.function == 5
        # Accepts str
        d.function = "hello"
        assert d.function == "hello"
        # Accepts float
        d.function = 3.14
        assert d.function == 3.14

    def test_invalid_type_raises(self) -> None:
        d = Dimension(name="x", function=random_choice(["a", "b"]))
        with pytest.raises(ValueError, match="must be a generator"):
            d.function = {"key": "value"}  # dict is invalid
        # A plain list is rejected: `next()` on a list raises TypeError, so the
        # list branch is dead code (removed per decision #06 — cleanup, not a
        # type widening).
        with pytest.raises(ValueError, match="must be a generator"):
            d.function = [1, 2, 3]


class TestDimensionsExpandSetter:
    """Tests for Dimensions.expand setter."""

    def test_assignment_updates_override(self) -> None:
        d = Dimension(name="region", function=random_choice(["US", "EU"]))
        d.expand = False
        assert d.expand is False
        d.expand = True
        assert d.expand is True


class TestMultiItemsExpandSetter:
    """Tests for MultiItems.expand setter."""

    def test_assignment_updates_override(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        mi = MultiItem(names=["a", "b"], function=gen())
        mi.expand = False
        assert mi.expand is False
        mi.expand = True
        assert mi.expand is True


class TestDimensionsEquality:
    """Tests for Dimensions.__eq__ and __hash__."""

    def test_equal_by_name(self) -> None:
        d1 = Dimension(name="store", function=random_choice(["A", "B"]))
        d2 = Dimension(name="store", function=random_choice(["X", "Y"]))
        assert d1 == d2

    def test_not_equal(self) -> None:
        d1 = Dimension(name="store", function=random_choice(["A", "B"]))
        d2 = Dimension(name="region", function=random_choice(["A", "B"]))
        assert d1 != d2

    def test_not_equal_other_type(self) -> None:
        d = Dimension(name="x", function=random_choice(["a", "b"]))
        assert d != "not a dimension"

    def test_hashable(self) -> None:
        d1 = Dimension(name="store", function=random_choice(["A", "B"]))
        d2 = Dimension(name="region", function=random_choice(["A", "B"]))
        s = {d1, d2}
        assert len(s) == 2

    def test_same_name_same_hash(self) -> None:
        d1 = Dimension(name="store", function=random_choice(["A"]))
        d2 = Dimension(name="store", function=random_choice(["B"]))
        assert hash(d1) == hash(d2)

    def test_list_name_hash(self) -> None:
        d1 = Dimension(name=["a", "b"], function=random_choice(["X"]))
        d2 = Dimension(name=["a", "b"], function=random_choice(["Y"]))
        assert hash(d1) == hash(d2)


class TestDimensionsToJson:
    """Tests for Dimensions.to_json()."""

    def test_returns_dict(self) -> None:
        d = Dimension(name="port", function=random_int(1, 100))
        js = d.to_json()
        assert isinstance(js, dict)
        assert js["name"] == "port"
        assert "function" in js

    def test_includes_function_repr(self) -> None:
        d = Dimension(name="protocol", function=random_choice(["TCP", "UDP"]))
        js = d.to_json()
        assert "random_choice" in js["function"]

    def test_repr_includes_expand_and_weights(self) -> None:
        d = Dimension(
            name="region",
            function=random_choice(["US", "EU"]),
            expand=False,
            weights={"US": 5.0, "EU": 2.0},
        )
        text = repr(d)
        assert "'expand'" in text
        assert "False" in text
        assert "'weights'" in text
        assert "US" in text
        assert "EU" in text


# ── MultiItems ──────────────────────────────────────────────────────────


class TestMultiItemsInit:
    """Tests for MultiItems.__init__."""

    def test_accepts_generator(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        mi = MultiItem(names=["a", "b"], function=gen())
        assert mi.names == ["a", "b"]

    def test_initial_data_is_none(self) -> None:
        def gen():
            while True:
                yield (1,)

        mi = MultiItem(names=["x"], function=gen())
        assert mi.data is None

    def test_with_aggregation_types(self) -> None:
        from ts_data_generator.schema.models import AggregationType

        def gen():
            while True:
                yield (1, 2)

        mi = MultiItem(
            names=["a", "b"],
            function=gen(),
            aggregation_type=[AggregationType.SUM, AggregationType.AVG],
        )
        assert mi.aggregation_type == [AggregationType.SUM, AggregationType.AVG]

    def test_aggregation_types_as_strings(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        mi = MultiItem(names=["a", "b"], function=gen(), aggregation_type=["sum", "avg"])
        assert mi.aggregation_type == ["sum", "avg"]

    def test_aggregation_type_none_by_default(self) -> None:
        def gen():
            while True:
                yield (1,)

        mi = MultiItem(names=["x"], function=gen())
        assert mi.aggregation_type is None

    def test_expand_none_by_default(self) -> None:
        def gen():
            while True:
                yield (1,)

        mi = MultiItem(names=["x"], function=gen())
        assert mi.expand is None

    def test_with_expand_override(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        mi_true = MultiItem(names=["a", "b"], function=gen(), expand=True)
        mi_false = MultiItem(names=["a", "b"], function=gen(), expand=False)
        assert mi_true.expand is True
        assert mi_false.expand is False


class TestMultiItemsGenerate:
    """Tests for MultiItems.generate()."""

    def test_returns_dataframe(self) -> None:
        def gen():
            while True:
                yield (10, 20)

        mi = MultiItem(names=["a", "b"], function=gen())
        result = mi.generate(_timestamps(5))
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["a", "b"]

    def test_length_matches_timestamps(self) -> None:
        def gen():
            idx = 0
            while True:
                yield (idx,)
                idx += 1

        mi = MultiItem(names=["counter"], function=gen())
        ts = _timestamps(100)
        result = mi.generate(ts)
        assert len(result) == 100

    def test_values_match_generator(self) -> None:
        def gen():
            while True:
                yield (1, 2, 3)

        mi = MultiItem(names=["a", "b", "c"], function=gen())
        result = mi.generate(_timestamps(3))
        assert list(result["a"]) == [1, 1, 1]
        assert list(result["b"]) == [2, 2, 2]
        assert list(result["c"]) == [3, 3, 3]

    def test_data_property_updated(self) -> None:
        def gen():
            while True:
                yield (42,)

        mi = MultiItem(names=["answer"], function=gen())
        mi.generate(_timestamps(10))
        assert mi.data is not None
        assert len(mi.data) == 10

    def test_generate_accepts_rng_protocol(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        mi = MultiItem(names=["a", "b"], function=gen())
        result = mi.generate(_timestamps(5), rng=DefaultRNG())
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5


class TestMultiItemsFunctionSetter:
    """Tests for MultiItems.function setter."""

    def test_valid_types_accepted(self) -> None:
        def gen():
            while True:
                yield (1,)

        mi = MultiItem(names=["x"], function=gen())
        mi.function = 42
        assert mi.function == 42
        mi.function = "hello"
        assert mi.function == "hello"

    def test_invalid_type_raises(self) -> None:
        def gen():
            while True:
                yield (1,)

        mi = MultiItem(names=["x"], function=gen())
        with pytest.raises(ValueError, match="must be a generator"):
            mi.function = {"key": "val"}
        # A plain list is rejected (dead `list` branch removed, per decision #06).
        with pytest.raises(ValueError, match="must be a generator"):
            mi.function = [1, 2, 3]


class TestMultiItemsEquality:
    """Tests for MultiItems.__eq__ and __hash__."""

    def test_equal_by_names(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        m1 = MultiItem(names=["a", "b"], function=gen())
        m2 = MultiItem(names=["a", "b"], function=gen())
        assert m1 == m2

    def test_not_equal(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        m1 = MultiItem(names=["a", "b"], function=gen())
        m2 = MultiItem(names=["c", "d"], function=gen())
        assert m1 != m2

    def test_not_equal_other_type(self) -> None:
        def gen():
            while True:
                yield (1,)

        m = MultiItem(names=["x"], function=gen())
        assert m != "not a multi item"

    def test_hashable(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        m1 = MultiItem(names=["a", "b"], function=gen())
        m2 = MultiItem(names=["c", "d"], function=gen())
        s = {m1, m2}
        assert len(s) == 2

    def test_same_names_same_hash(self) -> None:
        def gen_a():
            while True:
                yield (1, 2)

        def gen_b():
            while True:
                yield (3, 4)

        m1 = MultiItem(names=["a", "b"], function=gen_a())
        m2 = MultiItem(names=["a", "b"], function=gen_b())
        assert hash(m1) == hash(m2)


class TestMultiItemsToJson:
    """Tests for MultiItems.to_json()."""

    def test_returns_dict(self) -> None:
        def gen():
            while True:
                yield (1, 2)

        mi = MultiItem(names=["a", "b"], function=gen())
        js = mi.to_json()
        assert isinstance(js, dict)
        assert js["names"] == ["a", "b"]
        assert "function" in js


# ── Metrics ──────────────────────────────────────────────────────────────


class TestMetricsGenerateReturnsMetricResult:
    """Phase 2A: Metrics.generate() returns MetricResult with .signal and .baseline."""

    def test_generate_returns_metric_result(self) -> None:
        from ts_data_generator.schema.models import MetricResult

        trend = LinearTrend(offset=10, noise_level=0)
        m = Metric(name="val", trends={trend})
        result = m.generate(_timestamps(5), rng=DefaultRNG())
        assert isinstance(result, MetricResult)

    def test_metric_result_has_signal_and_baseline(self) -> None:
        trend = LinearTrend(offset=10, noise_level=0)
        m = Metric(name="val", trends={trend})
        result = m.generate(_timestamps(5), rng=DefaultRNG())
        assert hasattr(result, "signal")
        assert hasattr(result, "baseline")
        assert isinstance(result.signal, pd.DataFrame)
        assert isinstance(result.baseline, pd.DataFrame)

    def test_without_anomalies_signal_equals_baseline(self) -> None:
        trend = LinearTrend(offset=5, noise_level=0)
        m = Metric(name="val", trends={trend})
        result = m.generate(_timestamps(10), rng=DefaultRNG())
        np.testing.assert_array_equal(result.signal.values, result.baseline.values)

    def test_with_anomalies_signal_differs_from_baseline(self) -> None:
        n = 500
        timestamps = _timestamps(n)
        trend = LinearTrend(offset=10, noise_level=0)
        anomaly = PointAnomaly(probability=0.5, magnitude=999, mode="additive")
        m = Metric(name="val", trends={trend}, anomalies=[anomaly])
        result = m.generate(timestamps, rng=SeedableRNG(42))
        assert not np.array_equal(result.signal.values, result.baseline.values)

    def test_baseline_is_clean_no_anomaly_effect(self) -> None:
        n = 500
        timestamps = _timestamps(n)
        trend = LinearTrend(offset=10, noise_level=0)
        anomaly = PointAnomaly(probability=0.5, magnitude=999, mode="replacement")
        m = Metric(name="val", trends={trend}, anomalies=[anomaly])
        result = m.generate(timestamps, rng=SeedableRNG(42))
        # baseline should only contain trend offset (10), no 999 replacements
        assert not np.any(result.baseline["val"].values == 999)
        assert np.any(result.signal["val"].values == 999)

    def test_metric_accepts_single_trend_list_tuple_set_and_stores_list(self) -> None:
        from ts_data_generator.exceptions import MetricError
        from ts_data_generator.trends import SinusoidalTrend

        t1 = LinearTrend(offset=10)
        t2 = SinusoidalTrend(amplitude=5)

        m_single = Metric(name="m1", trends=t1)
        assert isinstance(m_single.trends, list)
        assert m_single.trends == [t1]

        m_list = Metric(name="m2", trends=[t1, t2])
        assert isinstance(m_list.trends, list)
        assert m_list.trends == [t1, t2]

        m_tuple = Metric(name="m3", trends=(t1, t2))
        assert isinstance(m_tuple.trends, list)
        assert m_tuple.trends == [t1, t2]

        m_set = Metric(name="m4", trends={t1})
        assert isinstance(m_set.trends, list)
        assert m_set.trends == [t1]

        with pytest.raises(MetricError, match="Duplicate trends are present"):
            Metric(name="m_dup", trends=[t1, t1])


class TestGranularityStrEnum:
    """Verify Granularity is a StrEnum with singular time-unit noun members."""

    def test_granularity_members_and_strenum(self) -> None:
        from enum import StrEnum

        from ts_data_generator.schema.models import Granularity

        assert issubclass(Granularity, StrEnum)
        assert isinstance(Granularity.HOUR, str)
        assert Granularity.SECOND == "s"
        assert Granularity.MINUTE == "min"
        assert Granularity.FIVE_MINUTE == "5min"
        assert Granularity.HOUR == "h"
        assert Granularity.DAY == "D"
        assert Granularity.WEEK == "W"
        assert Granularity.MONTH == "ME"
        assert Granularity.YEAR == "Y"
