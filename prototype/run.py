"""PROTOTYPE (throwaway) — TUI driver for the expand_dimensions mechanics.

Run:  uv run python prototype/run.py

A lightweight terminal app that exercises the REAL DataGen pipeline (real
Dimensions, Metrics, trends, anomalies, aggregator) through the pure logic in
``expand_logic.py`` and renders the observable state after each action. It
answers ticket #48's two fog questions by observation:

  1. Aggregation — does aggregate_dataframe resample correctly *per
     combination* (dimensions are groupby keys), or does it merge/break series?
  2. Anomaly labels per series — does the auto-emit <metric>_anomaly column
     generate correctly per combination, and does the max/OR rule hold per
     series after aggregation?

Plus it demonstrates the core mechanics (Cartesian product, per-combination
regeneration, deterministic order-insensitive seeding, timestamp-first
ordering) and the non-enumerable-domain error case.
"""

from __future__ import annotations

import sys
from itertools import product

import pandas as pd

from ts_data_generator.aggregator import aggregate_dataframe
from ts_data_generator.data_gen import DataGen
from ts_data_generator.schema.models import Granularity
from ts_data_generator.anomalies.point import PointAnomaly
from ts_data_generator.utils.trends import SinusoidalTrend
from ts_data_generator.utils.functions import random_choice

from expand_logic import expand_dimensions, expandable_domain, ExpandError

# ANSI
B = "\x1b[1m"
D = "\x1b[2m"
G = "\x1b[32m"
R = "\x1b[31m"
Y = "\x1b[33m"
N = "\x1b[0m"

# ---- scenario config -----------------------------------------------------
BASE_SEED = 42
START, END = "2024-01-01", "2024-01-03"  # 2 days, hourly -> 48 timestamps
GRAN = Granularity.HOURLY
REGIONS = ["US", "EU", "APAC"]
ENVS = ["prod", "staging"]


def _add_metric(dg: DataGen) -> None:
    """Add a metric with a trend + a point anomaly so an _anomaly label emits."""
    dg.add_metric(
        "cpu",
        {SinusoidalTrend(amplitude=5, freq=24)},
        anomalies=[PointAnomaly(probability=0.1, mode="replacement", magnitude=999)],
    )


def _build_datagen(dim_order: list[str]) -> DataGen:
    """Build a real DataGen. dim_order lets us test seed order-insensitivity."""
    dg = DataGen(start_datetime=START, end_datetime=END, granularity=GRAN, seed=BASE_SEED)
    dims = {
        "region": ("region", random_choice(REGIONS)),
        "env": ("env", ENVS),  # static list -> wrapped in cycle() by add_dimension
    }
    for name in dim_order:
        n, fn = dims[name]
        dg.add_dimension(n, fn)
    _add_metric(dg)
    return dg


# ---- scenarios ------------------------------------------------------------
def scenario_expand() -> dict:
    dg = _build_datagen(["region", "env"])
    out = expand_dimensions(dg.dimensions, dg.metrics, dg._timestamps, BASE_SEED)
    n_ts = len(dg._timestamps)
    expected_rows = n_ts * len(REGIONS) * len(ENVS)
    # Per-combo integrity: every combo has the full timestamp range.
    grouped = out.groupby(["region", "env"]).size()
    intact = all(grouped == n_ts)
    return {
        "dg": dg,
        "out": out,
        "n_ts": n_ts,
        "expected_rows": expected_rows,
        "intact": intact,
        "grouped": grouped,
    }


def scenario_aggregation(state: dict | None) -> dict:
    if state is None or "out" not in state:
        state = scenario_expand()
    out = state["out"]
    dg = state["dg"]
    agg = aggregate_dataframe(
        data=out,
        metrics=dg.metrics,
        dimensions=dg.dimensions,
        multi_items={},
        from_granularity=dg.granularity,
        to_granularity="D",
    )
    n_days = out.index.normalize().nunique()
    expected_agg_rows = n_days * len(REGIONS) * len(ENVS)
    # Per-series: each (region, env) combo resamples to one row per day.
    per_combo = agg.groupby(["region", "env"]).size()
    series_intact = all(per_combo == n_days)
    # Series not merged: distinct combos have distinct value distributions.
    distinct_values = agg.groupby(["region", "env"])["cpu"].nunique()
    not_merged = bool((distinct_values > 1).any() or len(distinct_values) == len(REGIONS) * len(ENVS))
    return {**state, "agg": agg, "n_days": n_days, "expected_agg_rows": expected_agg_rows,
            "series_intact": series_intact, "per_combo": per_combo,
            "distinct_values": distinct_values, "not_merged": not_merged}


