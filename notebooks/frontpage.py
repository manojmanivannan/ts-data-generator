import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Mega Signal – layered composite time series

    ```python
    # Mega-signal metric: 16 stacked trends on a fresh generator
    d_mega = DataGen(
        start_datetime="2024-01-01", end_datetime="2024-01-10", granularity="5min", seed=7
    )

    d_mega.add_metric(
        name="mega_signal",
        trends=[
            LinearTrend(offset=60, slope=0, noise_level=0.3),
            SinusoidalTrend(amplitude=22, freq=30, phase=0, noise_level=0.2),
            SinusoidalTrend(amplitude=18, freq=14, phase=4, noise_level=0.2),
            SinusoidalTrend(amplitude=15, freq=7, phase=2, noise_level=0.2),
            SinusoidalTrend(amplitude=12, freq=3.5, phase=6, noise_level=0.2),
            SinusoidalTrend(amplitude=10, freq=1.75, phase=1, noise_level=0.2),
            SinusoidalTrend(amplitude=8, freq=1, phase=6, noise_level=0.2),
            SinusoidalTrend(amplitude=6, freq=0.5, phase=3, noise_level=0.2),
            SinusoidalTrend(amplitude=5, freq=0.25, phase=0, noise_level=0.15),
            SinusoidalTrend(amplitude=4, freq=0.125, phase=9, noise_level=0.15),
            SinusoidalTrend(amplitude=3, freq=0.0625, phase=5, noise_level=0.1),
            SinusoidalTrend(amplitude=2, freq=0.05, phase=12, noise_level=0.1),
            WeekendTrend(weekend_effect=10, direction="down", noise_level=1.0, limit=12),
            MarkovTrend(
                states=["low", "mid", "high"], values=[-8, 0, 8], stickiness=0.95, noise_std=1.5
            ),
            ARNoiseTrend(decay=0.55, noise_std=1.8),
            StockTrend(amplitude=1.5, direction="up", noise_level=0.3),
        ],
        anomalies=[
            PointAnomaly(probability=0.006, magnitude=4, mode="additive"),
            PointAnomaly(probability=0.003, magnitude=-4, mode="additive"),
            MissingData(mode="burst", burst_probability=0.004, min_length=2, max_length=4),
            ConceptDrift(
                segments=[
                    DriftSegment(
                        start_timestamp="2024-01-08T12:00:00",
                        transition_window=3600,
                        target_mean=60,
                        target_std=6,
                        hold_duration=5400,
                        restore=True,
                    )
                ]
            ),
            PeriodicBurstAnomaly(
                period=200, duration=6, peak_magnitude=3, decay=0.3, tail_length=4, mode="additive"
            ),
        ],
    )
    ```
    """)
    return


@app.cell
def _():
    from ts_data_generator import (
        ARNoiseTrend,
        ConceptDrift,
        DataGen,
        DriftSegment,
        LinearTrend,
        MarkovTrend,
        MissingData,
        PointAnomaly,
        SinusoidalTrend,
        StockTrend,
        WeekendTrend,
    )
    from ts_data_generator.anomalies import PeriodicBurstAnomaly

    return (
        ARNoiseTrend,
        ConceptDrift,
        DataGen,
        DriftSegment,
        LinearTrend,
        MarkovTrend,
        MissingData,
        PeriodicBurstAnomaly,
        PointAnomaly,
        SinusoidalTrend,
        StockTrend,
        WeekendTrend,
    )


@app.cell
def _(
    ARNoiseTrend,
    ConceptDrift,
    DataGen,
    DriftSegment,
    LinearTrend,
    MarkovTrend,
    MissingData,
    PeriodicBurstAnomaly,
    PointAnomaly,
    SinusoidalTrend,
    StockTrend,
    WeekendTrend,
):
    # Mega-signal metric: 16 stacked trends on a fresh generator
    d_mega = DataGen(
        start_datetime="2024-01-01", end_datetime="2024-01-10", granularity="5min", seed=7
    )

    d_mega.add_metric(
        name="mega_signal",
        trends=[
            LinearTrend(offset=60, slope=0, noise_level=0.3),
            SinusoidalTrend(amplitude=22, freq=30, phase=0, noise_level=0.2),
            SinusoidalTrend(amplitude=18, freq=14, phase=4, noise_level=0.2),
            SinusoidalTrend(amplitude=15, freq=7, phase=2, noise_level=0.2),
            SinusoidalTrend(amplitude=12, freq=3.5, phase=6, noise_level=0.2),
            SinusoidalTrend(amplitude=10, freq=1.75, phase=1, noise_level=0.2),
            SinusoidalTrend(amplitude=8, freq=1, phase=6, noise_level=0.2),
            SinusoidalTrend(amplitude=6, freq=0.5, phase=3, noise_level=0.2),
            SinusoidalTrend(amplitude=5, freq=0.25, phase=0, noise_level=0.15),
            SinusoidalTrend(amplitude=4, freq=0.125, phase=9, noise_level=0.15),
            SinusoidalTrend(amplitude=3, freq=0.0625, phase=5, noise_level=0.1),
            SinusoidalTrend(amplitude=2, freq=0.05, phase=12, noise_level=0.1),
            WeekendTrend(weekend_effect=10, direction="down", noise_level=1.0, limit=12),
            MarkovTrend(
                states=["low", "mid", "high"], values=[-8, 0, 8], stickiness=0.95, noise_std=1.5
            ),
            ARNoiseTrend(decay=0.55, noise_std=1.8),
            StockTrend(amplitude=1.5, direction="up", noise_level=0.3),
        ],
        anomalies=[
            PointAnomaly(probability=0.006, magnitude=4, mode="additive"),
            PointAnomaly(probability=0.003, magnitude=-4, mode="additive"),
            MissingData(mode="burst", burst_probability=0.004, min_length=2, max_length=4),
            ConceptDrift(
                segments=[
                    DriftSegment(
                        start_timestamp="2024-01-08T12:00:00",
                        transition_window=3600,
                        target_mean=60,
                        target_std=6,
                        hold_duration=5400,
                        restore=True,
                    )
                ]
            ),
            PeriodicBurstAnomaly(
                period=200, duration=6, peak_magnitude=3, decay=0.3, tail_length=4, mode="additive"
            ),
        ],
    )
    return (d_mega,)


@app.cell
def _(d_mega, mo):
    title = (
        "mega_signal — 16 layered trends with point anomalies, "
        "burst gaps, timed drift & periodic bursts"
    )
    mo.hstack([
        mo.ui.matplotlib(d_mega.plot(figsize=(20, 9), title=title)),
        mo.md("""
    | Category | Description / Metrics |
    | --- | --- |
    | Base Trend | A flat linear base |
    | Sinusoidal Trend | 11 sine in a freq cascade (frequency 30 → 0.05) |
    | WeekendTrend | downward WeekendTrend |
    | MarkovTrend | sticky 3-state MarkovTrend regime (-8 / 0 / +8) |
    | ARNoiseTrend | Autoregressive ARNoiseTrend (decay 0.55) |
    | StockTrend | A gentle upward StockTrend |
    | PointAnomaly | Additive spikes (+4 / -4) |
    | MissingData | Burst-mode MissingData gaps |
    | ConceptDrift | at 2024-01-08 12:00 (Δ60 for 1.5 hours, then restored) |
    | PeriodicBurstAnomaly | A recurring PeriodicBurstAnomaly |
        """)])
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
