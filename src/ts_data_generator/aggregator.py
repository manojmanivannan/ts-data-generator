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
) -> pd.DataFrame:
    """Resample *data* from *from_granularity* to *to_granularity*.

    Each metric is aggregated according to its ``aggregation_type``
    (e.g. mean, sum).  Dimensions are used as groupby keys.  Multi-items
    with an explicit ``aggregation_type`` are treated as metrics, otherwise
    they join the groupby keys.

    Args:
        data: The source DataFrame (assumed indexed by timestamp).
        metrics: Mapping of metric name to ``Metrics`` instance.
        dimensions: Mapping of dimension name to ``Dimensions`` instance.
        multi_items: Mapping of comma-joined names to ``MultiItems`` instance.
        from_granularity: Current granularity of the data (e.g. ``"5min"``).
        to_granularity: Target granularity (e.g. ``"h"``, ``"D"``).

    Returns:
        A new DataFrame aggregated to *to_granularity*.

    Raises:
        AggregationError: If *to_granularity* is finer than *from_granularity*.
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

    group_keys = list(dimensions.keys())

    for key, multi_item in multi_items.items():
        if multi_item.aggregation_type:
            for i, item_name in enumerate(key.split(",")):
                atype = multi_item.aggregation_type[i]
                agg_dict[item_name] = (
                    atype.value if isinstance(atype, AggregationType) else atype
                )
        else:
            group_keys.extend(key.split(","))

    resample_freq = target.resample_alias()

    resampled = (
        data.drop("epoch", axis=1, errors="ignore")
        .reset_index()
        .groupby(group_keys)
        .resample(resample_freq, on="index")
        .agg(agg_dict)
        .reset_index()
        .set_index("index")
        .sort_index()
    )

    if isinstance(resampled.columns, pd.MultiIndex):
        resampled.columns = resampled.columns.get_level_values(0)

    resampled["epoch"] = resampled.index.astype("int64") // 10**9
    return resampled
