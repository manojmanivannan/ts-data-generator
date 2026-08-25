"""Tests for domain-carrying carrier objects and the add_dimension carrier path.

The library's dimension generators are ``Generator``-ABC carrier objects that
are also iterators (so ``next()`` keeps working) and additionally expose
``.domain`` and ``.expandable``. This is the no-introspection / no-sampling
domain-recovery mechanism for the ``expand_dimensions`` feature (#51/#53).
"""

from __future__ import annotations

import pytest

from ts_data_generator import DataGen
from ts_data_generator.exceptions import ValidationError
from ts_data_generator.random import SeedableRNG
from ts_data_generator.utils.functions import (
    auto_generate_name,
    constant,
    ordered_choice,
    random_choice,
    random_float,
    random_int,
)


@pytest.fixture
def data_gen():
    """A minimal hourly DataGen for add_dimension carrier tests."""
    dg = DataGen()
    dg.start_datetime = "2022-01-01"
    dg.end_datetime = "2022-01-02"
    dg.granularity = "h"
    return dg


class TestRandomChoiceCarrier:
    def test_domain_is_sorted_distinct(self) -> None:
        carrier = random_choice(["B", "A", "C", "A"])
        assert carrier.domain == ["A", "B", "C"]

    def test_expandable_is_true(self) -> None:
        carrier = random_choice(["A", "B", "C"])
        assert carrier.expandable is True

    def test_next_still_yields_choices(self) -> None:
        carrier = random_choice(["A", "B", "C"])
        values = [next(carrier) for _ in range(10)]
        assert all(v in ("A", "B", "C") for v in values)

    def test_is_a_generator(self) -> None:
        from collections.abc import Generator

        assert isinstance(random_choice(["A", "B"]), Generator)

    def test_deterministic_with_seed(self) -> None:
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        gen1 = random_choice(["A", "B", "C"], rng=rng1)
        gen2 = random_choice(["A", "B", "C"], rng=rng2)
        assert [next(gen1) for _ in range(20)] == [next(gen2) for _ in range(20)]


class TestOrderedChoiceCarrier:
    def test_domain_is_sorted_distinct(self) -> None:
        carrier = ordered_choice(["C", "A", "B", "A"])
        assert carrier.domain == ["A", "B", "C"]

    def test_expandable_is_true(self) -> None:
        assert ordered_choice(["A", "B", "C"]).expandable is True

    def test_next_cycles_in_order(self) -> None:
        carrier = ordered_choice(["A", "B", "C"])
        assert [next(carrier) for _ in range(5)] == ["A", "B", "C", "A", "B"]


class TestConstantCarrier:
    def test_scalar_domain(self) -> None:
        carrier = constant(10)
        assert carrier.domain == [10]
        assert carrier.expandable is True

    def test_scalar_next_yields_constant(self) -> None:
        carrier = constant("x")
        assert [next(carrier) for _ in range(3)] == ["x", "x", "x"]

    def test_list_domain(self) -> None:
        carrier = constant([3, 1, 2, 1])
        assert carrier.domain == [1, 2, 3]
        assert carrier.expandable is True

    def test_list_next_cycles(self) -> None:
        carrier = constant([1, 2, 3])
        assert [next(carrier) for _ in range(5)] == [1, 2, 3, 1, 2]

    def test_tuple_domain(self) -> None:
        carrier = constant(("a", "b"))
        assert carrier.domain == ["a", "b"]
        assert carrier.expandable is True


class TestRangeCarriers:
    def test_random_int_expandable_false(self) -> None:
        carrier = random_int(1, 100)
        assert carrier.expandable is False
        assert carrier.domain is None
        assert carrier.non_expandable_reason is not None

    def test_random_int_next_yields_in_range(self) -> None:
        carrier = random_int(1, 10)
        values = [next(carrier) for _ in range(20)]
        assert all(1 <= v <= 10 for v in values)

    def test_random_int_deterministic_with_seed(self) -> None:
        gen1 = random_int(1, 100, rng=SeedableRNG(99))
        gen2 = random_int(1, 100, rng=SeedableRNG(99))
        assert [next(gen1) for _ in range(20)] == [next(gen2) for _ in range(20)]

    def test_random_float_expandable_false(self) -> None:
        carrier = random_float(0.0, 1.0)
        assert carrier.expandable is False
        assert carrier.domain is None
        assert carrier.non_expandable_reason is not None

    def test_random_float_next_yields_in_range(self) -> None:
        carrier = random_float(1.0, 2.0)
        values = [next(carrier) for _ in range(10)]
        assert all(1.0 <= v <= 2.0 for v in values)


