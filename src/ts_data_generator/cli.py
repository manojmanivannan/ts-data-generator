"""
CLI module for ts-data-generator.
Provides command-line interface for generating synthetic time series data.
"""

import inspect
import json
import os
import re
from pathlib import Path
from typing import List, Optional

import click
from pydantic import BaseModel, Field, field_validator

from ts_data_generator import DataGen


# Environment variable prefix for configuration
ENV_PREFIX = "TSDATA_"


def _load_env_defaults() -> dict:
    """Load default values from environment variables."""
    defaults = {}
    prefix = ENV_PREFIX

    for key, value in os.environ.items():
        if key.startswith(prefix):
            config_key = key[len(prefix) :].lower()
            defaults[config_key] = value

    return defaults


from ts_data_generator.schema.models import Granularity
from ts_data_generator.utils import functions as dimension_functions
from ts_data_generator.utils import trends as trend_functions


# Pydantic models for config validation
class DimensionSpec(BaseModel):
    """A dimension specification in config."""

    name: str = Field(..., description="Dimension name")
    function: str = Field(
        default="random_choice", description="Dimension function name"
    )
    values: List[str] = Field(..., description="Dimension values")


class MetricSpec(BaseModel):
    """A metric specification in config."""

    name: str = Field(..., description="Metric name")
    trends: str = Field(..., description="Trend specifications (comma-separated)")


class GeneratorConfig(BaseModel):
    """Configuration for data generation."""

    start: str = Field(..., description="Start datetime (YYYY-MM-DD)")
    end: str = Field(..., description="End datetime (YYYY-MM-DD)")
    granularity: str = Field(..., description="Data granularity")
    dimensions: List[str] = Field(default_factory=list, description="Dimension specs")
    metrics: List[str] = Field(default_factory=list, description="Metric specs")
    output: str = Field(..., description="Output CSV file path")

    @field_validator("granularity")
    @classmethod
    def validate_granularity(cls, v: str) -> str:
        valid = [g.value for g in Granularity]
        if v.lower() not in valid:
            raise ValueError(f"Invalid granularity '{v}'. Valid: {', '.join(valid)}")
        return v.lower()


# Preset configurations
PRESETS: dict = {
    "daily-sales": {
        "start": "2024-01-01",
        "end": "2024-01-31",
        "granularity": "D",
        "dimensions": ["product:A,B,C,D", "region:X,Y,Z"],
        "metrics": ["sales:LinearTrend(limit=1000)+WeekendTrend(weekend_effect=100)"],
        "output": "daily_sales.csv",
    },
    "hourly-metrics": {
        "start": "2024-01-01",
        "end": "2024-01-02",
        "granularity": "h",
        "dimensions": ["sensor:random_choice:S1,S2,S3"],
        "metrics": [
            "temperature:LinearTrend(limit=50)",
            "humidity:SinusoidalTrend(amplitude=20,freq=24)",
        ],
        "output": "hourly_metrics.csv",
    },
    "minute-stock": {
        "start": "2024-01-01",
        "end": "2024-01-02",
        "granularity": "5min",
        "dimensions": ["symbol:random_choice:API,GOOG,MSFT"],
        "metrics": ["price:StockTrend(amplitude=5,direction=up,noise_level=0.01)"],
        "output": "minute_stock.csv",
    },
    "weekly-revenue": {
        "start": "2024-01-01",
        "end": "2024-12-31",
        "granularity": "D",
        "dimensions": ["quarter:Q1,Q2,Q3,Q4", "region:North,South,East,West"],
        "metrics": ["revenue:LinearTrend(limit=100)+WeekendTrend(weekend_effect=50)"],
        "output": "weekly_revenue.csv",
    },
    "monthly-recurring": {
        "start": "2024-01-01",
        "end": "2024-12-31",
        "granularity": "D",
        "dimensions": ["plan:Basic,Pro,Enterprise"],
        "metrics": ["mrr:LinearTrend(limit=100)"],
        "output": "monthly_mrr.csv",
    },
}


# Constants
DIM_SEPARATOR = ";"
TREND_SEPARATOR = "+"
VALUE_SEPARATOR = ","
DEFAULT_DIMENSION_FUNCTION = "random_choice"


