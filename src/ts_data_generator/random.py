"""Seedable RNG wrapper around numpy.random.Generator (PCG64)."""

import numpy as np


class SeedableRNG:
    """Wraps a PCG64-backed numpy Generator for deterministic randomness.

    Args:
        seed: Integer seed for the PCG64 bit generator.

    Example:
        >>> rng = SeedableRNG(42)
        >>> rng.normal(0, 1, size=3)
        >>> rng.uniform(0, 1, size=5)
    """

    def __init__(self, seed: int) -> None:
        self._seed = seed
        self._generator = np.random.Generator(np.random.PCG64(seed))

    @property
    def seed(self) -> int:
        return self._seed

    def normal(self, loc: float = 0.0, scale: float = 1.0, size: int | tuple | None = None) -> np.ndarray | float:
        return self._generator.normal(loc=loc, scale=scale, size=size)

    def uniform(self, low: float = 0.0, high: float = 1.0, size: int | tuple | None = None) -> np.ndarray | float:
        return self._generator.uniform(low=low, high=high, size=size)

    def choice(self, a: np.ndarray | list, size: int | None = None, p: np.ndarray | None = None) -> np.ndarray | object:
        return self._generator.choice(a, size=size, p=p)

    def random(self, size: int | tuple | None = None) -> np.ndarray | float:
        return self._generator.random(size=size)
