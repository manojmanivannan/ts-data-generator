"""PROTOTYPE (throwaway) — expand_dimensions core mechanics.

This is the liftable logic module behind the prototype TUI in ``run.py``.
It is deliberately pure: no I/O, no terminal code. The TUI imports it and
calls into it; nothing flows the other direction. When the question on
ticket #48 is answered, this module is the bit worth keeping.

Question being prototyped
-------------------------
Does a global ``expand_dimensions`` flag work as designed — turning output
from one row per timestamp into one row per (timestamp x Cartesian product
of all explicit-list dimensions' distinct values), each combination carrying
its own independently-regenerated, reproducible metric series — and do
aggregation and the auto-emit ``<metric>_anomaly`` column fall out correctly
per series?

Standing spec constraints (from the map's destination-pinning grilling)
encoded here:
  - Global toggle; all dimensions expand.
  - Per-series metrics: ``metric.generate(timestamps)`` run once per combo.
  - Cartesian product of all dimensions' distinct value sets.
  - Only explicit-list domains expand; non-enumerable generators error.
  - Per-combination seed = stable hash of (base_seed, sorted [(name, value)]).
  - Row ordering: timestamp-first, then dimension values lexicographically
    (dimension names taken in alphabetical order so ordering is insensitive
    to the order dimensions were added).
"""

from __future__ import annotations

import hashlib
from itertools import product
from typing import Any

import pandas as pd

from ts_data_generator.random import SeedableRNG
from ts_data_generator.schema.models import Dimensions, Metrics

# Generators whose domain is a finite explicit list and may expand.
_EXPLICIT_QUALNAMES = {"random_choice", "ordered_choice", "constant"}
# Generators with a numeric range domain — rejected even when the range is
# small, because enumerating ranges risks silent row-count explosion.
_RANGE_QUALNAMES = {"random_int", "random_float"}

# Fallback sampling caps for opaque generators (e.g. itertools.cycle wrapping
# a static list). Draw up to _SAMPLE_CAP values; if the distinct set exceeds
# _DOMAIN_CAP or is still growing at the sample limit, declare non-enumerable.
_SAMPLE_CAP = 512
_DOMAIN_CAP = 64


class ExpandError(ValueError):
    """Raised when a dimension cannot be expanded (non-enumerable domain)."""


def expandable_domain(dimension: Dimensions) -> list[Any]:
    """Return the sorted distinct value domain of an expandable dimension.

    Only explicit-list dimensions expand. A non-enumerable generator (a numeric
    range, or an opaque generator whose distinct values keep growing) raises
    ``ExpandError``.

    The domain is recovered exactly when the generator's source function is
    introspectable (``random_choice`` / ``ordered_choice`` / ``constant``) via
    its frame locals; opaque generators (e.g. ``itertools.cycle`` wrapping a
    static list) fall back to sampling with a cap.
    """
    fn = dimension.function
    qualname = getattr(getattr(fn, "gi_code", None), "co_qualname", None)

    if qualname in _RANGE_QUALNAMES:
        raise ExpandError(
            f"dimension {dimension.name!r} uses {qualname}(), a non-enumerable "
            f"range generator; cannot expand. Use random_choice/ordered_choice/"
            f"constant or a static list instead."
        )

    if qualname in _EXPLICIT_QUALNAMES:
        locals_ = fn.gi_frame.f_locals
        if qualname == "constant":
            value = locals_["value"]
            domain = list(value) if isinstance(value, (list, tuple)) else [value]
        else:  # random_choice / ordered_choice
            domain = list(locals_["iterable"])
        return _dedupe_sort(domain)

    # Opaque generator (no gi_code, e.g. itertools.cycle) — sample to recover.
    return _sample_domain(dimension)


def _sample_domain(dimension: Dimensions) -> list[Any]:
    seen: set[Any] = set()
    ordered: list[Any] = []
    for _ in range(_SAMPLE_CAP):
        value = next(dimension.function)
        if value not in seen:
            seen.add(value)
            ordered.append(value)
            if len(seen) > _DOMAIN_CAP:
                raise ExpandError(
                    f"dimension {dimension.name!r} has a non-enumerable domain "
                    f"(> {_DOMAIN_CAP} distinct values sampled); cannot expand."
                )
    # If we hit the sample cap and the set is still at the cap's edge, it may
    # still be growing — treat as non-enumerable when near the boundary.
    if len(seen) >= _SAMPLE_CAP:
        raise ExpandError(
            f"dimension {dimension.name!r} domain not resolved within "
            f"{_SAMPLE_CAP} samples; cannot expand."
        )
    return _dedupe_sort(ordered)


def _dedupe_sort(values: list[Any]) -> list[Any]:
    """Stable de-duplication preserving first-seen order, then sort.

    Sorting uses a string key so mixed-type domains (e.g. ints and strings)
    sort deterministically without raising on cross-type comparison.
    """
    seen: set[Any] = set()
    distinct = [v for v in values if not (v in seen or seen.add(v))]
    return sorted(distinct, key=lambda v: (str(type(v)), str(v)))


def combination_seed(base_seed: int, combination: list[tuple[str, Any]]) -> int:
    """Stable, order-insensitive per-combination seed.

    ``combination`` is a list of ``(dimension_name, value)`` pairs. It is
    sorted before hashing so the seed is independent of the order dimensions
    were added or enumerated. The hash is SHA-256 so it is stable across
    processes (unlike Python's salted ``hash()``).
    """
    payload = repr((base_seed, sorted(combination, key=lambda kv: kv[0])))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return int(digest, 16) % (2**32)


def expand_dimensions(
    dimensions: dict[str, Dimensions],
    metrics: dict[str, Metrics],
    timestamps: pd.DatetimeIndex,
    base_seed: int,
) -> pd.DataFrame:
    """Build the expanded DataFrame: one row per (timestamp x combination).

    Each combination carries its own independently-regenerated metric series,
    seeded deterministically per combination. Rows are ordered timestamp-first,
    then by dimension values lexicographically (dimension names in alphabetical
    order).
    """
    dim_names = sorted(dimensions)  # alphabetical -> order-insensitive
    domains = [expandable_domain(dimensions[name]) for name in dim_names]

    frames: list[pd.DataFrame] = []
    for combo_values in product(*domains):
        # (name, value) pairs in alphabetical dimension-name order.
        combo_pairs = list(zip(dim_names, combo_values))
        seed = combination_seed(base_seed, combo_pairs)
        rng = SeedableRNG(seed)

        per_metric_frames: list[pd.DataFrame] = []
        for metric in metrics.values():
            result = metric.generate(timestamps, rng=rng)
            per_metric_frames.append(result.signal)
            if not result.labels.empty:
                per_metric_frames.append(result.labels)

        combo_df = pd.concat(per_metric_frames, axis=1) if per_metric_frames else pd.DataFrame(index=timestamps)
        # Broadcast the fixed dimension values across all timestamps.
        for name, value in combo_pairs:
            combo_df[name] = value
        combo_df["_ts"] = timestamps
        frames.append(combo_df)

    if not frames:
        return pd.DataFrame(index=timestamps)

    out = pd.concat(frames, axis=0, ignore_index=True)
    out = out.sort_values(by=["_ts", *dim_names], kind="stable").reset_index(drop=True)
    out = out.set_index("_ts")
    out.index.name = None
    return out