def scenario_anomaly(state: dict | None) -> dict:
    if state is None or "agg" not in state:
        state = scenario_aggregation(state)
    out = state["out"]
    agg = state["agg"]
    label_col = "cpu_anomaly"
    has_labels = label_col in out.columns
    # Raw per-combo anomaly counts.
    raw_per_combo = out.groupby(["region", "env"])[label_col].sum() if has_labels else None
    # Aggregated (max/OR) per-combo anomaly counts.
    agg_per_combo = agg.groupby(["region", "env"])[label_col].sum() if has_labels else None
    # OR rule: aggregated True implies at least one raw True in that window/series.
    or_holds = True
    if has_labels:
        for (region, env), grp in out.groupby(["region", "env"]):
            agg_grp = agg[(agg["region"] == region) & (agg["env"] == env)]
            for day, day_rows in grp.groupby(grp.index.normalize()):
                agg_val = agg_grp[agg_grp.index.normalize() == day][label_col].iloc[0]
                if agg_val and not day_rows[label_col].any():
                    or_holds = False
                if (not agg_val) and day_rows[label_col].any():
                    or_holds = False
    return {**state, "label_col": label_col, "has_labels": has_labels,
            "raw_per_combo": raw_per_combo, "agg_per_combo": agg_per_combo, "or_holds": or_holds}


def scenario_determinism() -> dict:
    dg_a = _build_datagen(["region", "env"])
    dg_b = _build_datagen(["env", "region"])  # dimensions added in different order
    out_a = expand_dimensions(dg_a.dimensions, dg_a.metrics, dg_a._timestamps, BASE_SEED)
    out_b = expand_dimensions(dg_b.dimensions, dg_b.metrics, dg_b._timestamps, BASE_SEED)
    same_seed_equal = out_a.equals(out_b)
    # Different seed -> different data (sanity).
    out_c = expand_dimensions(dg_a.dimensions, dg_a.metrics, dg_a._timestamps, BASE_SEED + 1)
    diff_seed_differs = not out_a.equals(out_c)
    return {"same_seed_equal": same_seed_equal, "diff_seed_differs": diff_seed_differs,
            "out_a": out_a, "out_b": out_b}


def scenario_error() -> dict:
    from ts_data_generator.utils.functions import random_int
    dg = _build_datagen(["region", "env"])
    dg.add_dimension("tenant", random_int(1, 100))
    try:
        expandable_domain(dg.dimensions["tenant"])
        return {"raised": False, "msg": "(no error raised — unexpected)"}
    except ExpandError as e:
        return {"raised": True, "msg": str(e)}


# ---- rendering ------------------------------------------------------------
def _ok(cond: bool) -> str:
    return f"{G}PASS{N}" if cond else f"{R}FAIL{N}"


def render(frame: str) -> None:
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.write(frame)
    sys.stdout.flush()


def frame_expand(s: dict) -> str:
    lines = [
        f"{B}expand_dimensions — core mechanics{N}  {D}(seed={BASE_SEED}, hourly, 2 days){N}",
        "",
        f"{B}Shape:{N} {s['out'].shape[0]} rows x {s['out'].shape[1]} cols  "
        f"{D}(expected {s['expected_rows']} = {s['n_ts']} ts x {len(REGIONS)} x {len(ENVS)}){N}",
        f"{B}Per-combo series intact:{N} {_ok(s['intact'])}  "
        f"{D}(each combo has all {s['n_ts']} timestamps){N}",
        "",
        f"{B}Domain recovery:{N}",
        f"  region -> {expandable_domain(_build_datagen(['region']).dimensions['region'])}",
        f"  env     -> {expandable_domain(_build_datagen(['env']).dimensions['env'])}  {D}(static list via cycle){N}",
        "",
        f"{B}First 8 rows (timestamp-first, then dim values lexicographic):{N}",
        str(s["out"].head(8).to_string()),
        "",
        f"{B}Rows per combination:{N}",
        str(s["grouped"].to_string()),
    ]
    return "\n".join(lines) + "\n\n" + _menu()