def _parse_value(value: str) -> int | float | str:
    """Parse a value string into appropriate Python type."""
    if value.isdigit():
        return int(value)
    if "." in value:
        try:
            return float(value)
        except ValueError:
            return value
    return value


def _parse_dimension_spec(spec: str) -> tuple[str, str, tuple | list]:
    """
    Parse dimension specification.

    Formats:
    - name:function:values (e.g., "product:random_choice:A,B,C")
    - name:values (e.g., "product:A,B,C" -> defaults to random_choice)

    Returns:
        tuple: (name, function_name, values)
    """
    parts = spec.split(":", 2)

    if len(parts) == 2:
        # Shorthand: name:values -> defaults to random_choice
        name, values = parts
        function_name = DEFAULT_DIMENSION_FUNCTION
    else:
        name, function_name, values = parts

    # Parse values - convert to tuple of ints/floats if all values are numeric
    value_list = values.split(VALUE_SEPARATOR)
    if all(v.lstrip("-").replace(".", "", 1).isdigit() for v in value_list if v):
        # All are numeric - convert to int or float
        parsed_values = tuple(
            (
                int(v)
                if v.isdigit() or (v.startswith("-") and v[1:].isdigit())
                else float(v)
            )
            for v in value_list
        )
    else:
        parsed_values = value_list

    return name, function_name, parsed_values


def _parse_trend_spec(trend_spec: str) -> tuple[str, dict[str, int | float | str]]:
    """
    Parse trend specification.

    Format: TrendName(param1=value1,param2=value2)

    Returns:
        tuple: (trend_name, param_dict)
    """
    match = re.match(r"(\w+)\((.*?)\)", trend_spec)
    if not match:
        raise click.BadParameter(
            f"Invalid trend format '{trend_spec}'. Expected: TrendName(param=value)"
        )

    trend_name = match.group(1)
    params_str = match.group(2)

    param_dict = {}
    if params_str:
        for param in params_str.split(VALUE_SEPARATOR):
            key, value = param.split("=")
            param_dict[key] = _parse_value(value)

    return trend_name, param_dict


def _get_dimension_function(function_name: str) -> callable:
    """Get dimension function by name, raising a proper click error if not found."""
    try:
        return getattr(dimension_functions, function_name)
    except AttributeError:
        available = [
            f
            for f in dir(dimension_functions)
            if callable(getattr(dimension_functions, f)) and not f.startswith("_")
        ]
        raise click.BadParameter(
            f"Unknown dimension function '{function_name}'. "
            f"Available: {', '.join(available)}"
        )


def _get_trend_function(function_name: str) -> callable:
    """Get trend function by name, raising a proper click error if not found."""
    try:
        return getattr(trend_functions, function_name)
    except AttributeError:
        available = [
            f
            for f in dir(trend_functions)
            if callable(getattr(trend_functions, f)) and "Trend" in f
        ]
        raise click.BadParameter(
            f"Unknown trend function '{function_name}'. "
            f"Available: {', '.join(available)}"
        )


