import marimo

__generated_with = "0.24.0"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
 
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Aggregation Example
    """)
    return


@app.cell
def _():
    # Import the Data generator class from the ts_data_generator module
    from ts_data_generator import DataGen
    from ts_data_generator.schema.models import AggregationType
    from ts_data_generator.utils.functions import random_choice, random_int
    from ts_data_generator.utils.trends import (
        SinusoidalTrend,
        LinearTrend,
    )
    import random

    return (
        AggregationType,
        DataGen,
        LinearTrend,
        SinusoidalTrend,
        random,
        random_choice,
    )


@app.cell
def _(
    AggregationType,
    DataGen,
    LinearTrend,
    SinusoidalTrend,
    random,
    random_choice,
):
    d = DataGen()
    d.start_datetime = "2019-01-01"
    d.end_datetime = "2019-02-28"
    d.to_granularity("h")


    d.add_dimension("product", random_choice(["A", "B", "C", "D"]))
    d.add_dimension(name="interface", function="X Y Z".split())

    d.add_metric(
        name="sinusoidal",
        trends=[
            SinusoidalTrend(name="sine", amplitude=6, freq=3, phase=0, noise_level=1.5)
        ],
        aggregation_type=AggregationType.SUM,
    )


    d.add_metric(
        name="sinusoidal_linear",
        trends=[
            SinusoidalTrend(name="sine", amplitude=3, freq=5, phase=0, noise_level=1.5),
            LinearTrend(name="linear", slope=30, offset=10, noise_level=1),
        ],
        aggregation_type=AggregationType.SUM,
    )


    def my_custom_function():
        while True:
            val1 = random.randint(1, 2)
            val2 = random.randint(1, 3)
            # val3 = val1 + val2
            yield (val1, val2)


    d.add_multi_items(
        names="val1 val2".split(),
        function=my_custom_function(),
        aggregation_type=[AggregationType.SUM, AggregationType.AVG],
    )
    d.add_multi_items(
        names="val3 val4".split(),
        function=my_custom_function(),
        aggregation_type=[AggregationType.SUM, AggregationType.AVG],
    )
    return (d,)


@app.cell
def _(d):
    # get data for the first month
    first_month_data = d.data[(d.data.index.month == 1)]
    first_month_before_agg_val1 = first_month_data[
        (first_month_data["product"] == "A") & (first_month_data["interface"] == "X")
    ]["val1"].sum()
    first_month_before_agg_val2 = first_month_data[
        (first_month_data["product"] == "A") & (first_month_data["interface"] == "X")
    ]["val2"].mean()


    # Now aggregate the data to monthly granularity and check if the aggregated values match the expected values
    aggregated_data = d.aggregate(granularity="ME")

    first_month_after_agg_val1 = aggregated_data[
        (aggregated_data.index.month == 1)
        & (aggregated_data["product"] == "A")
        & (aggregated_data["interface"] == "X")
    ]["val1"].sum()
    first_month_after_agg_val2 = aggregated_data[
        (aggregated_data.index.month == 1)
        & (aggregated_data["product"] == "A")
        & (aggregated_data["interface"] == "X")
    ]["val2"].mean()
    return (
        first_month_after_agg_val1,
        first_month_after_agg_val2,
        first_month_before_agg_val1,
        first_month_before_agg_val2,
    )


@app.cell
def _(
    first_month_after_agg_val1,
    first_month_after_agg_val2,
    first_month_before_agg_val1,
    first_month_before_agg_val2,
):
    print(first_month_before_agg_val1 == first_month_after_agg_val1)  # expected to be True
    print(first_month_before_agg_val2 == first_month_after_agg_val2)  # expected to be True
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Aggregation with `expand_dimensions=True`

    When `expand_dimensions=True`, `DataGen.aggregate()` groups by all dimensional axes (including scalar dimensions and linked dimensions), and resamples each metric according to its configured `AggregationType`.
    """)
    return