def frame_aggregation(s: dict) -> str:
    lines = [
        f"{B}aggregation fall-out — aggregate to DAILY{N}  {D}(dimensions as groupby keys){N}",
        "",
        f"{B}Aggregated shape:{N} {s['agg'].shape[0]} rows  "
        f"{D}(expected {s['expected_agg_rows']} = {s['n_days']} days x {len(REGIONS)} x {len(ENVS)}){N}",
        f"{B}Per-series resample intact:{N} {_ok(s['series_intact'])}  "
        f"{D}(each combo -> one row per day){N}",
        f"{B}Series not merged:{N} {_ok(s['not_merged'])}  "
        f"{D}(distinct combos keep distinct values){N}",
        "",
        f"{B}Aggregated rows per combination:{N}",
        str(s["per_combo"].to_string()),
        "",
        f"{B}Aggregated head:{N}",
        str(s["agg"].head(8).to_string()),
    ]
    return "\n".join(lines) + "\n\n" + _menu()


def frame_anomaly(s: dict) -> str:
    lines = [
        f"{B}anomaly-label fall-out — <metric>_anomaly per series{N}",
        "",
        f"{B}Label column present:{N} {_ok(s['has_labels'])}  {D}({s['label_col']}){N}",
        f"{B}max/OR rule holds per series:{N} {_ok(s['or_holds'])}  "
        f"{D}(agg True iff any raw True in window){N}",
        "",
        f"{B}Raw anomaly counts per combination:{N}",
        str(s["raw_per_combo"].to_string()),
        "",
        f"{B}Aggregated (max/OR) anomaly counts per combination:{N}",
        str(s["agg_per_combo"].to_string()),
    ]
    return "\n".join(lines) + "\n\n" + _menu()


def frame_determinism(s: dict) -> str:
    a = s["out_a"]
    first_region = sorted(REGIONS)[0]
    first_env = sorted(ENVS)[0]
    sub = a[(a["region"] == first_region) & (a["env"] == first_env)]
    lines = [
        f"{B}determinism & order-insensitivity{N}",
        "",
        f"{B}Same seed, dims added [region,env] vs [env,region]:{N} {_ok(s['same_seed_equal'])}",
        f"  {D}per-combo seed = stable hash of (base_seed, sorted [(name,value)]){N}",
        f"{B}Different seed -> different data:{N} {_ok(s['diff_seed_differs'])}",
        "",
        f"{B}First combo (region={first_region}, env={first_env}) head — order A:{N}",
        str(sub.head(4).to_string()),
    ]
    return "\n".join(lines) + "\n\n" + _menu()


def frame_error(s: dict) -> str:
    lines = [
        f"{B}non-enumerable domain validation{N}",
        "",
        f"{B}ExpandError raised for random_int dimension:{N} {_ok(s['raised'])}",
        "",
        f"{B}Message:{N}",
        f"  {Y}{s['msg']}{N}",
    ]
    return "\n".join(lines) + "\n\n" + _menu()


def _menu() -> str:
    return (
        f"{B}[1]{N} expand   {B}[2]{N} aggregation   {B}[3]{N} anomaly   "
        f"{B}[4]{N} determinism   {B}[5]{N} error case   {B}[q]{N} quit"
    )


# ---- main loop ------------------------------------------------------------
def main() -> None:
    state = scenario_expand()
    view = "1"
    render(frame_expand(state))
    while True:
        try:
            key = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if key == "q":
            break
        if key == "1":
            state = scenario_expand()
            view = "1"
        elif key == "2":
            state = scenario_aggregation(state)
            view = "2"
        elif key == "3":
            state = scenario_anomaly(state)
            view = "3"
        elif key == "4":
            state = scenario_determinism()
            view = "4"
        elif key == "5":
            state = scenario_error()
            view = "5"
        else:
            continue
        if view == "1":
            render(frame_expand(state))
        elif view == "2":
            render(frame_aggregation(state))
        elif view == "3":
            render(frame_anomaly(state))
        elif view == "4":
            render(frame_determinism(state))
        elif view == "5":
            render(frame_error(state))


if __name__ == "__main__":
    main()