class TestAutoGenerateNameCarrier:
    def test_expandable_false(self) -> None:
        carrier = auto_generate_name("metric")
        assert carrier.expandable is False
        assert carrier.domain is None
        assert carrier.non_expandable_reason is not None

    def test_next_yields_a_name(self) -> None:
        carrier = auto_generate_name("metric")
        name = next(carrier)
        assert name.startswith("m_")

    def test_yields_same_name_each_step(self) -> None:
        carrier = auto_generate_name("dimension", rng=SeedableRNG(5))
        first = next(carrier)
        assert [next(carrier) for _ in range(4)] == [first] * 4

    def test_deterministic_with_seed(self) -> None:
        gen1 = auto_generate_name("metric", rng=SeedableRNG(123))
        gen2 = auto_generate_name("metric", rng=SeedableRNG(123))
        assert next(gen1) == next(gen2)


class TestAddDimensionListBranch:
    """The add_dimension list branch carries its domain — no opaque itertools.cycle."""

    def test_list_branch_is_a_carrier(self, data_gen) -> None:
        from collections.abc import Generator

        from ts_data_generator.carriers import DimensionCarrier

        data_gen.add_dimension("x", [1, 2, 3])
        fn = data_gen.dimensions["x"].function
        assert isinstance(fn, DimensionCarrier)
        assert isinstance(fn, Generator)

    def test_list_branch_domain_is_the_list(self, data_gen) -> None:
        data_gen.add_dimension("x", [1, 2, 3])
        assert data_gen.dimensions["x"].function.domain == [1, 2, 3]
        assert data_gen.dimensions["x"].function.expandable is True

    def test_list_branch_not_itertools_cycle(self, data_gen) -> None:
        import itertools

        data_gen.add_dimension("x", [1, 2, 3])
        fn = data_gen.dimensions["x"].function
        # The carrier wraps its own infinite source, not a bare itertools.cycle.
        assert not isinstance(fn, itertools.cycle)
        assert type(fn) is not itertools.cycle

    def test_list_branch_still_generates(self, data_gen) -> None:
        data_gen.add_dimension("interface", "X Y Z".split())
        df = data_gen.data
        values = list(df["interface"])
        # Cycles X,Y,Z across all rows; one row per timestamp.
        assert len(values) == len(df)
        assert values[:6] == ["X", "Y", "Z", "X", "Y", "Z"]
        assert set(values) == {"X", "Y", "Z"}


class TestAddDimensionDomainEscapeHatch:
    def _opaque(self):
        def gen():
            while True:
                yield "only"

        return gen()

    def test_opaque_gen_with_domain_becomes_expandable_carrier(self, data_gen) -> None:
        from ts_data_generator.carriers import DimensionCarrier

        data_gen.add_dimension("x", self._opaque(), domain=["a", "b", "c"])
        fn = data_gen.dimensions["x"].function
        assert isinstance(fn, DimensionCarrier)
        assert fn.expandable is True
        assert fn.domain == ["a", "b", "c"]

    def test_opaque_gen_with_domain_still_yields(self, data_gen) -> None:
        data_gen.add_dimension("x", self._opaque(), domain=["a", "b"])
        _ = data_gen.data
        assert set(data_gen.data["x"]) == {"only"}

    def test_domain_on_range_carrier_raises_eagerly(self, data_gen) -> None:
        with pytest.raises(ValidationError):
            data_gen.add_dimension("x", random_int(1, 100), domain=[1, 2, 3])

    def test_domain_on_float_range_carrier_raises_eagerly(self, data_gen) -> None:
        with pytest.raises(ValidationError):
            data_gen.add_dimension("x", random_float(0.0, 1.0), domain=[0.0, 1.0])

    def test_domain_on_auto_generate_name_raises_eagerly(self, data_gen) -> None:
        with pytest.raises(ValidationError):
            data_gen.add_dimension("x", auto_generate_name("cat"), domain=["a", "b"])

    def test_domain_on_expandable_carrier_raises(self, data_gen) -> None:
        with pytest.raises(ValidationError):
            data_gen.add_dimension("x", random_choice(["A", "B"]), domain=["A", "B"])
