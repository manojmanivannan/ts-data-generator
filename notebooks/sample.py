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
    <!-- html title in the middle -->
    <p style="text-align: center;">
        <h1 style="text-align: center;">Time Series Data Generator Library</h1>
        <h3 style="text-align: center;">A tool for generating synthetic time series data</h3>
    </p>
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Setting up the generator
    """)
    return


@app.cell
def _():
    # Import the Data generator class from the ts_data_generator module 
    from ts_data_generator import DataGen

    return (DataGen,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Instantiate the generator, then</br>set start and end datetime along with the granularity.
    """)
    return


@app.cell
def _(DataGen):
    d = DataGen()
    d.start_datetime = "2019-01-01"
    d.end_datetime = "2019-01-12"
    d.to_granularity("h")
    return (d,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Adding dimension
    Adding a dimension needs two parameter: a name(str) and a function.</br>
    The function parameter can take either integer, float, string or generator object as input.

    There are some useful generator objects like `random_choice` and `random_int` in the `ts_data_generator.utils.functions` module
    """)
    return


@app.cell
def _(d):
    from ts_data_generator.utils.functions import random_choice, random_int

    d.add_dimension("product", random_choice(["A", "B", "C", "D"]),expand=True)
    d.add_dimension("product_id", random_int(1,10000))
    d.add_dimension(name="interface", function="X Y Z".split(), expand=True)
    d.add_dimension(name="const",function=3)
    return random_choice, random_int


@app.cell
def _(d):
    d.data
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Adding Metrics

    Adding a metric needs two parameters: a name(str) and Trends.</br>
    Trends are components that can be layered to create complex metrics. They create trends to simulate any metrics.</br>
    You can club multiple trends to achieve your desired metric. Out of the box, there are four trends: Sine, Linear, Weekend, Stock
    """)
    return


@app.cell
def _(d):
    from ts_data_generator.utils.trends import SinusoidalTrend, LinearTrend, WeekendTrend, StockTrend


    d.add_metric(
        name="sinusoidal", 
        trends=[
            SinusoidalTrend(name="sine", amplitude=6, freq=3, phase=0, noise_level=1.5)
        ]
        )


    d.add_metric(
        name="sinusoidal_linear", 
        trends=[
            SinusoidalTrend(name="sine", amplitude=3, freq=5, phase=0, noise_level=1.5),
            LinearTrend(name="linear", slope=30, offset=10, noise_level=1)
        ])


    d.add_metric(
        name="weekend_trend", 
        trends=[
            WeekendTrend(name="weekend", weekend_effect=10, direction="up", noise_level=0.5, limit=10)
        ])


    d.add_metric(
        name="stock_like_trend", 
        trends=[
            StockTrend(name='stock', amplitude=10, direction='up', noise_level=0.5),
            LinearTrend(name='Linear', offset=0, noise_level=1, slope=10)
        ])
    return LinearTrend, SinusoidalTrend, WeekendTrend


@app.cell
def _(d):
    d
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Additional Trend Types

    Beyond the four basic trends, <code>ts_data_generator</code> includes:</br>

    <b>HolidayTrend</b> — ramps values up/down around holidays from the <code>holidays</code> library.<br/>
    <b>ARNoiseTrend</b> — autoregressive AR(p) noise with explicit coefficients or auto-generated decay.<br/>
    <b>MarkovTrend</b> — discrete-state Markov chain with configurable stickiness or explicit transition matrix.</cell id="cell-10">
    """)
    return


@app.cell
def _(d):
    # Additional trend types: HolidayTrend, ARNoiseTrend, MarkovTrend
    from ts_data_generator.utils.trends import HolidayTrend, ARNoiseTrend, MarkovTrend

    # Add more metrics with the new trend types
    d.add_metric(
        name="holiday_effect",
        trends=[
            HolidayTrend(name="hols", country="US", effect=30, pre_window=3, post_window=2, direction="up"),
        ],
    )

    d.add_metric(
        name="ar_noise",
        trends=[
            ARNoiseTrend(name="ar", coefficients=[0.5, -0.2], noise_std=0.5),
        ],
    )

    d.add_metric(
        name="markov_states",
        trends=[
            MarkovTrend(name="mkv", states=["low", "med", "high"], values=[10, 50, 100], stickiness=0.9, noise_std=5),
        ],
    )

    d.data.tail()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Adding Anomalies

    Anomalies inject realistic irregularities into metric values after trend composition.
    Types include <code>PointAnomaly</code> (isolated spikes), <code>MissingData</code> (NaN gaps), and <code>ConceptDrift</code> (gradual regime shifts).</br>
    MissingData supports three modes: <code>random</code>, <code>burst</code>, and <code>patterned</code>.</br>
    ConceptDrift uses <code>start_timestamp</code> for absolute segment positioning.</br>

    Anomalies compose with <code>+</code> and are applied in order (PointAnomaly → MissingData last).</cell id="cell-10">
    """)
    return


