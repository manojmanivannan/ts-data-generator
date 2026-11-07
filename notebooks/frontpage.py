import marimo

__generated_with = "0.24.0"
app = marimo.App()


@app.cell
def _():
    from ts_data_generator import (
        DataGenerator,
        Granularity,
        LinearTrend,
        SinusoidalTrend,
        random_choice,
    )

    d = DataGenerator(
        start_datetime="2020-01-01",
        end_datetime="2020-01-03",
        granularity=Granularity.FIVE_MINUTE,
    )
    d.add_dimension("product", random_choice(["A", "B", "C","D"]))
    d.add_metric(
        "temperature",
        trends=[
            SinusoidalTrend("sine1", amplitude=40, freq=1, phase=0, noise_level=3),
            SinusoidalTrend("sine2", amplitude=40, freq=90, phase=0, noise_level=2),
        ]
    )
    d.add_metric(
        "humidity",
        trends=[
            SinusoidalTrend("sine3", amplitude=30, freq=1, phase=90, noise_level=2),
            LinearTrend("linear", slope=0.1, offset=5, noise_level=2),
        ]
    )
    d.plot(figsize=(12, 3))
    return


if __name__ == "__main__":
    app.run()
