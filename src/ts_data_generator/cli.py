# import click
# from ts_data_generator import DataGen
# from ts_data_generator.schema.models import Granularity
# import ts_data_generator.utils.functions as util_functions
# import importlib
# from ts_data_generator.utils.trends import (
#     SinusoidalTrend,
#     LinearTrend,
#     WeekendTrend,
#     StockTrend,
# )
# import re

# # tsgen --start "2019-01-01" --end "2019-01-12" --granularity "FIVE_MIN" --dimensions "product:random_choice:A,B,C,D;product_id:random_int:1,10000" --metrics "sales:LinearTrend(limit=500)+WeekendTrend(weekend_effect=50)" --output "data.csv"

# @click.command()
# @click.option('--start', required=True, type=str, help="Start datetime (e.g., '2019-01-01').")
# @click.option('--end', required=True, type=str, help="End datetime (e.g., '2019-01-12').")
# @click.option('--granularity', required=True, type=click.Choice(['FIVE_MIN', 'HOURLY', 'DAILY'], case_sensitive=False), help="Granularity of the time series data.")
# @click.option('--dimensions', required=True, type=str, help="Semicolon-separated list of dimensions of the format 'name:function:values' (e.g., 'product:random_choice:A,B,C,D;product_id:random_int:1,10000').")
# @click.option('--metrics', required=True, type=str, help="Semicolon-separated list of metrics with trends (e.g., 'sales:LinearTrend(limit=500)+WeekendTrend(weekend_effect=50)').")
# @click.option('--output', required=True, type=str, help="Output file path (e.g., 'data.csv').")
# def main(start, end, granularity, dimensions, metrics, output):
#     """
#     Generate time series data using ts_data_generator library.
#     """
#     # Initialize the data generator
#     data_gen = DataGen()
#     data_gen.start_datetime = start
#     data_gen.end_datetime = end
#     data_gen.granularity = Granularity[granularity.upper()]

#     # Add dimensions
#     for dimension in dimensions.split(';'):
#         name, dtype, values = dimension.split(':', 2)
#         dtype_function = getattr(util_functions, dtype)
#         if all([v.isdigit() for v in values.split(',')]):
#             values = map(int, values.split(','))
#         else:
#             values = values.split(',')

#         try:
#             data_gen.add_dimension(name, dtype_function(values))
#         except TypeError as e:
#             if 'random_int' in str(e):
#                 data_gen.add_dimension(name, dtype_function(*values))


#     # Add metrics with trends
#     for metric in metrics.split(';'):
#         # print('metric', metric) # sales:LinearTrend(limit=500)+WeekendTrend(weekend_effect=50)
#         name, *trend_defs = metric.split(':')
#         trends = []
#         for trend_def in trend_defs[0].split('+'):
#             # Extract trend name and parameters using a regex
#             match = re.match(r"(\w+)\((.*?)\)", trend_def)
#             if not match:
#                 raise ValueError(f"Invalid trend definition: {trend_def}")

#             trend_name = match.group(1)  # Extract trend name
#             params_str = match.group(2)  # Extract parameters inside parentheses

#             # Parse parameters into a dictionary
#             param_dict = {}
#             if params_str:  # Ensure there are parameters to parse
#                 for param in params_str.split(','):
#                     key, value = param.split('=')
#                     try:
#                         # Convert values to int, float, or leave as string
#                         value = int(value) if value.isdigit() else float(value) if '.' in value else value
#                     except ValueError:
#                         pass
#                     param_dict[key] = value


#             if trend_name == 'SinusoidalTrend':
#                 trends.append(SinusoidalTrend(**param_dict))
#             elif trend_name == 'LinearTrend':
#                 trends.append(LinearTrend(**param_dict))
#             elif trend_name == 'WeekendTrend':
#                 trends.append(WeekendTrend(**param_dict))
#             elif trend_name == 'StockTrend':
#                 trends.append(StockTrend(**param_dict))
#             else:
#                 raise ValueError(f"Unsupported trend type: {trend_name}")
#         data_gen.add_metric(name=name, trends=trends)

#     # Generate and save data
#     data = data_gen.data
#     if output.endswith('.csv'):
#         data.to_csv(output, index=True)
#     else:
#         raise ValueError("Output file must be .csv")

#     click.echo(f"Data successfully generated and saved to {output}")


# if __name__ == '__main__':
#     main()

import inspect, sys
import click
from ts_data_generator import DataGen
from ts_data_generator.schema.models import Granularity
import ts_data_generator.utils.functions as util_functions
import importlib
import ts_data_generator.utils.trends as trends_functions
import re


@click.group()
def main():
    """CLI tool for generating time series data."""


