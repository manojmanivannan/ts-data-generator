import re
from typing import Any

from ts_data_generator.schema.types import AnomalySpec, DimensionSpec, PresetConfig, TrendSpec


def _parse_value(value: str) -> int | float | str | bool | list[Any]:
    if value.lower() in ("true", "false"):
        return value.lower() == "true"

    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    if "," in value and not value.startswith("["):
        return [v.strip() for v in value.split(",")]

    return value


def parse_dimension_spec(spec: str) -> DimensionSpec:
    # Support for legacy shorthand format: name:function:values or name:values
    if ":" in spec and "=" not in spec:
        parts = spec.split(":", 2)
        if len(parts) == 2:
            name, values = parts
            func_name = "random_choice"
        else:
            name, func_name, values = parts

        value_list = values.split(",")
        parsed = [_parse_value(v.strip()) for v in value_list]
        return DimensionSpec(name=name.strip(), function_name=func_name.strip(), args=parsed)

    if "=" not in spec:
        raise ValueError(
            f"Invalid dimension spec: {spec}. Expected format: name=function(args) or name:values"
        )

    name, func_part = spec.split("=", 1)

    match = re.match(r"(\w+)(?:\((.*)\))?", func_part)
    if not match:
        raise ValueError(f"Invalid function format: {func_part}")

    func_name = match.group(1)
    args_str = match.group(2)

    args: tuple[Any, ...] = ()
    if args_str:
        args_list = [arg.strip() for arg in args_str.split(",")]
        parsed_args = [_parse_value(arg) for arg in args_list]
        args = tuple(parsed_args)

    return DimensionSpec(name=name.strip(), function_name=func_name.strip(), args=args)


def parse_trend_spec(spec: str) -> TrendSpec:
    match = re.match(r"(\w+)(?:\((.*)\))?", spec)
    if not match:
        raise ValueError(f"Invalid trend spec: {spec}")

    name = match.group(1)
    kwargs_str = match.group(2)

    kwargs: dict[str, Any] = {}
    if kwargs_str:
        # Extremely basic parser - actual parser needs bracket awareness
        kv_pairs = [pair.strip() for pair in kwargs_str.split(",") if pair.strip()]
        for pair in kv_pairs:
            if "=" not in pair:
                continue  # Ignore malformed for now
            k, v = pair.split("=", 1)
            kwargs[k.strip()] = _parse_value(v.strip())

    return TrendSpec(name=name.strip(), kwargs=kwargs)


def parse_anomaly_spec(spec: str) -> AnomalySpec:
    ts = parse_trend_spec(spec)
    return AnomalySpec(name=ts.name, kwargs=ts.kwargs)


PRESETS = {
    "daily-sales": PresetConfig(
        start="2024-01-01",
        end="2024-01-31",
        granularity="D",
        output="daily_sales.csv",
        dimensions=["product:A,B,C,D", "region:X,Y,Z"],
        metrics=["sales:LinearTrend(slope=30)+WeekendTrend(weekend_effect=100)"],
    ),
    "hourly-metrics": PresetConfig(
        start="2024-01-01",
        end="2024-01-07",
        granularity="h",
        output="hourly_metrics.csv",
        dimensions=["server:web1,web2,db1,db2", "metric:cpu,memory,disk"],
        metrics=["value:SinusoidalTrend(freq=24,amplitude=10)+LinearTrend(slope=0.1)"],
    ),
    "minute-stock": PresetConfig(
        start="2024-01-01 09:30:00",
        end="2024-01-01 16:00:00",
        granularity="min",
        output="minute_stock.csv",
        dimensions=["ticker:AAPL,MSFT,GOOGL"],
        metrics=["price:StockTrend(noise_level=0.01)"],
        anomalies=["price:PointAnomaly(probability=0.05,magnitude=5.0,mode=additive)"],
    ),
    "weekly-revenue": PresetConfig(
        start="2023-01-01",
        end="2023-12-31",
        granularity="W",
        output="weekly_revenue.csv",
        dimensions=["department:electronics,clothing,home"],
        metrics=["revenue:LinearTrend(slope=30)+SinusoidalTrend(freq=52,amplitude=5000)"],
    ),
    "monthly-recurring": PresetConfig(
        start="2020-01-01",
        end="2024-12-31",
        granularity="ME",
        output="mrr.csv",
        dimensions=["tier:basic,pro,enterprise"],
        metrics=["mrr:LinearTrend(slope=30)"],
        anomalies=["mrr:ConceptDrift(start_timestamp=2022-01-31,target_mean=100000,target_std=5000,transition_window=15552000)"],
    ),
}


def load_preset(name: str) -> PresetConfig:
    if name not in PRESETS:
        raise ValueError(f"Preset {name} not found")
    return PRESETS[name]


def apply_config_overrides(base_config: PresetConfig, **cli_kwargs: Any) -> PresetConfig:
    dims = cli_kwargs.get("dimensions")
    metrics = cli_kwargs.get("metrics")
    anomalies = cli_kwargs.get("anomalies")

    return PresetConfig(
        dimensions=list(dims) if dims else base_config.dimensions,
        metrics=list(metrics) if metrics else base_config.metrics,
        anomalies=list(anomalies) if anomalies else base_config.anomalies,
        start=base_config.start,
        end=base_config.end,
        granularity=base_config.granularity,
        output=base_config.output,
    )
