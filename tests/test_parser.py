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
    
    config = load_preset("daily-sales")
    assert isinstance(config, PresetConfig)
    assert "product:A,B,C,D" in config.dimensions
    assert "sales:LinearTrend(slope=30)+WeekendTrend(weekend_effect=100)" in config.metrics

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
