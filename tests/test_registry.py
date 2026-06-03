"""Tests for the Registry class."""

from __future__ import annotations

import click
import pytest

from ts_data_generator.utils.registry import Registry

# ── helpers for test modules ─────────────────────────────────────────────
# NOTE: names must NOT start with '_' because Registry.list_available()
# always skips private names.

class Base:
    """Abstract-ish base for testing base_class filtering."""


class ConcreteA(Base):
    """A concrete subclass of Base."""


class ConcreteB(Base):
    """Another concrete subclass of Base."""


class NotSubclass:
    """A class that does *not* inherit from Base."""


def top_level_fn() -> str:
    """A top-level module function."""
    return "hello"


# Use this module itself as the test module.
_TEST_MODULE = __name__


class TestRegistryInit:
    """Tests for Registry.__init__."""

    def test_accepts_module_string(self) -> None:
        """A dotted module string is imported successfully."""
        r = Registry("ts_data_generator.utils.functions")
        assert "random_choice" in r.list_available()

    def test_accepts_module_object(self) -> None:
        """An already-imported module object is accepted."""
        import ts_data_generator.utils.functions as fn_mod

        r = Registry(fn_mod)
        assert "random_choice" in r.list_available()


class TestRegistryGet:
    """Tests for Registry.get()."""

    def test_finds_existing_name(self) -> None:
        r = Registry(_TEST_MODULE)
        obj = r.get("top_level_fn")
        assert obj is top_level_fn

    def test_raises_bad_parameter_for_missing(self) -> None:
        r = Registry(_TEST_MODULE)
        with pytest.raises(click.BadParameter, match="not a valid option"):
            r.get("nonexistent_thing")

    def test_base_class_filter(self) -> None:
        r = Registry(_TEST_MODULE, base_class=Base)

        obj_a = r.get("ConcreteA")
        assert obj_a is ConcreteA

        obj_b = r.get("ConcreteB")
        assert obj_b is ConcreteB

    def test_base_class_rejects_non_subclass(self) -> None:
        r = Registry(_TEST_MODULE, base_class=Base)
        with pytest.raises(click.BadParameter, match="not a valid option"):
            r.get("NotSubclass")

    def test_base_class_rejects_function(self) -> None:
        """A module-level function is not a class, so issubclass check rejects it."""
        r = Registry(_TEST_MODULE, base_class=Base)
        with pytest.raises(click.BadParameter, match="not a valid option"):
            r.get("top_level_fn")

    def test_base_class_rejects_string(self) -> None:
        """A string value (not a class) is rejected by base_class filter."""
        r = Registry(_TEST_MODULE, base_class=Base)
        # top_level_fn exists but is not a class
        with pytest.raises(click.BadParameter):
            r.get("top_level_fn")

    def test_name_filter_affects_error_message(self) -> None:
        """name_filter controls what appears in the 'Available:' error message."""
        r = Registry(_TEST_MODULE, name_filter=lambda n: n.startswith("Concrete"))
        with pytest.raises(click.BadParameter) as exc_info:
            r.get("NoSuchName")
        msg = str(exc_info.value)
        # ConcreteA and ConcreteB should be listed
        assert "ConcreteA" in msg
        assert "ConcreteB" in msg
        # NotSubclass and top_level_fn should NOT appear (filtered out)
        assert "NotSubclass" not in msg
        assert "top_level_fn" not in msg

    def test_name_filter_does_not_prevent_get(self) -> None:
        """name_filter limits list_available() but get() still uses getattr."""
        r = Registry(_TEST_MODULE, name_filter=lambda n: n == "nothing")
        # get() uses raw getattr, not the filter
        obj = r.get("top_level_fn")
        assert obj is top_level_fn


class TestRegistryListAvailable:
    """Tests for Registry.list_available()."""

    def test_lists_all_public_names_by_default(self) -> None:
        r = Registry("ts_data_generator.utils.functions")
        available = r.list_available()
        for name in ("constant", "random_choice", "random_int", "random_float",
                      "ordered_choice", "auto_generate_name"):
            assert name in available

    def test_private_names_excluded(self) -> None:
        """dir() entries starting with '_' are excluded by default."""
        r = Registry(_TEST_MODULE)
        available = r.list_available()
        private = [n for n in available if n.startswith("_")]
        assert not private

    def test_base_class_filters_to_subclasses(self) -> None:
        r = Registry(_TEST_MODULE, base_class=Base)
        available = r.list_available()
        assert "ConcreteA" in available
        assert "ConcreteB" in available
        assert "NotSubclass" not in available
        assert "top_level_fn" not in available

    def test_name_filter_predicate(self) -> None:
        """name_filter removes names that don't match."""
        r = Registry(_TEST_MODULE, name_filter=lambda n: n.endswith("A"))
        available = r.list_available()
        assert "ConcreteA" in available
        assert "ConcreteB" not in available

    def test_returns_sorted(self) -> None:
        """list_available() returns alphabetically sorted names."""
        r = Registry("ts_data_generator.utils.functions")
        available = r.list_available()
        assert available == sorted(available)


class TestRegistryRealModules:
    """Tests using real project modules."""

    def test_trend_registry_finds_sinusoidal(self) -> None:
        """The trends module should expose SinusoidalTrend."""
        r = Registry(
            "ts_data_generator.utils.trends",
            base_class=object,  # just ensures it's a class
        )
        assert "SinusoidalTrend" in r.list_available()

    def test_anomaly_registry_finds_point_anomaly(self) -> None:
        """The anomalies module should expose PointAnomaly."""
        from ts_data_generator.anomalies import PointAnomaly

        r = Registry("ts_data_generator.anomalies")
        obj = r.get("PointAnomaly")
        assert obj is PointAnomaly

    def test_function_registry_finds_random_choice(self) -> None:
        """The functions module should expose random_choice."""
        from ts_data_generator.utils.functions import random_choice

        r = Registry("ts_data_generator.utils.functions")
        obj = r.get("random_choice")
        assert obj is random_choice