@app.cell
def _(DataGen, LinearTrend, WeekendTrend):
    # Anomaly injection examples
    from ts_data_generator.anomalies import PointAnomaly, MissingData, ConceptDrift, DriftSegment

    # Set up a fresh generator for anomaly demos
    d2 = DataGen(seed=42)
    d2.start_datetime = "2019-01-01"
    d2.end_datetime = "2019-01-12"
    d2.to_granularity("h")

    # Add a baseline metric with anomalies
    d2.add_metric(
        name="test_metric",
        trends=[
            LinearTrend(name="base", slope=5, offset=50, noise_level=2),
            WeekendTrend(name="wknd", weekend_effect=30, direction="up", noise_level=1),
        ],
        anomalies=[
            PointAnomaly(probability=0.02, magnitude=50),
            MissingData(probability=0.01),
            MissingData(mode="burst", burst_probability=0.005, min_length=2, max_length=3),
        ],
    )

    # ConceptDrift with start_index for sequential multi-segment positioning
    d2.add_metric(
        name="drift_metric",
        trends=[LinearTrend(name="base", slope=4, offset=20, noise_level=1)],
        anomalies=[
            ConceptDrift(segments=[
                DriftSegment(start_timestamp="2019-01-01T00:00:00", target_mean=80, target_std=5, hold_duration=86400, restore=True),
                DriftSegment(start_timestamp="2019-01-06T12:00:00", target_mean=90, target_std=10, hold_duration=86400, restore=True),
            ]),
        ],
    )

    d2.plot(figsize=(12,6), title="Metrics with Anomalies")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Plot the data
    Since the dataset in pandas, only numeric data is plotted.</br>
    You exclude or include columns with the arguments `exclude` and `include`
    """)
    return


@app.cell
def _(d):
    d.plot(exclude=['product_id'])
    return


@app.cell
def _(d):
    d.data.head()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Removing a metric or dimension
    You can remove a dimension or metric from the generator using the name
    """)
    return


@app.cell
def _(d):
    d.remove_dimension('product_id')
    d.remove_metric('sinusoidal')
    d.data.head()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Extending time range
    Changing the start or end datetime if automatically generate the data for all columns
    """)
    return


@app.cell
def _(d):
    d.end_datetime = '2019-01-12 02:05:00'
    d.data.tail()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Adding multi dimension/metric
    In case you want to add a dimensions or metrics that are linked
    """)
    return


@app.cell
def _(d):
    import random
    def my_custom_function():
        while True:
            val1 = random.randint(1,100)
            val2 =  random.randint(1,100)
            val3 = val1 + val2
            yield (val1, val2, val3)

    d.add_multi_items(names="val1 val2 val3".split(), function=my_custom_function(), aggregation_type="sum avg min".split())
    return (my_custom_function,)


@app.cell
def _(d):
    d.data.head()
    return


@app.cell
def _(d, my_custom_function):
    d.add_multi_items(names="val4 val5 val6".split(), function=my_custom_function())
    return


@app.cell
def _(d):
    d.data.head()
    return


@app.cell
def _(d):
    d.remove_multi_item(["val1"])
    d.data
    return


