# create several out of the box generator functions to be used in the DataGen class

import random
import numpy as np
import pandas as pd

def constant(value):
    """
    Returns a constant value.

    Args:
        value: The constant value to return.

    """
    while True:
        yield value
        
def random_choice(iterable):
    """
    Returns a random element from the given iterable.

    Args:
        iterable (iterable): The iterable to choose from.

    """
    while True:
        yield random.choice(iterable)


def random_int(start, end):
    """
    Returns a random integer between start and end, inclusive.

    Args:
        start (int): The starting value of the range.
        end (int): The ending value of the range.

    """
    while True:
        yield random.randint(start, end)


def random_float(start, end):
    """
    Returns a random float between start and end, inclusive.

    Args:
        start (float): The starting value of the range.
        end (float): The ending value of the range.

    """
    while True:
        yield random.uniform(start, end)


def ordered_choice(iterable):
    """
    Returns a random element from the given iterable in order.

    Args:
        iterable (iterable): The iterable to choose from.

    """
    while True:
        yield random.choice(iterable)


def auto_generate_name(category):
    """
    Generates a unique name for a metric or dimension.

    Args:
        category (str): The category of the name, either 'metric' or 'dimension'.

    """
    return f"{category}_{random.randint(1, 100)}"

