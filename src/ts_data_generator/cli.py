"""CLI module for ts-data-generator.

Provides the ``tsdata`` command-line interface via Click.
"""

import inspect
import json
import logging
import re
from pathlib import Path

import click
from pydantic import BaseModel, Field, field_validator

from ts_data_generator import DataGen
from ts_data_generator.anomalies.base import Anomaly
from ts_data_generator.exceptions import RegistryError
from ts_data_generator.schema.models import Granularity
from ts_data_generator.utils import functions as dimension_functions
from ts_data_generator.utils import trends as trend_functions
from ts_data_generator.utils.registry import Registry
from ts_data_generator.utils.trends import Trends

logger = logging.getLogger(__name__)

DIM_SEPARATOR = ";"
TREND_SEPARATOR = "+"
VALUE_SEPARATOR = ","
DEFAULT_DIMENSION_FUNCTION = "random_choice"

# ---------------------------------------------------------------------------
# Registries for CLI-pluggable types
# ---------------------------------------------------------------------------

_DIMENSION_REGISTRY = Registry(
    "ts_data_generator.utils.functions",
    name_filter=lambda n: not n.startswith("_"),
)
_TREND_REGISTRY = Registry(
    "ts_data_generator.utils.trends",
    name_filter=lambda n: not n.startswith("_") and n != "Trends",
    base_class=Trends,
)
_ANOMALY_REGISTRY = Registry(
    "ts_data_generator.anomalies",
    name_filter=lambda n: not n.startswith("_") and n != "Anomaly",
    base_class=Anomaly,
)


# ---------------------------------------------------------------------------
# Pydantic config models
# ---------------------------------------------------------------------------


class DimensionSpec(BaseModel):
    """A dimension specification in config."""

    name: str = Field(..., description="Dimension name")
    function: str = Field(default=DEFAULT_DIMENSION_FUNCTION, description="Dimension function name")
    values: list[str] = Field(..., description="Dimension values")


class MetricSpec(BaseModel):
    """A metric specification in config."""

    name: str = Field(..., description="Metric name")
    trends: str = Field(..., description="Trend specifications (comma-separated)")


class GeneratorConfig(BaseModel):
    """Configuration for data generation."""

    start: str = Field(..., description="Start datetime (YYYY-MM-DD)")
    end: str = Field(..., description="End datetime (YYYY-MM-DD)")
    granularity: str = Field(..., description="Data granularity")
    dimensions: list[str] = Field(default_factory=list, description="Dimension specs")
    metrics: list[str] = Field(default_factory=list, description="Metric specs")
    anomalies: list[str] = Field(default_factory=list, description="Anomaly specs")
    seed: int | None = Field(default=None, description="Random seed")
    output: str = Field(..., description="Output CSV file path")

    @field_validator("granularity")
    @classmethod
    def validate_granularity(cls, v: str) -> str:
        valid = [g.value for g in Granularity]
        if v not in valid:
            raise ValueError(f"Invalid granularity {v!r}. Valid: {', '.join(valid)}")
        return v


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

