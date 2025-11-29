# create several out of the box generator functions to be used in the DataGen class

import random
import numpy as np
import pandas as pd
from typing import Union, Iterable, Tuple, Generator, TypeVar
from itertools import cycle

T = TypeVar("T")


def constant(value: Union[int, str, float, list]):
    """
    Returns a constant value.

    Args:
        value: A single constant int, string or float value to return.

    """
    while True:
        # if value is iterable, return the first element
        if isinstance(value, (list, tuple)):
            yield value[0]
        else:
            yield value


constant._example = "name:constant:10"


def random_choice(iterable):
    """
    Returns a random element from the given iterable.

    Args:
        iterable (iterable): The iterable to choose from.

    """
    while True:
        yield random.choice(iterable)


random_choice._example = "name:random_choice:A,B,C"


def random_int(start: int, end: int):
    """
    Returns a random integer between start and end, inclusive.

    Args:
        start (int): The starting value of the range.
        end (int): The ending value of the range.

    """
    while True:
        yield random.randint(start, end)


random_int._example = "name:random_int:1,100"


def random_float(start: float, end: float):
    """
    Returns a random float between start and end, inclusive.

    Args:
        start (float): The starting value of the range.
        end (float): The ending value of the range.

    """
    while True:
        yield random.uniform(start, end)


random_float._example = "name:random_float:0.0,1.0"


def ordered_choice(iterable):
    """
    Returns a random element from the given iterable in order.

    Args:
        iterable (iterable): The iterable to choose from.

    """
    yield cycle(iterable)


ordered_choice._example = "name:ordered_choice:A,B,C"


def auto_generate_name(category):
    """
    Generates a unique name for a metric or dimension.

    Args:
        category (str): The category of the name, either 'metric' or 'dimension'.

    """
    return f"{category[0]}_{random.randint(1, 100)}"


auto_generate_name._example = "name:auto_generate_name:mycat"


def random_multi_choice(
    *iterables: Iterable[T],
) -> Generator[Tuple[T, ...], None, None]:
    """
    Generates an infinite sequence of random tuples,
    selecting one random element from each given iterable.

    :param iterables: One or more iterables from which to randomly select elements.
    :return: An infinite generator yielding tuples with one random element from each iterable.
    """
    while True:
        choices = [random.choice(list(iterable)) for iterable in iterables]
        if len(choices) == 1:
            yield choices[0]
        else:
            yield tuple(choices)


random_multi_choice._example = "name:random_multi_choice:A,B:C,D:E,F"