@app.cell
def _(d):
    d
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Multivariate Dimension Expansion (`expand_dimensions`)

    By default, `DataGen` generates one row per timestamp, advancing dimensions and metrics concurrently in a single stream.

    When `expand_dimensions=True`, the generator expands enumerable dimensions into their full **Cartesian product**. Each unique combination of dimensions gets an independently regenerated, reproducible metric series based on a deterministic per-combination seed.
    """)
    return


@app.cell
def _(DataGen, LinearTrend, SinusoidalTrend, random_choice):
    from ts_data_generator.utils.functions import ordered_choice
    d_exp = DataGen(start_datetime='2024-01-01', end_datetime='2024-01-03', granularity='h', seed=42, expand_dimensions=True)
    d_exp.add_dimension('region', random_choice(['US', 'EU']))
    d_exp.add_dimension('tier', ordered_choice(['free', 'premium']))
    # 1. Create DataGen with expand_dimensions=True
    d_exp.add_metric('revenue', {LinearTrend(offset=100, slope=5, noise_level=1), SinusoidalTrend(amplitude=15, freq=24, noise_level=0.5)})
    d_exp.add_multi_items(names=['datacenter', 'city'], function=[('DC-1', 'New York'), ('DC-2', 'London')])
    df_expanded = d_exp.data
    print(f'Total rows: {len(df_expanded)} (49 timestamps × 2 regions × 2 tiers × 2 datacenters = {49 * 2 * 2 * 2})')
    # Add enumerable dimensions
    # Add metric with composed trends
    # Add linked dimensions via MultiItems (expands as tuple domain)
    df_expanded.head(10)
    return (d_exp,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Per-Dimension Expansion Override (`expand=False`)

    You can also opt individual dimensions out of the Cartesian product expansion by passing `expand=False`. Non-expanding dimensions will regenerate within each combination series rather than multiplying the row count.
    """)
    return


@app.cell
def _(d_exp, random_int):
    # Add non-expanding dimension that regenerates within each series
    d_exp.add_dimension("request_id", random_int(1000, 9999), expand=False)
    df_mixed = d_exp.data
    print(f"Total rows remain: {len(df_mixed)}")
    df_mixed.head(10)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Multi-Series Metric Scaling (`weights` & `scale_variance`)

    When expanding dimensions, different dimension combinations often represent entities with fundamentally different base volume or magnitude (e.g. *enterprise* vs *free*, *US* vs *EU*).

    `ts-data-generator` allows you to scale metric baselines across dimension slices using:
    1. **Explicit Weights**: Passing a dict `{value: weight}` or `weights={...}` directly to `add_dimension` / `add_multi_items`.
    2. **Stochastic Variance (`scale_variance`)**: Drawing log-normal scale factors deterministically per slice.
    """)
    return


@app.cell
def _(DataGen, LinearTrend, SinusoidalTrend):
    # Create DataGen with dimension scaling
    d_scaled = DataGen(
        start_datetime="2024-01-01",
        end_datetime="2024-01-03",
        granularity="h",
        seed=42,
        expand_dimensions=True,
        scale_variance=0.2,  # auto stochastic log-normal variance across slices
    )

    # 1. Explicit weights via dictionary or weights parameter
    d_scaled.add_dimension("tier", {"enterprise": 10.0, "pro": 3.0, "free": 1.0})
    d_scaled.add_dimension("region", ["US", "EU"], weights={"US": 5.0, "EU": 2.0})

    # 2. Composed metric
    d_scaled.add_metric(
        "revenue",
        {LinearTrend(offset=100, slope=2, noise_level=1), SinusoidalTrend(amplitude=15, freq=24)},
    )

    df_scaled = d_scaled.data
    # Group by dimension combination to inspect the different magnitudes
    print("Average revenue by tier and region:")
    print(df_scaled.groupby(["tier", "region"])["revenue"].mean().round(2))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Aggregate data

    You can also perform basic data aggregation.

    Checkout this notebook: [Aggregate](https://github.com/manojmanivannan/ts-data-generator/blob/main/notebooks/aggregate.py)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
 
    """)
    return


if __name__ == "__main__":
    app.run()