PRESETS: dict[str, dict] = {
    "daily-sales": {
        "start": "2024-01-01",
        "end": "2024-01-31",
        "granularity": "D",
        "dimensions": ["product:A,B,C,D", "region:X,Y,Z"],
        "metrics": ["sales:LinearTrend(slope=30)+WeekendTrend(weekend_effect=100)"],
        "output": "daily_sales.csv",
    },
    "hourly-metrics": {
        "start": "2024-01-01",
        "end": "2024-01-02",
        "granularity": "h",
        "dimensions": ["sensor:random_choice:S1,S2,S3"],
        "metrics": [
            "temperature:LinearTrend(slope=30)",
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
        "metrics": ["revenue:LinearTrend(slope=30)+WeekendTrend(weekend_effect=50)"],
        "output": "weekly_revenue.csv",
    },
    "monthly-recurring": {
        "start": "2024-01-01",
        "end": "2024-12-31",
        "granularity": "D",
        "dimensions": ["plan:Basic,Pro,Enterprise"],
        "metrics": ["mrr:LinearTrend(slope=30)"],
        "output": "monthly_mrr.csv",
    },
    "scientific-mock": {
        "start": "2025-01-01T00:00:00",
        "end": "2025-01-07T00:00:00",
        "granularity": "5min",
        "dimensions": [
            "experiment_id:auto_generate_name:exp_",
            "sensor_type:random_choice:temperature,pressure,radiation,voltage",
            "lab_location:ordered_choice:Site_A,Site_B,Site_C",
            "batch_number:random_int:1,100",
            "calibration_factor:random_float:0.9,1.1",
        ],
        "metrics": [
            "temperature:LinearTrend(offset=25,slope=0.1)+SinusoidalTrend(amplitude=5,freq=1)+ARNoiseTrend(decay=0.8,noise_std=0.5)",
            "pressure:LinearTrend(offset=1013,slope=-1)+ARNoiseTrend(decay=0.9,noise_std=2)+WeekendTrend(weekend_effect=-10,direction=down)",
            "radiation_level:MarkovTrend(states=[safe,elevated,danger],values=[0.1,1.5,5.0],stickiness=0.95,noise_std=0.1)+LinearTrend(offset=0,slope=0.01)",
            "voltage:SinusoidalTrend(amplitude=2,freq=0.5)+ARNoiseTrend(decay=0.5,noise_std=0.2)+StockTrend(amplitude=5.0,direction=up,noise_level=0.1)",
            "equipment_load:WeekendTrend(weekend_effect=-20,direction=down)+LinearTrend(offset=80,slope=0)+ARNoiseTrend(decay=0.7,noise_std=5)+SinusoidalTrend(amplitude=10,freq=1)",
        ],
        "anomalies": [
            "temperature:PointAnomaly(probability=0.01,magnitude=15)+MissingData(mode=burst,burst_probability=0.005,min_length=3,max_length=10)",
            "pressure:PointAnomaly(probability=0.005,mode=replacement,magnitude=0.0)",
            "radiation_level:PointAnomaly(probability=0.01,mode=additive,magnitude=10.0)",
        ],
        "output": "scientific_mock_data.csv",
    },
}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_value(value: str) -> int | float | str | bool | list:
    """Parse a string value into int, float, bool, list, or str."""
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        return [_parse_value(v) for v in _split_bracket_aware(inner)]
    if value.lstrip("-").isdigit():
        return int(value)
    if "." in value:
        try:
            return float(value)
        except ValueError:
            pass
    return value


def _parse_dimension_spec(spec: str) -> tuple[str, str, tuple | list]:
    """Parse a dimension specification string.

    Formats:
      - ``name:function:values`` (e.g. ``"product:random_choice:A,B,C"``)
      - ``name:values`` (defaults to ``random_choice``)

    Returns:
        Tuple of (name, function_name, values).
    """
    parts = spec.split(":", 2)

    if len(parts) == 2:
        name, values = parts
        function_name = DEFAULT_DIMENSION_FUNCTION
    else:
        name, function_name, values = parts

    value_list = values.split(VALUE_SEPARATOR)
    if all(v.lstrip("-").replace(".", "", 1).isdigit() for v in value_list if v):
        parsed = tuple(
            (int(v) if v.isdigit() or (v.startswith("-") and v[1:].isdigit()) else float(v))
            for v in value_list
        )
    else:
        parsed = value_list

    return name, function_name, parsed


def _split_bracket_aware(text: str, sep: str = VALUE_SEPARATOR) -> list[str]:
    """Split by *sep* but ignore separators inside ``[...]``."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch == "[":
            depth += 1
            current.append(ch)
        elif ch == "]":
            depth = max(0, depth - 1)
            current.append(ch)
        elif ch == sep and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


def _parse_trend_spec(
    trend_spec: str,
) -> tuple[str, dict[str, int | float | str | bool | list]]:
    """Parse a trend specification string.

    Format: ``TrendName(param1=value1,param2=value2)``

    Returns:
        Tuple of (trend_name, param_dict).

    Raises:
        click.BadParameter: If the format is invalid.
    """
    match = re.match(r"(\w+)\((.*)\)", trend_spec)
    if not match:
        raise click.BadParameter(
            f"Invalid trend format {trend_spec!r}. Expected: TrendName(param=value)"
        )

    trend_name = match.group(1)
    params_str = match.group(2)

    param_dict: dict[str, int | float | str] = {}
    if params_str:
        for param in _split_bracket_aware(params_str):
            try:
                key, value = param.split("=", 1)
            except ValueError:
                raise click.BadParameter(
                    f"Invalid parameter {param!r} in {trend_spec!r}. Expected key=value format."
                ) from None
            param_dict[key] = _parse_value(value)

    return trend_name, param_dict


def _get_dimension_function(function_name: str):
    """Look up a dimension function by name.

    Raises:
        click.BadParameter: If the function is not found.
    """
    try:
        return _DIMENSION_REGISTRY.get(function_name)
    except RegistryError as exc:
        raise click.BadParameter(str(exc)) from exc


def _get_trend_function(function_name: str):
    """Look up a trend class by name.

    Raises:
        click.BadParameter: If the class is not found.
    """
    try:
        return _TREND_REGISTRY.get(function_name)
    except RegistryError as exc:
        raise click.BadParameter(str(exc)) from exc


def _load_config(config_path: Path) -> dict:
    """Load and validate a JSON configuration file.

    Raises:
        click.BadParameter: If the JSON is invalid or validation fails.
    """
    try:
        with open(config_path) as fh:
            config = json.load(fh)
    except json.JSONDecodeError as exc:
        raise click.BadParameter(f"Invalid JSON in config file: {exc}") from exc

    try:
        validated = GeneratorConfig(**config)
        return validated.model_dump()
    except Exception as exc:
        raise click.BadParameter(f"Invalid config: {exc}") from exc


def _apply_config_overrides(config: dict, **cli_kwargs: str | None) -> dict:
    """Overlay CLI argument values on top of a config dict."""
    result = dict(config)
    for key in ("start", "end", "granularity", "output"):
        if cli_kwargs.get(key):
            result[key] = cli_kwargs[key]
    return result


def _parse_anomaly_spec(
    spec: str,
) -> tuple[str, dict[str, int | float | str | bool | list]]:
    """Parse an anomaly specification string.

    Format: ``AnomalyType(param1=value1,param2=value2)``

    Returns:
        Tuple of (anomaly_name, param_dict).

    Raises:
        click.BadParameter: If the format is invalid.
    """
    return _parse_trend_spec(spec)


def _get_anomaly_class(class_name: str):
    """Look up an anomaly class by name.

    Raises:
        click.BadParameter: If the class is not found.
    """
    try:
        return _ANOMALY_REGISTRY.get(class_name)
    except RegistryError as exc:
        raise click.BadParameter(str(exc)) from exc


def _normalize_to_string(value: tuple | list | str) -> str:
    """Convert a tuple/list/str to a semicolon-joined string for parsing."""
    if isinstance(value, (tuple, list)):
        return DIM_SEPARATOR.join(str(v) for v in value)
    return value


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.group(context_settings={"max_content_width": 220})
def main():
    """CLI tool for generating synthetic time series data."""


@main.command()
@click.option("--start", type=str, help="Start datetime (YYYY-MM-DD)")
@click.option("--end", type=str, help="End datetime (YYYY-MM-DD)")
@click.option(
    "--granularity",
    type=click.Choice([g.value for g in Granularity], case_sensitive=False),
    help="Data granularity",
)
@click.option(
    "--dims",
    type=str,
    multiple=True,
    help=f"Dimension specs (sep by {DIM_SEPARATOR}). "
    "Formats: 'name:function:values' or 'name:values'",
)
@click.option(
    "--mets",
    type=str,
    multiple=True,
    help=f"Metric specs (sep by {DIM_SEPARATOR}). Format: 'name:Trend(param=value)+Trend2'",
)
@click.option(
    "--anomalies",
    type=str,
    multiple=True,
    help="Anomaly specs keyed by metric name. Repeatable. "
    "Format: 'metric:AnomalyType(param=value)+Anomaly2'",
)
@click.option("--output", type=str, help="Output CSV file path")
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Random seed for deterministic generation",
)
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
@click.option(
    "--show-sample-config",
    is_flag=True,
    help="Print a sample JSON config file to stdout and exit. "
    "Redirect to a file to edit: 'tsdata generate --show-sample-config > config.json'",
)
def generate(
    start: str | None,
    end: str | None,
    granularity: str | None,
    dims: tuple[str, ...],
    mets: tuple[str, ...],
    anomalies: tuple[str, ...],
    output: str | None,
    seed: int | None,
    config: Path | None,
    preset: str | None,
    show_sample_config: bool,
) -> None:
    """Generate synthetic time series data and save to CSV.

    Examples:

    \b
        # Simple dimension (defaults to random_choice)
        tsdata generate --dims "product:A,B,C" --mets "sales:LinearTrend(slope=30)" ...

    \b
        # Full syntax with function
        tsdata generate --dims "product:random_choice:A,B,C" ...

    \b
        # Multiple dimensions
        tsdata generate --dims "product:A,B,C" --dims "region:X,Y,Z" ...

    \b
        # Multiple trends (additive)
        tsdata generate --mets "sales:LinearTrend(slope=30)+WeekendTrend(weekend_effect=50)" ...

    \b
        # Deterministic generation with seed
        tsdata generate --seed 42 --dims "product:A,B" ...

    \b
        # Point anomalies on a metric
        tsdata generate --anomalies \\
            "sales:PointAnomaly(probability=0.01,magnitude=5)" ...

    \b
        # Missing data (random mode)
        tsdata generate --anomalies \\
            "sales:MissingData(probability=0.05)" ...

    \b
        # Missing data (burst mode)
        tsdata generate --anomalies \\
            "sales:MissingData(mode=burst,burst_probability=0.02,"
            "min_length=3,max_length=10)" ...

    \b
        # Concept drift (single segment)
        tsdata generate --anomalies \\
            "sales:ConceptDrift(start_timestamp=2019-01-01T06:00:00,"
            "transition_window=1800,target_mean=50,target_std=5,"
            "hold_duration=7200)" ...

    \b
        # Multiple anomaly types on one metric
        tsdata generate --anomalies \\
            "sales:PointAnomaly(probability=0.01,magnitude=5)"
            "+MissingData(probability=0.05)" ...

    \b
        # Multi-segment concept drift (repeat --anomalies)
        tsdata generate \\
            --anomalies "sales:ConceptDrift(start_timestamp=2019-01-01T00:00:00,"
            "transition_window=1800,target_mean=50,hold_duration=7200)" \\
            --anomalies "sales:ConceptDrift(start_timestamp=2019-01-02T00:00:00,"
            "transition_window=3600,target_mean=100,hold_duration=7200,restore=true)" ...

    \b
        # Full example with seed and anomalies
        tsdata generate --dims "product:A,B" \\
            --mets "sales:LinearTrend(slope=30)" \\
            --anomalies "sales:PointAnomaly(probability=0.01,magnitude=5)" \\
            --seed 42 \\
            --start 2024-01-01 --end 2024-01-02 \\
            --granularity 5min --output output.csv

    \b
        # Full example with seed and anomalies
        tsdata generate --dims product:auto_generate_name:prod \\
            --mets "sales:LinearTrend(slope=30)" \\
            --mets "sales2:WeekendTrend(weekend_effect=50)" \\
            --anomalies "sales:PointAnomaly(probability=0.01,magnitude=5)" \\
            --seed 42 \\
            --start 2026-04-17 --end 2026-04-18 --granularity 5min --output output.csv

    \b
        # Using config file
        tsdata generate --config config.json
    Config file schema::

        {
          "start": "2019-01-01",
          "end": "2019-01-12",
          "granularity": "5min",
          "dimensions": ["product:A,B,C", "region:X,Y,Z"],
          "metrics": [
            "sales:LinearTrend(slope=30)+WeekendTrend(weekend_effect=50)",
            "sales1:LinearTrend(slope=30)"
          ],
          "anomalies": [
            "sales:PointAnomaly(probability=0.01,magnitude=5)+MissingData(probability=0.05)"
          ],
          "seed": 42,
          "output": "data.csv"
        }
    """

    if show_sample_config:
        from importlib.resources import files

        sample = files("ts_data_generator.data").joinpath("sample_config.json").read_text()
        click.echo(sample)
        return

    if preset:
        preset_data = PRESETS[preset].copy()
        if not start:
            start = preset_data.get("start")
        if not end:
            end = preset_data.get("end")
        if not granularity:
            granularity = preset_data.get("granularity")
        if not output:
            output = preset_data.get("output")
        dims = tuple(preset_data.get("dimensions", []))
        mets = tuple(preset_data.get("metrics", []))

    if config:
        config_data = _load_config(config)
        config_data = _apply_config_overrides(
            config_data, start=start, end=end, granularity=granularity, output=output
        )
        start = config_data.get("start")
        end = config_data.get("end")
        granularity = config_data.get("granularity")
        dims = tuple(config_data.get("dimensions", []))
        mets = tuple(config_data.get("metrics", []))
        output = config_data.get("output")
        if not seed:
            seed = config_data.get("seed")
        if not anomalies:
            config_anomalies = config_data.get("anomalies", [])
            anomalies = tuple(config_anomalies)

    dims_str = _normalize_to_string(dims)
    mets_str = _normalize_to_string(mets)

    if not all([start, end, granularity, dims_str, mets_str, output]):
        click.echo(main.get_command(main, "generate").get_help(click.get_current_context()))
        return

    data_gen = DataGen(seed=seed)
    data_gen.start_datetime = start
    data_gen.end_datetime = end
    data_gen.to_granularity(granularity)

    for dimension in dims_str.split(DIM_SEPARATOR):
        dim_name, func_name, values = _parse_dimension_spec(dimension)
        dim_fn = _get_dimension_function(func_name)

        try:
            data_gen.add_dimension(dim_name, dim_fn(values))
        except TypeError:
            try:
                data_gen.add_dimension(dim_name, dim_fn(*values))
            except TypeError as exc:
                raise click.BadParameter(
                    f"Invalid parameters for dimension {dim_name!r} "
                    f"with function {func_name!r}: {values}"
                ) from exc

    # Collect metrics: {name: {"trends": [...], "anomalies": [...]}}
    metrics_data: dict[str, dict[str, list] | None] = {}

    for metric in mets_str.split(DIM_SEPARATOR):
        parts = metric.split(":")
        metric_name = parts[0]
        trend_specs = parts[1].split(TREND_SEPARATOR) if len(parts) > 1 else []

        trends = []
        for spec in trend_specs:
            trend_name, params = _parse_trend_spec(spec)
            trend_fn = _get_trend_function(trend_name)

            try:
                trends.append(trend_fn(**params))
            except TypeError as exc:
                bad_match = re.search(r"unexpected keyword argument '(\w+)'", str(exc))
                bad_param = bad_match.group(1) if bad_match else "unknown"
                raise click.BadParameter(
                    f"Invalid parameter {bad_param!r} for trend {trend_name!r}"
                ) from exc

        if metric_name not in metrics_data:
            metrics_data[metric_name] = {"trends": [], "anomalies": []}
        metrics_data[metric_name]["trends"].extend(trends)

    for anomaly_entry in anomalies:
        parts = anomaly_entry.split(":", 1)
        metric_name = parts[0]
        spec_strings = parts[1].split(TREND_SEPARATOR) if len(parts) > 1 else []

        if metric_name not in metrics_data:
            metrics_data[metric_name] = {"trends": [], "anomalies": []}

        for spec in spec_strings:
            anom_name, params = _parse_anomaly_spec(spec)
            anom_cls = _get_anomaly_class(anom_name)
            if anom_name == "ConceptDrift":
                from ts_data_generator.anomalies import DriftSegment

                segment = DriftSegment(**params)
                # Check if we already have a ConceptDrift waiting to collect segments
                existing = metrics_data[metric_name]["anomalies"]
                found_cd = None
                for a in existing:
                    if isinstance(a, anom_cls):
                        found_cd = a
                        break
                if found_cd is not None:
                    found_cd.segments.append(segment)
                else:
                    metrics_data[metric_name]["anomalies"].append(anom_cls(segments=[segment]))
            else:
                metrics_data[metric_name]["anomalies"].append(anom_cls(**params))

    for metric_name, data in metrics_data.items():
        if data is None:
            continue
        data_gen.add_metric(
            name=metric_name,
            trends=data["trends"],
            anomalies=data["anomalies"] if data["anomalies"] else None,
        )

    output_path = Path(output)
    if output_path.suffix.lower() != ".csv":
        raise click.BadParameter("Output file must have .csv extension.")

    data = data_gen.data
    data.to_csv(output, index=True, index_label="datetime")

    logger.info("Generated %s rows → %s", f"{len(data):,}", output)
    click.echo(f"Generated {len(data):,} rows → {output}")


@main.command()
def dimensions() -> None:
    """List available dimension functions."""
    excluded = {"TypeVar", "Generator", "Iterable", "Tuple", "Union", "cycle"}
    funcs = [
        f
        for f in dir(dimension_functions)
        if callable(getattr(dimension_functions, f)) and not f.startswith("_") and f not in excluded
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
def metrics() -> None:
    """List available trend functions."""
    funcs = [
        f
        for f in dir(trend_functions)
        if callable(getattr(trend_functions, f)) and not f.startswith("_") and "Trend" in f
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
def presets(preset_name: str | None) -> None:
    """List available preset configurations or show details for a specific preset.

    Usage:

    \b
        tsdata presets              # List all presets
        tsdata presets daily-sales  # Show details for daily-sales preset
    """
    if preset_name:
        if preset_name not in PRESETS:
            raise click.ClickException(
                f"Unknown preset {preset_name!r}. Use 'tsdata presets' to list all."
            )
        cfg = PRESETS[preset_name]
        click.echo(f"Preset: {preset_name}\n")
        click.echo(f"  Start: {cfg['start']}")
        click.echo(f"  End: {cfg['end']}")
        click.echo(f"  Granularity: {cfg['granularity']}")
        click.echo(f"  Dimensions: {', '.join(cfg['dimensions'])}")
        click.echo(f"  Metrics: {', '.join(cfg['metrics'])}")
        click.echo(f"  Output: {cfg['output']}")
        click.echo(f"\nUsage: tsdata generate --preset {preset_name} --output <output.csv>")
        click.echo("Or override specific values:")
        click.echo(
            f"  tsdata generate --preset {preset_name} --start 2024-02-01 --output mydata.csv"
        )
    else:
        click.echo("Available presets:\n")
        for name, cfg in PRESETS.items():
            click.echo(f"  {name}")
            click.echo(
                f"    Start: {cfg['start']}, End: {cfg['end']}, Granularity: {cfg['granularity']}"
            )
            click.echo(f"    Dimensions: {len(cfg['dimensions'])}, Metrics: {len(cfg['metrics'])}")
            click.echo(f"    Output: {cfg['output']}")
            click.echo()
        click.echo("Use 'tsdata presets <name>' for detailed info on a preset.")
        click.echo("Example: tsdata presets daily-sales")


if __name__ == "__main__":
    main()
