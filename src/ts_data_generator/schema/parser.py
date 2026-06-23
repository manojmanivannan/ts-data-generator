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
        metrics=["price:LinearTrend(offset=100,slope=0.2)+MarkovTrend(states=[bear,neutral,bull],values=[10,50,120],stickiness=0.98,noise_std=2.0)+StockTrend(amplitude=10.0,direction=up,noise_level=0.01)"],
        anomalies=["price:PointAnomaly(probability=0.05,magnitude=5.0,mode=additive)"],
    ),
    "weekly-revenue": PresetConfig(
        start="2020-01-01",
        end="2025-12-31",
        granularity="W",
        output="weekly_revenue.csv",
        dimensions=["department:ordered_choice:electronics,clothing,home"],
        metrics=["revenue:LinearTrend(offset=10000,slope=10)+SinusoidalTrend(freq=365,amplitude=2000)+MarkovTrend(states=[low,normal,promo],values=[0,2000,8000],stickiness=0.85,noise_std=100)+ARNoiseTrend(decay=0.98,noise_std=50)"],
    ),
    "monthly-recurring": PresetConfig(
        start="2018-01-01",
        end="2025-12-31",
        granularity="ME",
        output="mrr.csv",
        dimensions=["tier:ordered_choice:basic,pro,enterprise"],
        metrics=["mrr:LinearTrend(offset=50000,slope=10)+MarkovTrend(states=[slow,normal,fast],values=[1000,5000,15000],stickiness=0.9,noise_std=500)+ARNoiseTrend(decay=0.85,noise_std=1000)"],
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
            "temperature:SinusoidalTrend(amplitude=5,freq=1.0,phase=0)+LinearTrend(offset=25,slope=0)+ARNoiseTrend(decay=0.85,noise_std=0.1)+WeekendTrend(weekend_effect=4,direction=down)",
            "pressure:SinusoidalTrend(amplitude=8,freq=1.0,phase=-2)+LinearTrend(offset=1013,slope=0)+ARNoiseTrend(decay=0.85,noise_std=0.2)+WeekendTrend(weekend_effect=10,direction=down)",
            "radiation_level:MarkovTrend(states=[safe,elevated,danger],values=[0.5,1.5,3.5],stickiness=0.95,noise_std=0.05)+SinusoidalTrend(amplitude=2.5,freq=1.0,phase=0)+LinearTrend(offset=2.0,slope=0.01)",
            "voltage:SinusoidalTrend(amplitude=3.0,freq=1.0,phase=-1)+LinearTrend(offset=12.0,slope=0)+ARNoiseTrend(decay=0.85,noise_std=0.05)+StockTrend(amplitude=1.0,direction=up,noise_level=0.05)+WeekendTrend(weekend_effect=1.5,direction=down)",
            "equipment_load:SinusoidalTrend(amplitude=10,freq=1.0,phase=0)+LinearTrend(offset=80,slope=0)+ARNoiseTrend(decay=0.85,noise_std=0.5)+WeekendTrend(weekend_effect=20,direction=down)",
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
            "gdp_index:SinusoidalTrend(amplitude=15.0,freq=1000,phase=0)+LinearTrend(offset=120,slope=0.02)+ARNoiseTrend(decay=0.98,noise_std=0.15)+WeekendTrend(weekend_effect=1.0,direction=down)",
            "inflation_rate:SinusoidalTrend(amplitude=3.0,freq=1000,phase=-48)+LinearTrend(offset=4.5,slope=0.005)+ARNoiseTrend(decay=0.98,noise_std=0.05)+WeekendTrend(weekend_effect=0.2,direction=down)",
            "unemployment_rate:SinusoidalTrend(amplitude=-2.5,freq=1000,phase=-48)+LinearTrend(offset=6.5,slope=-0.005)+ARNoiseTrend(decay=0.98,noise_std=0.03)+WeekendTrend(weekend_effect=0.1,direction=up)",
        ],
        anomalies=[
            "gdp_index:PointAnomaly(probability=0.003,mode=additive,magnitude=-6.0)",
            "inflation_rate:PointAnomaly(probability=0.004,mode=additive,magnitude=2.0)",
        ],
    ),
    "sociology-mobility": PresetConfig(
        start="2023-01-01",
        end="2025-12-31",
        granularity="D",
        output="sociology_mobility.csv",
        dimensions=[
            "age_group:ordered_choice:18-24,25-34,35-49,50-64,65+",
            "region:random_choice:urban,suburban,rural",
            "education_level:random_choice:high_school,bachelors,masters,doctorate",
            "respondent_batch:random_int:1,50",
        ],
        metrics=[
            "mobility_score:SinusoidalTrend(amplitude=12,freq=1000,phase=0)+LinearTrend(offset=55,slope=0.01)+ARNoiseTrend(decay=0.98,noise_std=0.15)+WeekendTrend(weekend_effect=4.0,direction=down)",
            "trust_index:SinusoidalTrend(amplitude=8,freq=1000,phase=-24)+LinearTrend(offset=60,slope=0)+ARNoiseTrend(decay=0.98,noise_std=0.1)+WeekendTrend(weekend_effect=2.5,direction=down)",
            "participation_rate:SinusoidalTrend(amplitude=6,freq=1000,phase=-48)+LinearTrend(offset=58,slope=0.01)+ARNoiseTrend(decay=0.98,noise_std=0.15)+WeekendTrend(weekend_effect=3.0,direction=down)",
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
            "voltage_drift:LinearTrend(offset=3.3,slope=-0.0003)+SinusoidalTrend(amplitude=0.2,freq=7.0,phase=0)+ARNoiseTrend(decay=0.99,noise_std=0.001)+WeekendTrend(weekend_effect=0.15,direction=down,limit=0.15)",
            "temperature_c:SinusoidalTrend(amplitude=5.0,freq=7.0,phase=-6)+LinearTrend(offset=25.0,slope=0.01)+ARNoiseTrend(decay=0.99,noise_std=0.05)+WeekendTrend(weekend_effect=2.0,direction=down,limit=2.0)",
            "defect_ppm:MarkovTrend(states=[normal,warn,critical],values=[1.0,2.0,3.0],stickiness=0.99,noise_std=0.1)+SinusoidalTrend(amplitude=150.0,freq=7.0,phase=-12)+LinearTrend(offset=500.0,slope=0)+ARNoiseTrend(decay=0.99,noise_std=5.0)+WeekendTrend(weekend_effect=70.0,direction=down,limit=70.0)",
            "throughput_units:SinusoidalTrend(amplitude=100.0,freq=7.0,phase=0)+LinearTrend(offset=850,slope=0.03)+ARNoiseTrend(decay=0.99,noise_std=1.0)+WeekendTrend(weekend_effect=70.0,direction=down,limit=70.0)",
            "supplier_shock_index:StockTrend(amplitude=10.0,direction=up,noise_level=0.05)+SinusoidalTrend(amplitude=5.0,freq=7.0,phase=-18)+LinearTrend(offset=100.0,slope=0)+WeekendTrend(weekend_effect=2.0,direction=down,limit=2.0)",
            "holiday_pressure_index:HolidayTrend(effect=40,pre_window=1,post_window=1,direction=up,dates=[2025-03-03,2025-03-06])+SinusoidalTrend(amplitude=80.0,freq=7.0,phase=0)+LinearTrend(offset=120.0,slope=0)",
        ],
        anomalies=[
            "defect_ppm:PointAnomaly(probability=0.006,mode=additive,magnitude=1200)",
            "throughput_units:MissingData(mode=random,probability=0.004)",
            "voltage_drift:PointAnomaly(probability=0.003,mode=replacement,magnitude=2.8)",
            "temperature_c:MissingData(mode=burst,burst_probability=0.008,min_length=2,max_length=5)",
            "supplier_shock_index:ConceptDrift(start_timestamp=2025-03-03T12:00:00,target_mean=40,target_std=4,transition_window=3600,hold_duration=21600,restore=true)+ConceptDrift(start_timestamp=2025-03-05T18:00:00,target_mean=15,target_std=3,transition_window=1800,hold_duration=14400,restore=false)",
        ],
    ),
    "epidemiology-wave": PresetConfig(
        start="2023-01-01",
        end="2025-12-31",
        granularity="D",
        output="epidemiology_wave.csv",
        dimensions=[
            "region:random_choice:North,South,East,West",
            "age_band:ordered_choice:0-17,18-39,40-64,65+",
            "pathogen_variant:ordered_choice:A,B,C",
        ],
        metrics=[
            "incidence_rate:SinusoidalTrend(amplitude=80,freq=1000,phase=0)+LinearTrend(offset=150,slope=0)+ARNoiseTrend(decay=0.98,noise_std=1.0)+WeekendTrend(weekend_effect=15,direction=down)",
            "hospitalization_rate:SinusoidalTrend(amplitude=12,freq=1000,phase=-48)+LinearTrend(offset=25,slope=0)+ARNoiseTrend(decay=0.98,noise_std=0.15)+WeekendTrend(weekend_effect=2,direction=down)",
            "testing_volume:SinusoidalTrend(amplitude=250,freq=1000,phase=0)+LinearTrend(offset=1500,slope=0)+ARNoiseTrend(decay=0.98,noise_std=4.0)+WeekendTrend(weekend_effect=700,direction=down)",
            "positivity_rate:SinusoidalTrend(amplitude=8,freq=1000,phase=-24)+LinearTrend(offset=15,slope=0)+ARNoiseTrend(decay=0.98,noise_std=0.1)+WeekendTrend(weekend_effect=2.0,direction=down)",
            "death_rate:SinusoidalTrend(amplitude=1.5,freq=1000,phase=-96)+LinearTrend(offset=4.0,slope=0)+ARNoiseTrend(decay=0.98,noise_std=0.015)+WeekendTrend(weekend_effect=0.8,direction=down)",
            "icu_occupancy:SinusoidalTrend(amplitude=3.5,freq=1000,phase=-72)+LinearTrend(offset=8.0,slope=0)+ARNoiseTrend(decay=0.98,noise_std=0.04)+WeekendTrend(weekend_effect=0.8,direction=down)",
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
