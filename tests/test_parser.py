import pytest
from ts_data_generator.schema.types import DimensionSpec, TrendSpec, AnomalySpec, PresetConfig

# We will TDD the new parser functions here

def test_parse_dimension_spec_returns_dataclass():
    from ts_data_generator.schema.parser import parse_dimension_spec
    
    spec = "location=random_choice(New York,London)"
    result = parse_dimension_spec(spec)
    
    assert isinstance(result, DimensionSpec)
    assert result.name == "location"
    assert result.function_name == "random_choice"
    assert result.args == ("New York", "London")

def test_parse_trend_spec_returns_dataclass():
    from ts_data_generator.schema.parser import parse_trend_spec
    
    spec = "linear(slope=2.5)"
    result = parse_trend_spec(spec)
    
    assert isinstance(result, TrendSpec)
    assert result.name == "linear"
    assert result.kwargs == {"slope": 2.5}


def test_parse_trend_spec_with_bracket_lists():
    from ts_data_generator.schema.parser import parse_trend_spec

    spec = "MarkovTrend(states=[safe,elevated,danger],values=[0.1,1.5,5.0],stickiness=0.95,noise_std=0.1)"
    result = parse_trend_spec(spec)

    assert isinstance(result, TrendSpec)
    assert result.name == "MarkovTrend"
    assert result.kwargs["states"] == ["safe", "elevated", "danger"]
    assert result.kwargs["values"] == [0.1, 1.5, 5.0]
    assert result.kwargs["stickiness"] == 0.95
    assert result.kwargs["noise_std"] == 0.1

def test_load_preset():
    from ts_data_generator.schema.parser import load_preset
    
    config = load_preset("minute-stock")
    assert isinstance(config, PresetConfig)
    assert "ticker:AAPL,MSFT,GOOGL" in config.dimensions
    assert "price:StockTrend(noise_level=0.01)" in config.metrics

def test_apply_config_overrides():
    from ts_data_generator.schema.parser import apply_config_overrides
    
    base = PresetConfig(dimensions=["id=uuid"], metrics=["value:LinearTrend(slope=1)"], anomalies=[])
    overrides = {
        "dimensions": ("region=random_choice(US,EU)",),
        "metrics": (),
        "anomalies": ("point(magnitude=10)",)
    }
    
    result = apply_config_overrides(base, **overrides)
    assert isinstance(result, PresetConfig)
    assert "region=random_choice(US,EU)" in result.dimensions
    assert "id=uuid" not in result.dimensions # Overrides replace
    assert result.metrics == ["value:LinearTrend(slope=1)"] # Empty tuple means no override
    assert result.anomalies == ["point(magnitude=10)"]


def test_electronics_reliability_preset_uses_all_dimension_and_trend_features():
    from ts_data_generator.schema.parser import load_preset

    config = load_preset("electronics-reliability")

    expected_dimension_functions = [
        "auto_generate_name",
        "ordered_choice",
        "random_choice",
        "random_int",
        "random_float",
        "constant",
    ]
    expected_trends = [
        "LinearTrend",
        "SinusoidalTrend",
        "WeekendTrend",
        "HolidayTrend",
        "ARNoiseTrend",
        "MarkovTrend",
        "StockTrend",
    ]
    expected_anomalies = [
        "PointAnomaly",
        "MissingData",
        "ConceptDrift",
    ]

    dimensions_blob = " ".join(config.dimensions)
    metrics_blob = " ".join(config.metrics)
    anomalies_blob = " ".join(config.anomalies)

    for func_name in expected_dimension_functions:
        assert f":{func_name}:" in dimensions_blob

    for trend_name in expected_trends:
        assert trend_name in metrics_blob

    for anomaly_name in expected_anomalies:
        assert anomaly_name in anomalies_blob

    # Cover key anomaly feature variants expressible in DSL
    assert "mode=additive" in anomalies_blob
    assert "mode=replacement" in anomalies_blob
    assert "mode=random" in anomalies_blob
    assert "mode=burst" in anomalies_blob
    assert "restore=true" in anomalies_blob
    assert "restore=false" in anomalies_blob
