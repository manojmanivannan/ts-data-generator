"""Core mechanics for the ``expand_dimensions`` engine feature (#54, #57).

With ``expand_dimensions`` on, the engine emits one row per
*(timestamp x Cartesian product of all enumerable dimensions' distinct
values)*, each combination carrying its own independently regenerated,
reproducible metric series — so filtering by any dimension value yields a
complete, intact, distinct sequential series.

Per-dimension control (#57, decision #52) makes the global flag an overridable
default. Each dimension's effective expansion is
``dim.expand if dim.expand is not None else global``: ``expand=True`` forces a
dimension into the product (even with the global flag off), ``expand=False``
opts it out. The Cartesian product runs over **expanding dimensions only**; a
non-expanding dimension instead regenerates one-value-per-timestamp *within*
each series, varying independently across combos (a categorical within-series
field, not a broadcast). ``expand=False`` is also the escape hatch for
non-enumerable dimensions: excluded from the product, no ``ExpandError`` — the
error fires only for a dimension that is *actually expanding*.

This lifts the #48 prototype's verified logic into the real engine, but reads
the carriers' ``.domain`` (#53) instead of the prototype's ``gi_frame``
introspection + sampling fallback — both rejected by #51 for production. The
domain is captured eagerly on each carrier at construction; the
expand/error classification happens here at expand time.

Standing spec constraints (from the map's destination-pinning grilling):
  * Per-series metrics: ``metric.generate(timestamps)`` run once per combo.
  * Cartesian product of *expanding* dimensions' distinct value sets only.
  * Only enumerable explicit-list domains expand; a non-enumerable dimension
    that is actually expanding raises :class:`~ts_data_generator.exceptions.
    ExpandError` (``expand=False`` opts out instead of erroring).
  * Per-combination seed = stable SHA-256 hash of
    ``(base_seed, sorted [(dimension_name, value), ...])`` over the *expanding*
    dims only — stable across processes (Python's ``hash()`` is salted) and
    order-insensitive (sorted by dimension name).
  * Row ordering: timestamp-first, then dimension values lexicographically
    (dimension names taken in alphabetical order so ordering is insensitive to
    the order dimensions were added).
"""

from __future__ import annotations

import hashlib
from itertools import product
from typing import Any

import numpy as np
import pandas as pd

from ts_data_generator.carriers import DimensionCarrier
from ts_data_generator.exceptions import ExpandError
from ts_data_generator.random import SeedableRNG
from ts_data_generator.schema.models import Dimensions, Metrics, MultiItems

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


def compute_combination_scale(
    combo_pairs: list[tuple[str, Any]],
    dimensions: dict[str, Dimensions],
    linked_dims: dict[str, MultiItems],
    rng: SeedableRNG,
    scale_variance: float = 0.0,
) -> float:
    """Compute the effective scale factor for a combination of expanding dimensions.

    Combines explicit weights defined on Dimensions / MultiItems multiplicatively,
    and applies a stochastic scale multiplier if scale_variance > 0.
    """
    scale = 1.0
    for key, val in combo_pairs:
        if key in dimensions:
            dim = dimensions[key]
            if dim.weights and val in dim.weights:
                scale *= float(dim.weights[val])
        elif key in linked_dims:
            mi = linked_dims[key]
            if mi.weights and val in mi.weights:
                scale *= float(mi.weights[val])

    if scale_variance > 0.0:
        scale *= float(np.exp(rng.normal(0, scale_variance)))

    return scale


def resolve_expand(dimension: Dimensions | MultiItems, global_expand: bool) -> bool:
    """Resolve a dimension's effective expansion against the global flag.

    ``None`` inherits the global flag; ``True``/``False`` override it
    (#57, decision #52). This is the flag logic only — it does not touch the
    carrier or resolve the domain, so it never raises ``ExpandError``.
    """
    if dimension.expand is not None:
        return dimension.expand
    return global_expand