def _load_config(config_path: Path) -> dict:
    """Load and validate JSON configuration file with pydantic."""
    try:
        with open(config_path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise click.BadParameter(f"Invalid JSON in config file: {e}")

    # Validate with pydantic
    try:
        validated = GeneratorConfig(**config)
        return validated.model_dump()
    except Exception as e:
        raise click.BadParameter(f"Invalid config: {e}")


def _apply_config_overrides(config: dict, **cli_kwargs: str | None) -> dict:
    """Apply CLI arguments as overrides to config values."""
    result = config.copy()

    # Only override if CLI provides a value (not None)
    for key in ["start", "end", "granularity", "output"]:
        if cli_kwargs.get(key):
            result[key] = cli_kwargs[key]

    return result


@click.group(context_settings={"max_content_width": 220})
def main():
    """CLI tool for generating time series data."""


@main.command()
@click.option("--start", "start", type=str, help="Start datetime (YYYY-MM-DD)")
@click.option("--end", "end", type=str, help="End datetime (YYYY-MM-DD)")
@click.option(
    "--granularity",
    type=click.Choice([g.value for g in Granularity], case_sensitive=False),
    help="Data granularity",
)
@click.option(
    "--dims",
    type=str,
    multiple=True,
    help=f"Dimension specs (sep by {DIM_SEPARATOR}). Formats: 'name:function:values' or 'name:values'",
)
@click.option(
    "--mets",
    type=str,
    multiple=True,
    help=f"Metric specs (sep by {DIM_SEPARATOR}). Format: 'name:Trend(param=value)+Trend2'",
)
@click.option("--output", "output", type=str, help="Output CSV file path")
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="JSON config file. Use 'tsdata generate --help' for config schema",
)
@click.option(
    "--preset",
    type=click.Choice(list(PRESETS.keys())),
    help="Use a preset configuration (use with --output to customize)",
)
def generate(start, end, granularity, dims, mets, output, config, preset):
    """
    Generate synthetic time series data and save to CSV.

    Examples:

        # Simple dimension (defaults to random_choice)
        tsdata generate --dims "product:A,B,C" --mets "sales:LinearTrend(limit=100)" ...

        # Full syntax with function
        tsdata generate --dims "product:random_choice:A,B,C" ...

        # Multiple dimensions
        tsdata generate --dims "product:A,B,C" --dims "region:X,Y,Z" ...

        # Multiple trends (additive)
        tsdata generate --mets "sales:LinearTrend(limit=500)+WeekendTrend(weekend_effect=50)" ...

        # Full example
        tsdata generate --dims  product:auto_generate_name:prod --mets "sales:LinearTrend(limit=500)" --mets "sales2:WeekendTrend(weekend_effect=50)" --start 2026-04-17 --end 2026-04-18 --granularity 5min --output output.csv

        # Using config file
        tsdata generate --config config.json

        # Using environment variables (prefix with TSDATA_)
        # TSDATA_START=2019-01-01 TSDATA_END=2019-01-12 TSDATA_GRANULARITY=5min tsdata generate ...

    Config file schema:

    {"start": "2019-01-01", "end": "2019-01-12", "granularity": "5min", "dimensions": ["product:A,B,C", "region:X,Y,Z"], "metrics": ["sales:LinearTrend(limit=500)+WeekendTrend(weekend_effect=50)","sales1:LinearTrend(limit=200)"], "output": "data.csv"}
    """
    # Load environment variable defaults
    env_defaults = _load_env_defaults()

    # Apply env defaults to CLI args if not specified
    start = start or env_defaults.get("start")
    end = end or env_defaults.get("end")
    granularity = granularity or env_defaults.get("granularity")
    output = output or env_defaults.get("output")

    # Load preset if specified
    if preset:
        preset_data = PRESETS[preset].copy()
        # CLI args override preset values
        if not start:
            start = preset_data.get("start")
        if not end:
            end = preset_data.get("end")
        if not granularity:
            granularity = preset_data.get("granularity")
        if not output:
            output = preset_data.get("output")
        dims = preset_data.get("dimensions", [])
        mets = preset_data.get("metrics", [])

    # Load configuration
    if config:
        config_data = _load_config(config)
        config_data = _apply_config_overrides(
            config_data, start=start, end=end, granularity=granularity, output=output
        )
        start = config_data.get("start")
        end = config_data.get("end")
        granularity = config_data.get("granularity")
        dims = config_data.get("dimensions", [])
        mets = config_data.get("metrics", [])
        output = config_data.get("output")

    # Normalize dims/mets to string (from tuple, list, or string)
    if isinstance(dims, (tuple, list)):
        dims = DIM_SEPARATOR.join(str(d) for d in dims)
    if isinstance(mets, (tuple, list)):
        mets = DIM_SEPARATOR.join(str(m) for m in mets)

    # Validate required arguments
    if not all([start, end, granularity, dims, mets, output]):
        click.echo(
            main.get_command(main, "generate").get_help(click.get_current_context())
        )
        return

    # Initialize data generator
    data_gen = DataGen()
    data_gen.start_datetime = start
    data_gen.end_datetime = end
    data_gen.to_granularity(granularity)

    # Add dimensions
    for dimension in dims.split(DIM_SEPARATOR):
        name, function_name, values = _parse_dimension_spec(dimension)

        dimension_fn = _get_dimension_function(function_name)

        try:
            data_gen.add_dimension(name, dimension_fn(values))
        except TypeError:
            try:
                # Try unpacking as separate args
                data_gen.add_dimension(name, dimension_fn(*values))
            except TypeError as e:
                raise click.BadParameter(
                    f"Invalid parameters for dimension '{name}' with function '{function_name}': {values}"
                )

    # Add metrics
    for metric in mets.split(DIM_SEPARATOR):
        parts = metric.split(":")
        name = parts[0]
        trend_specs = parts[1].split(TREND_SEPARATOR) if len(parts) > 1 else []

        trends = []
        for spec in trend_specs:
            trend_name, params = _parse_trend_spec(spec)
            trend_fn = _get_trend_function(trend_name)

            try:
                trends.append(trend_fn(**params))
            except TypeError as e:
                # Extract bad parameter name from error message
                bad_match = re.search(r"unexpected keyword argument '(\w+)'", str(e))
                bad_param = bad_match.group(1) if bad_match else "unknown"
                raise click.BadParameter(
                    f"Invalid parameter '{bad_param}' for trend '{trend_name}'"
                )

        data_gen.add_metric(name=name, trends=trends)

    # Validate output path
    output_path = Path(output)
    if output_path.suffix.lower() != ".csv":
        raise click.BadParameter("Output file must have .csv extension")

    # Generate and save data
    data = data_gen.data
    data.to_csv(output, index=True, index_label="datetime")

    click.echo(f"Generated {len(data):,} rows → {output}")