@app.cell
def _(AggregationType, DataGen, LinearTrend):
    # Aggregation across expanded dimensional combinations. ``region`` is part
    # of the linked tuple so it travels with its city (London -> EU, New York
    # -> US) instead of being crossed as an independent Cartesian axis.
    d_exp = DataGen(
        start_datetime="2024-01-01 00:00:00",
        end_datetime="2024-01-03 23:00:00",
        granularity="h",
        seed=42,
        expand_dimensions=True,
    )

    # Two stores in New York (US), one in London (EU) — so rolling up
    # store_id while keeping city actually combines series (S1 + S2 -> NY).
    d_exp.add_multi_items(
        names=["store_id", "city", "region"],
        function=[
            ("S1", "New York", "US"),
            ("S2", "New York", "US"),
            ("S3", "London", "EU"),
        ],
        weights={
            ("S1", "New York", "US"): 10.0,
            ("S2", "New York", "US"): 5.0,
            ("S3", "London", "EU"): 0.5,
        }
    )

    d_exp.add_metric(
        "sales",
        {LinearTrend(offset=10, slope=0, noise_level=0)},
        aggregation_type=AggregationType.SUM,
    )

    # 72 hours x 3 store/city/region combos = 216 rows
    df_raw = d_exp.data
    print(f"Raw data shape: {df_raw.shape}")

    # Aggregate to daily ('D'), grouping by every dimension:
    # 3 days x 3 combos = 9 rows
    df_daily = d_exp.aggregate(granularity="D", by=["region"])
    print(f"Aggregated daily shape: {df_daily.shape}")
    df_daily
    return (d_exp,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Aggregating by a Subset of Dimensions

    With `expand_dimensions=True`, every dimensional combination carries its
    own series. Pass `by` to `aggregate()` to roll up across a **subset** of
    dimensions — only the columns named in `by` survive as groupby keys;
    every other dimension is aggregated away according to each metric's
    `AggregationType`. `by` lists individual column names, so the components
    of a linked dimension (`store_id`, `city`, `region`) can be kept or
    rolled up independently: here we keep `region` and `city`, summing
    `store_id` away. Each store's base daily total is `240`; the per-tuple
    `weights` scale that to `S1 = 2400` (x10), `S2 = 1200` (x5), and `S3 =
    120` (x0.5). Rolling up `store_id` then sums the scaled series:
    `(US, New York)` = `S1 + S2 = 3600`, while `(EU, London)` keeps only
    `S3 = 120`.
    """)
    return


@app.cell
def _(d_exp):
    # Roll up to daily, keeping only region + city (store_id aggregated away).
    # 3 days x 2 (region, city) combos = 6 rows; store_id no longer a column.
    df_daily_by_subset = d_exp.aggregate(granularity="D", by=["region", "city"])
    print(f"Aggregated daily (by region, city) shape: {df_daily_by_subset.shape}")
    print(df_daily_by_subset[["region", "city", "sales"]].head(6))

    # Roll up every dimension: by=[] yields a pure time-only resample.
    df_daily_time_only = d_exp.aggregate(granularity="D", by=[])
    print(f"\nAggregated daily (all dims rolled up) shape: {df_daily_time_only.shape}")
    print(df_daily_time_only[["sales"]])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Aggregation with Scaled Dimension Combinations

    When combinations carry different weights or scale variances, aggregation rolls up each scaled series per dimension combination appropriately.
    """)
    return


@app.cell
def _(AggregationType, DataGen, LinearTrend):
    # Scaling across expanded dimensions with AggregationType.SUM
    d_scaled_agg = DataGen(
        start_datetime="2024-01-01 00:00:00",
        end_datetime="2024-01-03 23:00:00",
        granularity="h",
        seed=42,
        expand_dimensions=True,
    )

    # Add dimension with explicit weights: US has 5x weight, EU has 2x weight
    d_scaled_agg.add_dimension("region", ["US", "EU"], weights={"US": 5.0, "EU": 2.0})
    d_scaled_agg.add_metric(
        "sales",
        {LinearTrend(offset=10, slope=0, noise_level=0)},
        aggregation_type=AggregationType.SUM,
    )

    df_daily_scaled = d_scaled_agg.aggregate(granularity="D")
    print("Daily aggregated sales by region (US should be 5x base, EU 2x base):")
    print(df_daily_scaled[["region", "sales"]])
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
