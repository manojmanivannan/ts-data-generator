"""Tests for dimension generator functions."""

from __future__ import annotations

from ts_data_generator.random import DefaultRNG, SeedableRNG
from ts_data_generator.utils.functions import (
    auto_generate_name,
    random_choice,
    random_float,
    random_int,
)


class TestRandomChoiceWithRNG:
    def test_with_rng_is_deterministic(self) -> None:
        rng1 = SeedableRNG(42)
        rng2 = SeedableRNG(42)
        gen1 = random_choice(["A", "B", "C"], rng=rng1)
        gen2 = random_choice(["A", "B", "C"], rng=rng2)
        values1 = [next(gen1) for _ in range(20)]
        values2 = [next(gen2) for _ in range(20)]
        assert values1 == values2

    def test_different_seeds_produce_different_values(self) -> None:
        rng1 = SeedableRNG(1)
        rng2 = SeedableRNG(2)
        gen1 = random_choice(["A", "B", "C"], rng=rng1)
        gen2 = random_choice(["A", "B", "C"], rng=rng2)
        values1 = [next(gen1) for _ in range(20)]
        values2 = [next(gen2) for _ in range(20)]
        assert values1 != values2

    def test_without_rng_still_works(self) -> None:
        gen = random_choice(["X", "Y"])
        values = [next(gen) for _ in range(10)]
        assert all(v in ("X", "Y") for v in values)

    def test_with_default_rng_produces_valid_output(self) -> None:
        gen = random_choice(["A", "B", "C"], rng=DefaultRNG())
        values = [next(gen) for _ in range(10)]
        assert all(v in ("A", "B", "C") for v in values)


class TestRandomIntWithRNG:
    def test_with_rng_is_deterministic(self) -> None:
        rng1 = SeedableRNG(99)
        rng2 = SeedableRNG(99)
        gen1 = random_int(1, 100, rng=rng1)
        gen2 = random_int(1, 100, rng=rng2)
        values1 = [next(gen1) for _ in range(20)]
        values2 = [next(gen2) for _ in range(20)]
        assert values1 == values2

    def test_without_rng_still_works(self) -> None:
        gen = random_int(1, 10)
        values = [next(gen) for _ in range(20)]
        assert all(1 <= v <= 10 for v in values)

    def test_with_default_rng_produces_valid_output(self) -> None:
        gen = random_int(5, 15, rng=DefaultRNG())
        values = [next(gen) for _ in range(10)]
        assert all(5 <= v <= 15 for v in values)


class TestRandomFloatWithRNG:
    def test_with_rng_is_deterministic(self) -> None:
        rng1 = SeedableRNG(7)
        rng2 = SeedableRNG(7)
        gen1 = random_float(0.0, 1.0, rng=rng1)
        gen2 = random_float(0.0, 1.0, rng=rng2)
        values1 = [next(gen1) for _ in range(20)]
        values2 = [next(gen2) for _ in range(20)]
        assert values1 == values2

    def test_without_rng_still_works(self) -> None:
        gen = random_float(0.0, 5.0)
        values = [next(gen) for _ in range(10)]
        assert all(0.0 <= v <= 5.0 for v in values)

    def test_with_default_rng_produces_valid_output(self) -> None:
        gen = random_float(1.0, 2.0, rng=DefaultRNG())
        values = [next(gen) for _ in range(10)]
        assert all(1.0 <= v <= 2.0 for v in values)


class TestAutoGenerateNameWithRNG:
    def test_with_rng_is_deterministic(self) -> None:
        rng1 = SeedableRNG(123)
        rng2 = SeedableRNG(123)
        names1 = [auto_generate_name("metric", rng=rng1) for _ in range(5)]
        names2 = [auto_generate_name("metric", rng=rng2) for _ in range(5)]
        assert names1 == names2

    def test_without_rng_still_works(self) -> None:
        name = auto_generate_name("metric")
        assert name.startswith("m_")

    def test_with_default_rng_produces_valid_name(self) -> None:
        name = auto_generate_name("dimension", rng=DefaultRNG())
        assert name.startswith("d_")
