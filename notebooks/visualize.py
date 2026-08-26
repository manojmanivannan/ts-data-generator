import marimo

__generated_with = "0.24.0"
app = marimo.App()


@app.cell
def _():
    import subprocess

    return (subprocess,)


@app.cell
def _(subprocess):
    #!tsdata generate --config sample_config.json
    subprocess.call(['tsdata', 'generate', '--config', 'sample_config.json'])
    return


@app.cell
def _():
    import pandas as pd
    import matplotlib.pyplot as plt

    # Load the data
    df = pd.read_csv("output.csv", parse_dates=["datetime"])
    print(df.head())
    return df, plt


@app.cell
def _(df, plt):
    # Create a plot/
    fig, ax = plt.subplots(figsize=(10, 6))

    plottable_columns = [s for s in df.columns if s not in ["datetime", "epoch","product","region","tier","score","weight","item_id"]]
    # Plot each plottable column
    for col in plottable_columns:
        ax.plot(df["datetime"], df[col], label=col)

    # Customize the plot

    ax.set_xlabel("Datetime")
    ax.set_ylabel("Metric Value")
    ax.legend()
    plt.tight_layout()
    return


if __name__ == "__main__":
    app.run()
