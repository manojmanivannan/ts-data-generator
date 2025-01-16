import click
from ts_data_generator import DataGen
from ts_data_generator.schema.models import Granularity
from ts_data_generator.utils.functions import random_choice, random_int
from ts_data_generator.utils.trends import (
    SinusoidalTrend,
    LinearTrend,
    WeekendTrend,
    StockTrend,
)
import re

# tsgen --start "2019-01-01" --end "2019-01-12" --granularity "FIVE_MIN" --dimensions "product:random_choice:A,B,C,D;product_id:random_int:1,10000" --metrics "sales:LinearTrend(limit=500)+WeekendTrend(weekend_effect=50)" --output "data.csv"

@click.command()
@click.option('--start', required=True, type=str, help="Start datetime (e.g., '2019-01-01').")
@click.option('--end', required=True, type=str, help="End datetime (e.g., '2019-01-12').")
@click.option('--granularity', required=True, type=click.Choice(['FIVE_MIN', 'HOURLY', 'DAILY'], case_sensitive=False), help="Granularity of the time series data.")
@click.option('--dimensions', required=True, type=str, help="Semicolon-separated list of dimensions (e.g., 'product:random_choice:A,B,C,D;product_id:random_int:1,10000').")
@click.option('--metrics', required=True, type=str, help="Semicolon-separated list of metrics with trends (e.g., 'sales:LinearTrend(limit=500)+WeekendTrend(weekend_effect=50)').")
@click.option('--output', required=True, type=str, help="Output file path (e.g., 'data.csv').")
def main(start, end, granularity, dimensions, metrics, output):
    """
    Generate time series data using ts_data_generator library.
    """
    # Initialize the data generator
    data_gen = DataGen()
    data_gen.start_datetime = start
    data_gen.end_datetime = end
    data_gen.granularity = Granularity[granularity.upper()]

    # Add dimensions
    for dimension in dimensions.split(';'):
        name, dtype, values = dimension.split(':', 2)
        if dtype == 'random_choice':
            values = values.split(',')
            data_gen.add_dimension(name, random_choice(values))
        elif dtype == 'random_int':
            min_val, max_val = map(int, values.split(','))
            data_gen.add_dimension(name, random_int(min_val, max_val))
        else:
            raise ValueError(f"Unsupported dimension type: {dtype}")

    # Add metrics with trends
    for metric in metrics.split(';'):
        # print('metric', metric) # sales:LinearTrend(limit=500)+WeekendTrend(weekend_effect=50)
        name, *trend_defs = metric.split(':')
        trends = []
        for trend_def in trend_defs[0].split('+'):
            # Extract trend name and parameters using a regex
            match = re.match(r"(\w+)\((.*?)\)", trend_def)
            if not match:
                raise ValueError(f"Invalid trend definition: {trend_def}")

            trend_name = match.group(1)  # Extract trend name
            params_str = match.group(2)  # Extract parameters inside parentheses

            # Parse parameters into a dictionary
            param_dict = {}
            if params_str:  # Ensure there are parameters to parse
                for param in params_str.split(','):
                    key, value = param.split('=')
                    try:
                        # Convert values to int, float, or leave as string
                        value = int(value) if value.isdigit() else float(value) if '.' in value else value
                    except ValueError:
                        pass
                    param_dict[key] = value


            if trend_name == 'SinusoidalTrend':
                trends.append(SinusoidalTrend(**param_dict))
            elif trend_name == 'LinearTrend':
                trends.append(LinearTrend(**param_dict))
            elif trend_name == 'WeekendTrend':
                trends.append(WeekendTrend(**param_dict))
            elif trend_name == 'StockTrend':
                trends.append(StockTrend(**param_dict))
            else:
                raise ValueError(f"Unsupported trend type: {trend_name}")
        data_gen.add_metric(name=name, trends=trends)

    # Generate and save data
    data = data_gen.data
    if output.endswith('.csv'):
        data.to_csv(output, index=True)
    else:
        raise ValueError("Output file must be .csv")

    click.echo(f"Data successfully generated and saved to {output}")


if __name__ == '__main__':
    main()
