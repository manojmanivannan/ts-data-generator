"""Dimension generator functions that produce values for time series dimensions.

Each function returns a :class:`~ts_data_generator.carriers.DimensionCarrier` —
an infinite iterator yielding values at each time step that *also* carries its
``.domain`` and ``.expandable`` classification, captured at construction. This
is the no-introspection / no-sampling domain-recovery mechanism for the
``expand_dimensions`` feature. Most accept parameters from the CLI shorthand
syntax (e.g. ``name:random_choice:A,B,C``).
"""

from __future__ import annotations

import random as _random
from collections.abc import Iterable as _Iterable
from itertools import cycle as _cycle
from typing import TYPE_CHECKING
from typing import TypeVar as _TypeVar

from ts_data_generator.carriers import DomainCarrier as _DomainCarrier
from ts_data_generator.carriers import NonExpandableCarrier as _NonExpandableCarrier

if TYPE_CHECKING:
    from ts_data_generator.carriers import DimensionCarrier
    from ts_data_generator.random import RNGProtocol

_T = _TypeVar("_T")


def constant(
    value: int | str | float | list[int | str | float] | tuple[int | str | float, ...],
) -> DimensionCarrier[int | str | float]:
    """Yield the same constant value indefinitely.

    If given a list or tuple, cycles through the values — each timestamp
    gets the next element.

    Args:
        value: A constant value, or a list/tuple of values to cycle through.

    Returns:
        A carrier whose ``.domain`` is the value(s) and ``.expandable`` is
        ``True``; ``next()`` yields the constant (or next cycled) value.

    Example:
        >>> from ts_data_generator.functions import constant
        >>> carrier = constant(10)
        >>> carrier.domain
        [10]
        >>> carrier.expandable
        True
        >>> next(carrier), next(carrier)
        (10, 10)
        >>> cyc = constant(["X", "Y", "Z"])
        >>> cyc.domain
        ['X', 'Y', 'Z']
        >>> [next(cyc) for _ in range(4)]
        ['X', 'Y', 'Z', 'X']

    """
    if isinstance(value, (list, tuple)):
        domain = list(value)

        def _source() -> int | str | float:
            yield from _cycle(value)

    else:
        domain = [value]

        def _source() -> int | str | float:
            while True:
                yield value

    return _DomainCarrier(_source(), domain, "constant")


constant._example = "name:constant:10"


def random_choice(iterable: _Iterable[_T], rng: RNGProtocol | None = None) -> DimensionCarrier[_T]:
    """Yield a random element from the iterable at each step.

    Args:
        iterable: The collection to choose from.
        rng: Optional RNG for deterministic generation.

    Returns:
        A carrier whose ``.domain`` is the sorted-distinct elements and
        ``.expandable`` is ``True``; ``next()`` yields a random element.

    Example:
        CLI shorthand::

            name:random_choice:A,B,C

    """
    items = list(iterable)
    if rng is not None:

        def _source() -> _T:
            while True:
                yield rng.choice(items)

    else:

        def _source() -> _T:
            while True:
                yield _random.choice(items)

    return _DomainCarrier(_source(), items, "random_choice")


random_choice._example = "name:random_choice:A,B,C"


def random_int(start: int, end: int, rng: RNGProtocol | None = None) -> DimensionCarrier[int]:
    """Yield a random integer in [start, end] inclusive at each step.

    Args:
        start: Lower bound (inclusive).
        end: Upper bound (inclusive).
        rng: Optional RNG for deterministic generation.

    Returns:
        A carrier tagged ``expandable=False`` (a numeric range is not an
        enumerable dimension); ``next()`` yields a random integer.

    Example:
        CLI shorthand::

            name:random_int:1,100

    """
    if isinstance(start, list):
        start = start[0]
    if isinstance(end, list):
        end = end[0]

    if rng is not None:

        def _source() -> int:
            while True:
                yield int(rng.integers(start, end + 1))

    else:

        def _source() -> int:
            while True:
                yield _random.randint(start, end)

    return _NonExpandableCarrier(
        _source(),
        "random_int",
        "random_int() draws from a numeric range; use random_choice/ordered_choice "
        "for an enumerable dimension",
        (start, end),
    )


random_int._example = "name:random_int:1,100"


def random_float(
    start: float, end: float, rng: RNGProtocol | None = None
) -> DimensionCarrier[float]:
    """Yield a random float in [start, end) at each step.

    Args:
        start: Lower bound (inclusive).
        end: Upper bound (exclusive).
        rng: Optional RNG for deterministic generation.

    Returns:
        A carrier tagged ``expandable=False`` (a numeric range is not an
        enumerable dimension); ``next()`` yields a random float.

    Example:
        CLI shorthand::

            name:random_float:0.0,1.0

    """
    if isinstance(start, list):
        start = start[0]
    if isinstance(end, list):
        end = end[0]

    if rng is not None:

        def _source() -> float:
            while True:
                yield rng.uniform(start, end)

    else:

        def _source() -> float:
            while True:
                yield _random.uniform(start, end)

    return _NonExpandableCarrier(
        _source(),
        "random_float",
        "random_float() draws from a numeric range; use random_choice/ordered_choice "
        "for an enumerable dimension",
        (start, end),
    )


random_float._example = "name:random_float:0.0,1.0"


def ordered_choice(iterable: _Iterable[_T]) -> DimensionCarrier[_T]:
    """Yield elements from the iterable in repeating order.

    Args:
        iterable: The collection to cycle through.

    Returns:
        A carrier whose ``.domain`` is the sorted-distinct elements and
        ``.expandable`` is ``True``; ``next()`` yields the next element in
        sequence.

    Example:
        CLI shorthand::

            name:ordered_choice:A,B,C

    """
    items = list(iterable)

    def _source() -> _T:
        while True:
            yield from _cycle(items)

    return _DomainCarrier(_source(), items, "ordered_choice")


ordered_choice._example = "name:ordered_choice:A,B,C"


def auto_generate_name(category: str, rng: RNGProtocol | None = None) -> DimensionCarrier[str]:
    """Generate a unique identifier for a metric or dimension.

    Args:
        category: Either 'metric' or 'dimension'.
        rng: Optional RNG for deterministic generation.

    Returns:
        A carrier tagged ``expandable=False`` (an auto-generated name is not
        a finite-domain dimension generator) that yields the one generated
        name indefinitely; ``next()`` yields the name string.

    Example:
        CLI shorthand::

            name:auto_generate_name:mycat

    """
    prefix = category[0] if category else "x"
    if rng is not None:
        name = f"{prefix}_{rng.integers(1, 101)}"
    else:
        name = f"{prefix}_{_random.randint(1, 100)}"

    def _source() -> str:
        while True:
            yield name

    return _NonExpandableCarrier(
        _source(),
        "auto_generate_name",
        "auto_generate_name() is not a finite-domain dimension generator",
        (category,),
    )


auto_generate_name._example = "name:auto_generate_name:mycat"

__all__ = [
    "auto_generate_name",
    "constant",
    "ordered_choice",
    "random_choice",
    "random_float",
    "random_int",
]
