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
    "economics-cycle": PresetConfig(
        start="2024-01-01",
        end="2025-12-31",
        granularity="D",
        output="economics_cycle.csv",
        dimensions=[
            "country:random_choice:US,DE,IN,BR,JP",
            "sector:random_choice:manufacturing,services,energy,technology",
            "policy_regime:ordered_choice:tightening,neutral,easing",
        ],
        metrics=[
            "gdp_index:LinearTrend(offset=100,slope=0.02)+SinusoidalTrend(amplitude=2.5,freq=365)+ARNoiseTrend(decay=0.65,noise_std=0.35)",
            "inflation_rate:SinusoidalTrend(amplitude=0.8,freq=180)+ARNoiseTrend(decay=0.75,noise_std=0.2)",
            "unemployment_rate:LinearTrend(offset=6.5,slope=-0.01)+SinusoidalTrend(amplitude=0.5,freq=365)+ARNoiseTrend(decay=0.7,noise_std=0.15)",
        ],
        anomalies=[
            "gdp_index:PointAnomaly(probability=0.003,mode=additive,magnitude=-6.0)",
            "inflation_rate:PointAnomaly(probability=0.004,mode=additive,magnitude=2.0)",
        ],
    ),
    "sociology-mobility": PresetConfig(
        start="2025-01-01",
        end="2025-06-30",
        granularity="D",
        output="sociology_mobility.csv",
        dimensions=[
            "age_group:ordered_choice:18-24,25-34,35-49,50-64,65+",
            "region:random_choice:urban,suburban,rural",
            "education_level:random_choice:high_school,bachelors,masters,doctorate",
            "respondent_batch:random_int:1,50",
        ],
        metrics=[
            "mobility_score:MarkovTrend(states=[low,mid,high],values=[35,55,75],stickiness=0.92,noise_std=2.0)+LinearTrend(offset=0,slope=0.01)",
            "trust_index:SinusoidalTrend(amplitude=4,freq=30)+ARNoiseTrend(decay=0.8,noise_std=1.2)",
            "participation_rate:LinearTrend(offset=58,slope=0.01)+WeekendTrend(weekend_effect=-3,direction=down)+ARNoiseTrend(decay=0.75,noise_std=0.8)",
        ],
        anomalies=[
            "trust_index:MissingData(mode=burst,burst_probability=0.01,min_length=2,max_length=5)",
        ],
    ),
    "electronics-reliability": PresetConfig(
        start="2025-03-01T00:00:00",
        end="2025-03-08T00:00:00",
        granularity="5min",
        output="electronics_reliability.csv",
        dimensions=[
            "chip_id:auto_generate_name:chip",
            "assembly_line:ordered_choice:Line_A,Line_B,Line_C,Line_D",
            "component_family:random_choice:power,rf,digital,sensor,analog",
            "test_station:random_choice:ICT1,ICT2,FCT1,FCT2,BURNIN",
            "lot_number:random_int:1000,1300",
            "reference_voltage:random_float:3.0,3.6",
            "qa_mode:constant:production",
        ],
        metrics=[
            "voltage_drift:LinearTrend(offset=3.3,slope=-0.0003)+ARNoiseTrend(decay=0.85,noise_std=0.015)",
            "temperature_c:SinusoidalTrend(amplitude=3,freq=1)+ARNoiseTrend(decay=0.7,noise_std=0.4)",
            "defect_ppm:MarkovTrend(states=[normal,warn,critical],values=[120,550,1800],stickiness=0.96,noise_std=40)+WeekendTrend(weekend_effect=-70,direction=down)",
            "throughput_units:LinearTrend(offset=850,slope=0.03)+SinusoidalTrend(amplitude=40,freq=1)+ARNoiseTrend(decay=0.6,noise_std=12)",
            "supplier_shock_index:StockTrend(amplitude=20,direction=up,noise_level=0.2)",
            "holiday_pressure_index:HolidayTrend(effect=120,pre_window=1,post_window=1,direction=up,dates=[2025-03-03,2025-03-06])",
        ],
        anomalies=[
            "defect_ppm:PointAnomaly(probability=0.006,mode=additive,magnitude=1200)",
            "throughput_units:MissingData(mode=random,probability=0.004)",
            "voltage_drift:PointAnomaly(probability=0.003,mode=replacement,magnitude=2.8)",
            "temperature_c:MissingData(mode=burst,burst_probability=0.008,min_length=2,max_length=5)",
            "supplier_shock_index:ConceptDrift(start_timestamp=2025-03-03T12:00:00,target_mean=40,target_std=4,transition_window=3600,hold_duration=21600,restore=true)+ConceptDrift(start_timestamp=2025-03-05T18:00:00,target_mean=-10,target_std=3,transition_window=1800,hold_duration=14400,restore=false)",
        ],
    ),
    "epidemiology-wave": PresetConfig(
        start="2024-09-01",
        end="2025-03-31",
        granularity="D",
        output="epidemiology_wave.csv",
        dimensions=[
            "region:random_choice:North,South,East,West",
            "age_band:ordered_choice:0-17,18-39,40-64,65+",
            "pathogen_variant:ordered_choice:A,B,C",
        ],
        metrics=[
            "incidence_rate:SinusoidalTrend(amplitude=25,freq=60)+LinearTrend(offset=40,slope=-0.02)+ARNoiseTrend(decay=0.7,noise_std=4)",
            "hospitalization_rate:LinearTrend(offset=8,slope=-0.01)+SinusoidalTrend(amplitude=3,freq=60)+ARNoiseTrend(decay=0.75,noise_std=0.7)",
            "testing_volume:SinusoidalTrend(amplitude=200,freq=14)+WeekendTrend(weekend_effect=-140,direction=down)+ARNoiseTrend(decay=0.65,noise_std=25)",
        ],
        anomalies=[
            "incidence_rate:PointAnomaly(probability=0.006,mode=additive,magnitude=35)",
            "testing_volume:MissingData(mode=burst,burst_probability=0.008,min_length=1,max_length=3)",
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