def _resolve_domain(name: str, dimension: Dimensions | MultiItems) -> list[Any]:
    """Return the expandable domain of a dimension or linked dimension, or raise ``ExpandError``.

    Reads the carrier's ``.domain`` with zero introspection. A non-expandable
    carrier (numeric range / auto-generated name) or a plain generator without
    an explicit ``domain=`` (the opaque custom case) raises :class:`ExpandError`
    naming the dimension and the reason — the silent partial-expansion shape
    ruled out of scope. This only runs for dimensions that are *actually
    expanding*; a non-enumerable dim marked ``expand=False`` never reaches here.
    """
    fn = dimension.function
    if not isinstance(fn, DimensionCarrier):
        source_hint = "add_multi_items" if isinstance(dimension, MultiItems) else "add_dimension"
        raise ExpandError(
            f"dimension {name!r} cannot be expanded: it is an opaque generator "
            f"({_OPAQUE_KIND}) with no known domain. Provide a finite value list "
            f"via random_choice/ordered_choice/constant, a static list, or declare "
            f"its domain explicitly with domain= in {source_hint}."
        )
    if not fn.expandable:
        raise ExpandError(
            f"dimension {name!r} cannot be expanded: {fn.func_name}() is a "
            f"non-enumerable generator ({fn.non_expandable_reason}). "
            f"Use random_choice/ordered_choice/constant or a static list instead."
        )
    domain = fn.domain
    assert domain is not None  # expandable carriers always carry a domain
    if isinstance(dimension, MultiItems):
        normalized_domain: list[tuple[Any, ...]] = []
        for item in domain:
            t = tuple(item) if isinstance(item, (list, tuple)) else (item,)
            if len(t) != len(dimension.names):
                raise ExpandError(
                    f"dimension {name!r} cannot be expanded: domain entry {item!r} "
                    f"length ({len(t)}) does not match number of columns ({len(dimension.names)})."
                )
            normalized_domain.append(t)
        return normalized_domain
    return domain


