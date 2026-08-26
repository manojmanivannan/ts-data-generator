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
    # Use SchemaConverter to Impute the trends from CSV
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    > Note: Depends on scipy which is not part of this library
    """)
    return


@app.cell
def _():
    # Import the Data generator class from the ts_data_generator module 
    from ts_data_generator import DataGen
    from ts_data_generator.schema.models import Granularity
    from ts_data_generator.analyzers.converter import SchemaConverter
    # '%matplotlib inline' command supported automatically in marimo
    return (SchemaConverter,)


@app.cell
def _(SchemaConverter):
    s = SchemaConverter(csv_file_path='../etc/data/sample.csv',index_col=0)
    s.data
    return (s,)


@app.cell
def _(s):
    trend_info = s.analyze_numeric_trends(columns=['sales'],top_freq=2)
    trend_info
    return (trend_info,)


@app.cell
def _(s, trend_info):
    s.construct_trend_column('sales', trend_info['sales'])
    return


@app.cell
def _(s):
    df = s.data[['sales','sales_constructed']]
    normalized_df = (df-df.min())/(df.max()-df.min())
    return (normalized_df,)


@app.cell
def _(normalized_df):
    normalized_df.plot()
    return


if __name__ == "__main__":
    app.run()