@main.command()
def dimensions():
    """List available dimension functions."""
    funcs = [
        f
        for f in dir(dimension_functions)
        if callable(getattr(dimension_functions, f))
        and not f.startswith("_")
        and f not in ("TypeVar", "Generator", "Iterable", "Tuple", "Union", "cycle")
    ]

    click.echo("Available dimension functions:\n")
    for func_name in sorted(funcs):
        func = getattr(dimension_functions, func_name)
        sig = str(inspect.signature(func))
        example = getattr(func, "_example", "")
        click.echo(f"  {func_name}{sig}")
        if example:
            click.echo(f"    → {example}")


@main.command()
def metrics():
    """List available trend functions."""
    funcs = [
        f
        for f in dir(trend_functions)
        if callable(getattr(trend_functions, f))
        and not f.startswith("_")
        and "Trend" in f
    ]

    click.echo("Available trend functions:\n")
    for func_name in sorted(funcs):
        func = getattr(trend_functions, func_name)
        sig = str(inspect.signature(func))
        example = getattr(func, "_example", "")
        click.echo(f"  {func_name}{sig}")
        if example:
            click.echo(f"    → {example}")


@main.command()
@click.argument("preset_name", required=False)
def presets(preset_name: str | None):
    """List available preset configurations or show details for a specific preset.

    Usage:
        tsdata presets              # List all presets
        tsdata presets daily-sales  # Show details for daily-sales preset
    """
    if preset_name:
        if preset_name not in PRESETS:
            raise click.ClickException(
                f"Unknown preset '{preset_name}'. Use 'tsdata presets' to list all."
            )
        config = PRESETS[preset_name]
        click.echo(f"Preset: {preset_name}\n")
        click.echo(f"  Start: {config['start']}")
        click.echo(f"  End: {config['end']}")
        click.echo(f"  Granularity: {config['granularity']}")
        click.echo(f"  Dimensions: {', '.join(config['dimensions'])}")
        click.echo(f"  Metrics: {', '.join(config['metrics'])}")
        click.echo(f"  Output: {config['output']}")
        click.echo(
            f"\nUsage: tsdata generate --preset {preset_name} --output <output.csv>"
        )
        click.echo("Or override specific values:")
        click.echo(
            f"  tsdata generate --preset {preset_name} --start 2024-02-01 --output mydata.csv"
        )
    else:
        click.echo("Available presets:\n")
        for name, config in PRESETS.items():
            click.echo(f"  {name}")
            click.echo(
                f"    Start: {config['start']}, End: {config['end']}, Granularity: {config['granularity']}"
            )
            click.echo(
                f"    Dimensions: {len(config['dimensions'])}, Metrics: {len(config['metrics'])}"
            )
            click.echo(f"    Output: {config['output']}")
            click.echo()
        click.echo("Use 'tsdata presets <name>' for detailed info on a preset.")
        click.echo("Example: tsdata presets daily-sales")


if __name__ == "__main__":
    main()