def build_expanded_dataframe(
    dimensions: dict[str, Dimensions],
    metrics: dict[str, Metrics],
    timestamps: pd.DatetimeIndex,
    base_seed: int,
    global_expand: bool = True,
    multi_items: dict[str, MultiItems] | None = None,
    scale_variance: float = 0.0,
) -> pd.DataFrame:
    """Build the expanded DataFrame: one row per (timestamp x combination).

    The Cartesian product runs over **expanding** dimensions only — those whose
    effective expansion (per-dim override falling back to ``global_expand``) is
    ``True`` and which carry an enumerable domain. Linked dimensions (MultiItems
    without ``aggregation_type``) participate in the product as a compound key
    over their distinct-tuple domain. Each combination carries its own
    independently regenerated metric series (both regular metrics and linked
    metrics with ``aggregation_type``), seeded deterministically per
    combination over the expanding dims. Non-expanding dimensions regenerate
    one-value-per-timestamp within each series (varying across combos) instead
    of being broadcast. Rows are ordered timestamp-first, then by dimension
    values lexicographically (compound dimension keys sorted alphabetically,
    with component columns in declared order).

    Args:
        dimensions: Mapping of dimension name to ``Dimensions`` instance.
        metrics: Mapping of metric name to ``Metrics`` instance.
        timestamps: The full timestamp index for the dataset.
        base_seed: The base seed (a derived default when the engine is unseeded).
        global_expand: The global ``expand_dimensions`` flag the per-dim
            ``expand`` override falls back to. Defaults to ``True`` since this
            is only reached on the expansion path.
        multi_items: Optional mapping of comma-joined names to ``MultiItems``
            instance. Linked dimensions join dimension expansion; linked metrics
            regenerate once per combination.
        scale_variance: Standard deviation for stochastic log-normal scaling
            across unique combinations (0.0 = disabled).

    Returns:
        A DataFrame indexed by timestamp with dimension columns, metric signal
        columns, and any ``<metric>_anomaly`` label columns — sorted
        timestamp-first then by dimension value.

    Raises:
        ExpandError: If a dimension that is actually expanding is non-enumerable
            (numeric range / auto-generated name / opaque generator without
            ``domain=``).
    """
    if multi_items is None:
        multi_items = {}

    linked_dims: dict[str, MultiItems] = {
        key: mi for key, mi in multi_items.items() if not mi.aggregation_type
    }
    linked_metrics: dict[str, MultiItems] = {
        key: mi for key, mi in multi_items.items() if mi.aggregation_type
    }

    # Alphabetical (compound) dimension-name order -> order-insensitive seeding + ordering.
    all_dim_keys = sorted(list(dimensions.keys()) + list(linked_dims.keys()))

    expanding_keys: list[str] = []
    expanding_domains: list[list[Any]] = []
    is_linked: list[bool] = []

    non_expanding_scalar_names: list[str] = []
    non_expanding_linked_keys: list[str] = []

    for key in all_dim_keys:
        if key in dimensions:
            dim = dimensions[key]
            if resolve_expand(dim, global_expand):
                expanding_keys.append(key)
                expanding_domains.append(_resolve_domain(key, dim))
                is_linked.append(False)
            else:
                non_expanding_scalar_names.append(key)
        else:
            mi = linked_dims[key]
            if resolve_expand(mi, global_expand):
                expanding_keys.append(key)
                expanding_domains.append(_resolve_domain(key, mi))
                is_linked.append(True)
            else:
                non_expanding_linked_keys.append(key)

    frames: list[pd.DataFrame] = []
    for combo_values in product(*expanding_domains):
        # (key, value) pairs for the expanding dims, alphabetical key order.
        # For scalar dim: ("region", "US").
        # For linked dim: ("city,state", ("NYC", "NY")).
        combo_pairs = list(zip(expanding_keys, combo_values, strict=True))
        seed = combination_seed(base_seed, combo_pairs)
        rng = SeedableRNG(seed)
        combo_scale = compute_combination_scale(
            combo_pairs, dimensions, linked_dims, rng, scale_variance=scale_variance
        )

        combo_df = pd.DataFrame(index=timestamps)
        combo_df["_ts"] = timestamps

        # 1. Regular metrics
        for metric in metrics.values():
            result = metric.generate(timestamps, rng=rng, scale=combo_scale)
            combo_df = pd.concat([combo_df, result.signal], axis=1)
            if not result.labels.empty:
                combo_df = pd.concat([combo_df, result.labels], axis=1)

        # 2. Linked metrics (regenerate once per combination)
        for mi in linked_metrics.values():
            generated = mi.generate(timestamps, rng=rng)
            if combo_scale != 1.0:
                num_cols = generated.select_dtypes(include="number").columns
                if not num_cols.empty:
                    generated = generated.copy()
                    generated[num_cols] = generated[num_cols] * combo_scale
            combo_df = pd.concat([combo_df, generated], axis=1)

        # 3. Expanding dimensions (broadcast fixed combination value)
        for key, val, linked in zip(expanding_keys, combo_values, is_linked, strict=True):
            if not linked:
                combo_df[key] = val
            else:
                mi = linked_dims[key]
                for comp_name, comp_val in zip(mi.names, val, strict=True):
                    combo_df[comp_name] = comp_val

        # 4. Non-expanding scalar dimensions (regenerate within series)
        for name in non_expanding_scalar_names:
            generated = dimensions[name].generate(timestamps)
            combo_df[name] = generated[name].to_numpy()

        # 5. Non-expanding linked dimensions (regenerate within series)
        for key in non_expanding_linked_keys:
            mi = linked_dims[key]
            generated = mi.generate(timestamps)
            for comp_name in mi.names:
                combo_df[comp_name] = generated[comp_name].to_numpy()

        frames.append(combo_df)

    if not frames:
        return pd.DataFrame(index=timestamps)

    # Ordering: one alphabetical slot per compound name; component columns sort
    # in declared MultiItems.names order.
    sort_cols: list[str] = ["_ts"]
    for key in all_dim_keys:
        if key in dimensions:
            sort_cols.append(key)
        else:
            sort_cols.extend(linked_dims[key].names)

    out = pd.concat(frames, axis=0, ignore_index=True)
    out = out.sort_values(by=sort_cols, kind="stable").reset_index(drop=True)
    out = out.set_index("_ts")
    out.index.name = None
    return out
