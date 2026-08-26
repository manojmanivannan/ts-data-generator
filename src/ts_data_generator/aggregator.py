"""DataFrame aggregation utilities for coarser-granularity resampling.

Provides :func:`aggregate_dataframe` which resamples a time-series DataFrame
to a coarser granularity, respecting per-metric and multi-item aggregation
types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from ts_data_generator.exceptions import AggregationError
from ts_data_generator.schema.models import AggregationType, Granularity

if TYPE_CHECKING:
    from ts_data_generator.schema.models import Dimensions, Metrics, MultiItems


def aggregate_dataframe(
    data: pd.DataFrame,
    metrics: dict[str, Metrics],
    dimensions: dict[str, Dimensions],
    multi_items: dict[str, MultiItems],
    *,
    from_granularity: str,
    to_granularity: str,
    by: list[str] | None = None,
) -> pd.DataFrame:
    """Resample *data* from *from_granularity* to *to_granularity*.

    Each metric is aggregated according to its ``aggregation_type``
    (e.g. mean, sum).  Dimensions are used as groupby keys.  Multi-items
    with an explicit ``aggregation_type`` are treated as metrics, otherwise
    they join the groupby keys.

    When ``expand_dimensions`` has emitted one row per
    *(timestamp x dimension combination)*, pass *by* to roll up across a
    **subset** of dimensions: only the columns named in *by* are kept as
    groupby keys; every other dimension is aggregated away (its values
    combined through each metric's ``aggregation_type``).  *by* lists
    individual column names, so the components of a linked dimension
    (``MultiItems`` without ``aggregation_type``) may be kept or rolled up
    independently — e.g. ``by=["region", "city"]`` keeps ``region`` and
    ``city`` while rolling up a companion ``store_id`` column.

    Args:
        data: The source DataFrame (assumed indexed by timestamp).
        metrics: Mapping of metric name to ``Metrics`` instance.
        dimensions: Mapping of dimension name to ``Dimensions`` instance.
        multi_items: Mapping of comma-joined names to ``MultiItems`` instance.
        from_granularity: Current granularity of the data (e.g. ``"5min"``).
        to_granularity: Target granularity (e.g. ``"h"``, ``"D"``).
        by: Optional subset of dimension column names to group by.  ``None``
            (default) groups by every dimension and linked-dimension column
            (the historical behaviour).  An empty list aggregates away *all*
            dimensions, leaving a pure time-only resample.  Every entry must
            be a groupable column (a dimension name or a linked-dimension
            component); metric names are rejected.

    Returns:
        A new DataFrame aggregated to *to_granularity*.

    Raises:
        AggregationError: If *to_granularity* is finer than *from_granularity*,
            or if *by* names a column that is not a groupable dimension.
        KeyError: If *to_granularity* is not a recognised granularity string.
    """
    target = Granularity(to_granularity)
    current = Granularity(from_granularity)
    if target.finer_than(current):
        raise AggregationError(
            f"Cannot aggregate to finer granularity ({to_granularity}) "
            f"than current ({from_granularity})."
        )

    agg_dict: dict[str, str] = {
        name: metric.aggregation_type.value for name, metric in metrics.items()
    }

    # Auto-derived anomaly-label columns aggregate as a boolean OR (``max``):
    # if any point in a resample window was anomalous, label the window True.
    for name in metrics:
        label_col = f"{name}_anomaly"
        if label_col in data.columns:
            agg_dict[label_col] = "max"

    # Full set of groupable columns: scalar dimension names plus the
    # component columns of linked dimensions (MultiItems without an
    # aggregation_type). Multi-items *with* an aggregation_type are linked
    # metrics and join agg_dict instead.
    groupable: list[str] = list(dimensions.keys())

    for key, multi_item in multi_items.items():
        if multi_item.aggregation_type:
            for i, item_name in enumerate(key.split(",")):
                atype = multi_item.aggregation_type[i]
                agg_dict[item_name] = atype.value if isinstance(atype, AggregationType) else atype
        else:
            groupable.extend(key.split(","))

    if by is None:
        group_keys = groupable
    else:
        unknown = [name for name in by if name not in groupable]
        if unknown:
            raise AggregationError(
                f"by contains non-groupable column(s) {unknown}. Groupable columns: {groupable}."
            )
        group_keys = list(by)

    resample_freq = target.resample_alias()
    source = data.drop("epoch", axis=1, errors="ignore").reset_index()

    if group_keys:
        resampled = (
            source.groupby(group_keys)
            .resample(resample_freq, on="index")
            .agg(agg_dict)
            .reset_index()
            .set_index("index")
            .sort_index()
        )
    else:
        # No dimension groupby (e.g. by=[] rolling up every dimension): a
        # plain time-only resample, identical to groupby with no keys.
        resampled = (
            source.resample(resample_freq, on="index")
            .agg(agg_dict)
            .reset_index()
            .set_index("index")
            .sort_index()
        )

    if isinstance(resampled.columns, pd.MultiIndex):
        resampled.columns = resampled.columns.get_level_values(0)

    resampled["epoch"] = resampled.index.astype("int64") // 10**9
    return resampled
