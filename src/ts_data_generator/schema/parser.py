import re
from typing import Any

from ts_data_generator.schema.types import AnomalySpec, DimensionSpec, PresetConfig, TrendSpec


def _parse_value(value: str) -> int | float | str | bool | list[Any]:
    value = value.strip()

    if value.lower() in ("true", "false"):
        return value.lower() == "true"

    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        if not inner.strip():
            return []
        return [_parse_value(v) for v in _split_bracket_aware(inner)]

    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    if "," in value and not value.startswith("["):
        return [v.strip() for v in value.split(",")]

    return value


def _split_bracket_aware(text: str, sep: str = ",") -> list[str]:
    """Split by separator while ignoring separators inside brackets."""
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
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)

    if current:
        parts.append("".join(current).strip())

    return parts


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
        args_list = _split_bracket_aware(args_str)
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
        kv_pairs = [pair for pair in _split_bracket_aware(kwargs_str) if pair]
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
    "scientific-mock": PresetConfig(
        start="2025-01-01T00:00:00",
        end="2025-01-07T00:00:00",
        granularity="5min",
        output="scientific_mock_data.csv",
        dimensions=[
            "experiment_id:auto_generate_name:exp_",
            "sensor_type:random_choice:temperature,pressure,radiation,voltage",
            "lab_location:ordered_choice:Site_A,Site_B,Site_C",
            "batch_number:random_int:1,100",
            "calibration_factor:random_float:0.9,1.1",
        ],
        metrics=[
            "temperature:LinearTrend(offset=25,slope=0.1)+SinusoidalTrend(amplitude=5,freq=1)+ARNoiseTrend(decay=0.8,noise_std=0.5)",
            "pressure:LinearTrend(offset=1013,slope=-1)+ARNoiseTrend(decay=0.9,noise_std=2)+WeekendTrend(weekend_effect=-10,direction=down)",
            "radiation_level:MarkovTrend(states=[safe,elevated,danger],values=[0.1,1.5,5.0],stickiness=0.95,noise_std=0.1)+LinearTrend(offset=0,slope=0.01)",
            "voltage:SinusoidalTrend(amplitude=2,freq=0.5)+ARNoiseTrend(decay=0.5,noise_std=0.2)+StockTrend(amplitude=5.0,direction=up,noise_level=0.1)",
            "equipment_load:WeekendTrend(weekend_effect=-20,direction=down)+LinearTrend(offset=80,slope=0)+ARNoiseTrend(decay=0.7,noise_std=5)+SinusoidalTrend(amplitude=10,freq=1)",
        ],
        anomalies=[
            "temperature:PointAnomaly(probability=0.01,magnitude=15)+MissingData(mode=burst,burst_probability=0.005,min_length=3,max_length=10)",
            "pressure:PointAnomaly(probability=0.005,mode=replacement,magnitude=0.0)",
            "radiation_level:PointAnomaly(probability=0.01,mode=additive,magnitude=10.0)",
        ],
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
