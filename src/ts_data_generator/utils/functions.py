"""Dimension generator functions that produce values for time series dimensions.

Each function returns an infinite generator yielding values at each time step.
Most accept parameters from the CLI shorthand syntax (e.g. ``name:random_choice:A,B,C``).
"""

import random
from collections.abc import Generator, Iterable
from itertools import cycle
from typing import TypeVar

T = TypeVar("T")


def constant(value: int | str | float | list | tuple) -> Generator[int | str | float, None, None]:
    """Yield the same constant value indefinitely.

    If given a list or tuple, cycles through the values — each timestamp
    gets the next element.

    Args:
        value: A constant value, or a list/tuple of values to cycle through.

    Yields:
        The constant value (or next cycled value) at each step.

    Example:
        CLI shorthand: ``name:constant:10`` or ``name:constant:X,Y,Z``
    """
    if isinstance(value, (list, tuple)):
        while True:
            yield from cycle(value)
    else:
        while True:
            yield value


constant._example = "name:constant:10"


def random_choice(iterable: Iterable[T]) -> Generator[T, None, None]:
    """Yield a random element from the iterable at each step.

    Args:
        iterable: The collection to choose from.

    Yields:
        A randomly selected element at each step.

    Example:
        CLI shorthand: ``name:random_choice:A,B,C``
    """
    while True:
        yield random.choice(list(iterable))


random_choice._example = "name:random_choice:A,B,C"


def random_int(start: int, end: int) -> Generator[int, None, None]:
    """Yield a random integer in [start, end] inclusive at each step.

    Args:
        start: Lower bound (inclusive).
        end: Upper bound (inclusive).

    Yields:
        A random integer at each step.

    Example:
        CLI shorthand: ``name:random_int:1,100``
    """
    while True:
        yield random.randint(start, end)


random_int._example = "name:random_int:1,100"


def random_float(start: float, end: float) -> Generator[float, None, None]:
    """Yield a random float in [start, end) at each step.

    Args:
        start: Lower bound (inclusive).
        end: Upper bound (exclusive).

    Yields:
        A random float at each step.

    Example:
        CLI shorthand: ``name:random_float:0.0,1.0``
    """
    while True:
        yield random.uniform(start, end)


random_float._example = "name:random_float:0.0,1.0"


def ordered_choice(iterable: Iterable[T]) -> Generator[T, None, None]:
    """Yield elements from the iterable in repeating order.

    Args:
        iterable: The collection to cycle through.

    Yields:
        The next element in sequence at each step.

    Example:
        CLI shorthand: ``name:ordered_choice:A,B,C``
    """
    while True:
        yield from cycle(iterable)


ordered_choice._example = "name:ordered_choice:A,B,C"


def auto_generate_name(category: str) -> str:
    """Generate a unique identifier for a metric or dimension.

    Args:
        category: Either 'metric' or 'dimension'.

    Returns:
        A string like ``'m_42'`` for metrics or ``'d_17'`` for dimensions.
    """
    prefix = category[0] if category else "x"
    return f"{prefix}_{random.randint(1, 100)}"


auto_generate_name._example = "name:auto_generate_name:mycat"
