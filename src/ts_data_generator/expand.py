"""Core mechanics for the ``expand_dimensions`` engine feature (#54).

With ``expand_dimensions`` on, the engine emits one row per
*(timestamp x Cartesian product of all enumerable dimensions' distinct
values)*, each combination carrying its own independently regenerated,
reproducible metric series — so filtering by any dimension value yields a
complete, intact, distinct sequential series.

This lifts the #48 prototype's verified logic into the real engine, but reads
the carriers' ``.domain`` (#53) instead of the prototype's ``gi_frame``
introspection + sampling fallback — both rejected by #51 for production. The
domain is captured eagerly on each carrier at construction; the
expand/error classification happens here at expand time.

Standing spec constraints (from the map's destination-pinning grilling):
  * Per-series metrics: ``metric.generate(timestamps)`` run once per combo.
  * Cartesian product of all dimensions' distinct value sets.
  * Only enumerable explicit-list domains expand; non-enumerable generators
    raise :class:`~ts_data_generator.exceptions.ExpandError`.
  * Per-combination seed = stable SHA-256 hash of
    ``(base_seed, sorted [(dimension_name, value), ...])`` — stable across
    processes (Python's ``hash()`` is salted) and order-insensitive (sorted by
    dimension name).
  * Row ordering: timestamp-first, then dimension values lexicographically
    (dimension names taken in alphabetical order so ordering is insensitive to
    the order dimensions were added).
"""

from __future__ import annotations

import hashlib
from itertools import product
from typing import Any

import pandas as pd

from ts_data_generator.carriers import DimensionCarrier
from ts_data_generator.exceptions import ExpandError
from ts_data_generator.random import SeedableRNG
from ts_data_generator.schema.models import Dimensions, Metrics

# The carrier kind reported for an opaque plain generator with no domain.
_OPAQUE_KIND = "custom"


def combination_seed(base_seed: int, combination: list[tuple[str, Any]]) -> int:
    """Stable, order-insensitive per-combination seed.

    ``combination`` is a list of ``(dimension_name, value)`` pairs. It is sorted
    by dimension name before hashing so the seed is independent of the order
    dimensions were added or enumerated. The hash is SHA-256 so it is stable
    across processes (unlike Python's salted ``hash()``).

    Args:
        base_seed: The ``DataGen`` base seed.
        combination: ``(dimension_name, value)`` pairs for one combo.

    Returns:
        An unsigned 32-bit integer seed for the combo's RNG.
    """
    payload = repr((base_seed, sorted(combination, key=lambda kv: kv[0])))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return int(digest, 16) % (2**32)


def _resolve_domain(name: str, dimension: Dimensions) -> list[Any]:
    """Return the expandable domain of a dimension, or raise ``ExpandError``.

    Reads the carrier's ``.domain`` with zero introspection. A non-expandable
    carrier (numeric range / auto-generated name) or a plain generator without
    an explicit ``domain=`` (the opaque custom case) raises :class:`ExpandError`
    naming the dimension and the reason — the silent partial-expansion shape
    ruled out of scope.
    """
    fn = dimension.function
    if not isinstance(fn, DimensionCarrier):
        raise ExpandError(
            f"dimension {name!r} cannot be expanded: it is an opaque generator "
            f"({_OPAQUE_KIND}) with no known domain. Provide a finite value list "
            f"via random_choice/ordered_choice/constant, a static list, or declare "
            f"its domain explicitly with domain= in add_dimension."
        )
    if not fn.expandable:
        raise ExpandError(
            f"dimension {name!r} cannot be expanded: {fn.func_name}() is a "
            f"non-enumerable generator ({fn.non_expandable_reason}). "
            f"Use random_choice/ordered_choice/constant or a static list instead."
        )
    domain = fn.domain
    assert domain is not None  # expandable carriers always carry a domain
    return domain


def build_expanded_dataframe(
    dimensions: dict[str, Dimensions],
    metrics: dict[str, Metrics],
    timestamps: pd.DatetimeIndex,
    base_seed: int,
) -> pd.DataFrame:
    """Build the expanded DataFrame: one row per (timestamp x combination).

    Each combination carries its own independently regenerated metric series,
    seeded deterministically per combination. Rows are ordered timestamp-first,
    then by dimension values lexicographically (dimension names in alphabetical
    order, so ordering is insensitive to the order dimensions were added).

    Args:
        dimensions: Mapping of dimension name to ``Dimensions`` instance.
        metrics: Mapping of metric name to ``Metrics`` instance.
        timestamps: The full timestamp index for the dataset.
        base_seed: The base seed (a derived default when the engine is unseeded).

    Returns:
        A DataFrame indexed by timestamp with dimension columns, metric signal
        columns, and any ``<metric>_anomaly`` label columns — sorted
        timestamp-first then by dimension value.
    """
    # Alphabetical dimension-name order -> order-insensitive seeding + ordering.
    dim_names = sorted(dimensions)
    domains = [_resolve_domain(name, dimensions[name]) for name in dim_names]

    frames: list[pd.DataFrame] = []
    for combo_values in product(*domains):
        # (name, value) pairs in alphabetical dimension-name order.
        combo_pairs = list(zip(dim_names, combo_values, strict=True))
        seed = combination_seed(base_seed, combo_pairs)
        rng = SeedableRNG(seed)

        combo_df = pd.DataFrame(index=timestamps)
        combo_df["_ts"] = timestamps
        for metric in metrics.values():
            result = metric.generate(timestamps, rng=rng)
            combo_df = pd.concat([combo_df, result.signal], axis=1)
            if not result.labels.empty:
                combo_df = pd.concat([combo_df, result.labels], axis=1)
        # Broadcast the fixed dimension values across all timestamps of this combo.
        for name, value in combo_pairs:
            combo_df[name] = value
        frames.append(combo_df)

    if not frames:
        return pd.DataFrame(index=timestamps)

    out = pd.concat(frames, axis=0, ignore_index=True)
    out = out.sort_values(by=["_ts", *dim_names], kind="stable").reset_index(drop=True)
    out = out.set_index("_ts")
    out.index.name = None
    return out