@main.command()
@click.option(
    "--start", required=True, type=str, help="Start datetime (e.g., '2019-01-01')."
)
@click.option(
    "--end", required=True, type=str, help="End datetime (e.g., '2019-01-12')."
)
@click.option(
    "--granularity",
    required=True,
    type=click.Choice(["FIVE_MIN", "HOURLY", "DAILY"], case_sensitive=False),
    help="Granularity of the time series data.",
)
@click.option(
    "--dims",
    required=True,
    type=str,
    help="Semicolon-separated list of dimensions of the format 'name:function:values' (e.g., 'product:random_choice:A,B,C,D;product_id:random_int:1,10000').",
)
@click.option(
    "--mets",
    required=True,
    type=str,
    help="Semicolon-separated list of metrics with trends (e.g., 'sales:LinearTrend(limit=500)+WeekendTrend(weekend_effect=50)').",
)
@click.option(
    "--output", required=True, type=str, help="Output file path (e.g., 'data.csv')."
)
def generate(start, end, granularity, dims, mets, output):
    """
    Generate time series data and save it to a CSV file.
    """
    from click.core import Context

    # Initialize the data generator
    data_gen = DataGen()
    data_gen.start_datetime = start
    data_gen.end_datetime = end
    data_gen.granularity = Granularity[granularity.upper()]

    # Add dimensions
    for dimension in dims.split(";"):
        name, dtype, values = dimension.split(":", 2)
        try:
            dtype_function = getattr(util_functions, dtype)
        except AttributeError as e:
            click.echo(f"Error: Invalid dimension function type '{dtype}'.\n")
            dimensions.callback()
            sys.exit(1)

        if all([v.isdigit() for v in values.split(",")]):
            values = tuple(map(int, values.split(",")))
        else:
            values = values.split(",")

        try:
            data_gen.add_dimension(name, dtype_function(values))
        except TypeError as e:
            try:
                data_gen.add_dimension(name, dtype_function(*values))
            except TypeError as e:
                click.echo(
                    f"Error: Invalid dimension parameters '{values}' for {dtype}.\n"
                )
                dimensions.callback()
                sys.exit(1)
            except Exception as e:
                click.UsageError(
                    f"Error creating dimension: {e}\ for dimension type: {dtype}\n"
                )
                dimensions.callback()
                sys.exit(1)

    # Add metrics with trends
    for metric in mets.split(";"):
        name, *trend_defs = metric.split(":")
        trends = []
        for trend_def in trend_defs[0].split("+"):
            match = re.match(r"(\w+)\((.*?)\)", trend_def)
            if not match:
                raise ValueError(f"Invalid trend definition: {trend_def}")

            trend_name = match.group(1)
            params_str = match.group(2)

            param_dict = {}
            if params_str:
                for param in params_str.split(","):
                    key, value = param.split("=")
                    value = (
                        int(value)
                        if value.isdigit()
                        else float(value) if "." in value else value
                    )
                    param_dict[key] = value

            try:
                trend_function = getattr(trends_functions, trend_name)

            except AttributeError as e:
                click.echo(f"Error: Invalid trend type '{trend_name}'.\n")
                metrics.callback()
                sys.exit(1)

            try:
                trends.append(trend_function(**param_dict))

            except TypeError as e:
                click.echo(
                    f"Error: Invalid parameter '"
                    + re.search(
                        r"got an unexpected keyword argument '(\w+)'", str(e)
                    ).group(1)
                    + f"' for trend '{trend_name}'.\n"
                )
                metrics.callback()
                sys.exit(1)

        data_gen.add_metric(name=name, trends=trends)

    # Generate and save data
    data = data_gen.data
    if output.endswith(".csv"):
        data.to_csv(output, index=True)
    else:
        raise ValueError("Output file must be .csv")

    click.echo(f"Data successfully generated and saved to {output}")


@main.command()
def dimensions():
    """
    List all available dimension functions in ts_data_generator.utils.functions.
    """
    functions = [
        f
        for f in dir(util_functions)
        if callable(getattr(util_functions, f)) and not f.startswith("_")
    ]
    click.echo("Available dimension functions are:")
    for func in functions:
        # Get the function object
        func_obj = getattr(util_functions, func)
        # Get the function signature
        signature = inspect.signature(func_obj)
        # Print the function name and its arguments
        click.echo(f"- {func}{signature}")


@main.command()
def metrics():
    """
    List all available metric trends in ts_data_generator.utils.trends.
    """
    functions = [
        f
        for f in dir(trends_functions)
        if callable(getattr(trends_functions, f))
        and not f.startswith("_")
        and "Trend" in f
        and not f.startswith("Trends")
    ]
    click.echo("Available metric trends & parameters are:")
    for func in functions:
        # Get the function object
        func_obj = getattr(trends_functions, func)
        # Get the function signature
        signature = inspect.signature(func_obj)
        # Print the function name and its arguments
        click.echo(f"- {func}{signature}")


if __name__ == "__main__":
    main()
