import inspect, sys, click, importlib, re
from ts_data_generator import DataGen
from ts_data_generator.schema.models import Granularity
import ts_data_generator.utils.functions as util_functions
import ts_data_generator.utils.trends as trends_functions


@click.group(context_settings={"max_content_width": 220})
def main():
    """CLI tool for generating time series data."""


@main.command()
@click.option(
    "--start", required=True, type=str, help="Start datetime (e.g., '2019-01-01')"
)
@click.option(
    "--end", required=True, type=str, help="End datetime (e.g., '2019-01-12')"
)
@click.option(
    "--granularity",
    required=True,
    type=click.Choice(["FIVE_MIN", "HOURLY", "DAILY"], case_sensitive=False),
    help="Granularity of the time series data",
)
@click.option(
    "--dims",
    required=True,
    type=str,
    help="+ separated list of dimensions definition of format 'name:function:values'",
    multiple=True,
)
@click.option(
    "--mets",
    required=True,
    type=str,
    help="+ separated list of metrics definition trends of format 'name:trend(*params)'",
    multiple=True,
)
@click.option(
    "--output", required=True, type=str, help="Output file name"
)
def generate(start, end, granularity, dims, mets, output):
    """
    Generate time series data and save it to a CSV file.
    """
    mets = ";".join(mets)
    dims = ";".join(dims)
    
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
