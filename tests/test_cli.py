"""
Tests for the CLI module
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from ts_data_generator.cli import main, PRESETS


class TestCLIBasics:
    """Basic CLI tests"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_help_command(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Generate synthetic time series data" in result.output

    def test_generate_help(self, runner):
        result = runner.invoke(main, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--start" in result.output
        assert "--granularity" in result.output


class TestSmartDefaults:
    """Tests for smart defaults (name:values -> random_choice)"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_shorthand_dimension_syntax(self, runner, temp_output):
        """Test that name:values defaults to random_choice"""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "product:A,B,C",
            "--mets", "sales:LinearTrend(slope=20)",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"
        assert Path(temp_output).exists()
        content = Path(temp_output).read_text()
        assert "product" in content
        assert "sales" in content

    def test_full_dimension_syntax(self, runner, temp_output):
        """Test full syntax name:function:values still works"""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "product:random_choice:A,B,C",
            "--mets", "sales:LinearTrend(slope=20)",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"
        assert Path(temp_output).exists()

    def test_multiple_dimensions_with_shorthand(self, runner, temp_output):
        """Test multiple dimensions with shorthand"""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "product:A,B,C",
            "--dims", "region:X,Y,Z",
            "--mets", "sales:LinearTrend(slope=20)",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"
        content = Path(temp_output).read_text()
        assert "product" in content
        assert "region" in content


class TestConfigFile:
    """Tests for JSON config file support"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def config_file(self, temp_output):
        config = {
            "start": "2019-01-01",
            "end": "2019-01-02",
            "granularity": "5min",
            "dimensions": ["product:random_choice:A,B,C"],
            "metrics": ["sales:LinearTrend(slope=30)"],
            "output": temp_output
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            f.flush()
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_config_file_basic(self, runner, temp_output, config_file):
        """Test basic config file loading"""
        result = runner.invoke(main, ["generate", "--config", config_file])
        assert result.exit_code == 0, f"Error: {result.output}"
        assert Path(temp_output).exists()

    def test_config_cli_override(self, runner, temp_output, config_file):
        """Test CLI args override config file"""
        result = runner.invoke(main, [
            "generate",
            "--config", config_file,
            "--end", "2019-01-03"
        ])
        assert result.exit_code == 0, f"Error: {result.output}"

    def test_config_missing_fields(self, runner):
        """Test config with missing required fields"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"start": "2019-01-01"}, f)
            config_path = f.name

        try:
            result = runner.invoke(main, ["generate", "--config", config_path])
            assert result.exit_code != 0
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_config_invalid_json(self, runner):
        """Test config with invalid JSON"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            config_path = f.name

        try:
            result = runner.invoke(main, ["generate", "--config", config_path])
            assert result.exit_code != 0
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestPresets:
    """Tests for preset configurations"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_presets_command(self, runner):
        """Test listing presets"""
        result = runner.invoke(main, ["presets"])
        assert result.exit_code == 0
        assert "minute-stock" in result.output
        assert "economics-cycle" in result.output
        assert "electronics-reliability" in result.output

    def test_preset_minute_stock(self, runner, temp_output):
        """Test minute-stock preset"""
        result = runner.invoke(main, [
            "generate",
            "--preset", "minute-stock",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"
        assert Path(temp_output).exists()

    def test_preset_weekly_revenue(self, runner, temp_output):
        """Test weekly-revenue preset"""
        result = runner.invoke(main, [
            "generate",
            "--preset", "weekly-revenue",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"
        assert Path(temp_output).exists()

    def test_preset_monthly_recurring(self, runner, temp_output):
        """Test monthly-recurring preset"""
        result = runner.invoke(main, [
            "generate",
            "--preset", "monthly-recurring",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"
        assert Path(temp_output).exists()

    def test_preset_economics_cycle(self, runner, temp_output):
        """Test economics-cycle preset"""
        result = runner.invoke(main, [
            "generate",
            "--preset", "economics-cycle",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"
        assert Path(temp_output).exists()

    def test_preset_with_cli_override(self, runner, temp_output):
        """Test preset with CLI override"""
        result = runner.invoke(main, [
            "generate",
            "--preset", "minute-stock",
            "--output", temp_output,
            "--start", "2024-06-01",
            "--end", "2024-06-05"
        ])
        assert result.exit_code == 0, f"Error: {result.output}"

    def test_invalid_preset(self, runner):
        """Test invalid preset name"""
        result = runner.invoke(main, [
            "generate",
            "--preset", "invalid-preset",
            "--output", "/tmp/test.csv"
        ])
        assert result.exit_code != 0


class TestEnvironmentVariables:
    """Tests for environment variable support"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_env_variable_start(self, runner, temp_output, monkeypatch):
        """Test TSDATA_START environment variable"""
        monkeypatch.setenv("TSDATA_START", "2019-01-01")
        result = runner.invoke(main, [
            "generate",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "product:A,B",
            "--mets", "sales:LinearTrend(slope=20)",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"

    def test_env_variable_granularity(self, runner, temp_output, monkeypatch):
        """Test TSDATA_GRANULARITY environment variable"""
        monkeypatch.setenv("TSDATA_GRANULARITY", "h")
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--dims", "product:A,B",
            "--mets", "sales:LinearTrend(slope=20)",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"

    def test_env_variable_output(self, runner, temp_output, monkeypatch):
        """Test TSDATA_OUTPUT environment variable"""
        monkeypatch.setenv("TSDATA_OUTPUT", temp_output)
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "product:A,B",
            "--mets", "sales:LinearTrend(slope=20)"
        ])
        assert result.exit_code == 0, f"Error: {result.output}"
        assert Path(temp_output).exists()


class TestErrorHandling:
    """Tests for error handling"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_invalid_dimension_function(self, runner, temp_output):
        """Test invalid dimension function name"""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "product:invalid_function:A,B",
            "--mets", "sales:LinearTrend(slope=20)",
            "--output", temp_output
        ])
        assert result.exit_code != 0
        assert "Invalid" in result.output or "Unknown" in result.output

    def test_invalid_trend_function(self, runner, temp_output):
        """Test invalid trend function name"""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "product:A,B",
            "--mets", "sales:InvalidTrend(param=10)",
            "--output", temp_output
        ])
        assert result.exit_code != 0
        assert "Invalid" in result.output or "Unknown" in result.output

    def test_invalid_trend_format(self, runner, temp_output):
        """Test invalid trend format"""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "product:A,B",
            "--mets", "sales:not_a_trend",
            "--output", temp_output
        ])
        assert result.exit_code != 0

    def test_invalid_output_extension(self, runner):
        """Test invalid output file extension"""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "product:A,B",
            "--mets", "sales:LinearTrend(slope=20)",
            "--output", "/tmp/data.txt"
        ])
        assert result.exit_code != 0

    def test_missing_required_args(self, runner):
        """Test missing required arguments"""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01"
        ])
        assert result.exit_code == 0  # Shows help when no args


class TestListCommands:
    """Tests for listing commands"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_dimensions_command(self, runner):
        """Test listing dimension functions"""
        result = runner.invoke(main, ["dimensions"])
        assert result.exit_code == 0
        assert "random_choice" in result.output
        assert "constant" in result.output

    def test_metrics_command(self, runner):
        """Test listing trend functions"""
        result = runner.invoke(main, ["metrics"])
        assert result.exit_code == 0
        assert "LinearTrend" in result.output


class TestMultipleTrends:
    """Tests for multiple trends"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_multiple_trends_additive(self, runner, temp_output):
        """Test multiple trends with + separator"""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "product:A,B",
            "--mets", "sales:LinearTrend(slope=30)+WeekendTrend(weekend_effect=50)",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"
        assert Path(temp_output).exists()

    def test_multiple_metrics(self, runner, temp_output):
        """Test multiple metrics"""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "product:A,B",
            "--mets", "sales:LinearTrend(slope=30)",
            "--mets", "orders:LinearTrend(slope=30)",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"
        content = Path(temp_output).read_text()
        assert "sales" in content
        assert "orders" in content


class TestNumericValues:
    """Tests for numeric value handling"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_integer_values(self, runner, temp_output):
        """Test integer values in dimension"""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "id:random_int:1,100",
            "--mets", "sales:LinearTrend(slope=20)",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"

    def test_float_values(self, runner, temp_output):
        """Test float values in dimension"""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "price:random_float:10.5,100.5",
            "--mets", "sales:LinearTrend(slope=20)",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"


class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_constant_dimension(self, runner, temp_output):
        """Test constant dimension"""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "source:constant:main",
            "--mets", "sales:LinearTrend(slope=20)",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"
        content = Path(temp_output).read_text()
        # All values should be 'main'
        lines = content.strip().split("\n")
        for line in lines[1:]:  # Skip header
            if "main" not in line:
                assert "main" in line or "datetime" in line  # Header or value

    def test_single_value_dimension(self, runner, temp_output):
        """Test single value dimension"""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "5min",
            "--dims", "product:A",
            "--mets", "sales:LinearTrend(slope=20)",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"

    def test_all_granularities(self, runner, temp_output):
        """Test all granularity options"""
        # Test supported granularities (W, ME, Y have limitations with trends)
        granularities = ["s", "min", "5min", "h", "D"]
        for gran in granularities:
            result = runner.invoke(main, [
                "generate",
                "--start", "2019-01-01",
                "--end", "2019-01-02",
                "--granularity", gran,
                "--dims", "product:A,B",
                "--mets", "sales:LinearTrend(slope=20)",
                "--output", temp_output
            ])
            assert result.exit_code == 0, f"Error for granularity {gran}: {result.output}"


class TestSeedFlag:
    """Tests for --seed flag determinism."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def temp_output2(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_seed_produces_deterministic_output(self, runner, temp_output, temp_output2):
        """Two runs with --seed 42 should produce identical output."""
        base_args = [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "h",
            "--dims", "product:constant:A",
            "--mets", "sales:LinearTrend(slope=30)",
            "--seed", "42",
        ]

        result1 = runner.invoke(main, base_args + ["--output", temp_output])
        assert result1.exit_code == 0, f"Error: {result1.output}"

        result2 = runner.invoke(main, base_args + ["--output", temp_output2])
        assert result2.exit_code == 0, f"Error: {result2.output}"

        content1 = Path(temp_output).read_text()
        content2 = Path(temp_output2).read_text()
        assert content1 == content2

    def test_different_seeds_produce_different_output(self, runner, temp_output, temp_output2):
        """Different seeds should produce different output when trends use RNG."""
        args1 = [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "h",
            "--dims", "product:constant:A",
            "--mets", "sales:StockTrend(amplitude=5,noise_level=0.5)",
            "--seed", "42",
            "--output", temp_output,
        ]
        args2 = [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "h",
            "--dims", "product:constant:A",
            "--mets", "sales:StockTrend(amplitude=5,noise_level=0.5)",
            "--seed", "99",
            "--output", temp_output2,
        ]

        result1 = runner.invoke(main, args1)
        assert result1.exit_code == 0, f"Error: {result1.output}"

        result2 = runner.invoke(main, args2)
        assert result2.exit_code == 0, f"Error: {result2.output}"

        content1 = Path(temp_output).read_text()
        content2 = Path(temp_output2).read_text()
        assert content1 != content2


class TestAnomaliesFlag:
    """Tests for --anomalies CLI flag."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_point_anomaly_additive(self, runner, temp_output):
        """PointAnomaly with prob=1.0 adds magnitude to every value."""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "h",
            "--dims", "product:constant:A",
            "--mets", "sales:LinearTrend(slope=30)",
            "--anomalies", "sales:PointAnomaly(probability=1.0,magnitude=5,mode=additive)",
            "--seed", "42",
            "--output", temp_output,
        ])
        assert result.exit_code == 0, f"Error: {result.output}"

        import pandas as pd
        df = pd.read_csv(temp_output, index_col=0)
        # With no anomaly, LinearTrend(slope=30) over 24 hours produces
        # values from 0 to ~100. With additive magnitude 5, each = trend + 5.
        # LinearTrend(slope=30) uses tan(30°) ≈ 0.577 per time unit.
        assert len(df) == 25  # 24h + 1 (inclusive)
        assert all(df["sales"] > 0)
        # The anomaly is additive: min value should be at least 5
        assert df["sales"].min() >= 5

    def test_point_anomaly_replacement(self, runner, temp_output):
        """PointAnomaly with mode=replacement replaces values."""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "h",
            "--dims", "product:constant:A",
            "--mets", "sales:LinearTrend(slope=30)",
            "--anomalies", "sales:PointAnomaly(probability=1.0,magnitude=999,mode=replacement)",
            "--seed", "42",
            "--output", temp_output,
        ])
        assert result.exit_code == 0, f"Error: {result.output}"

        import pandas as pd
        df = pd.read_csv(temp_output, index_col=0)
        # All values should be exactly 999 (replacement with scalar magnitude)
        assert (df["sales"] == 999).all()

    def test_missing_data_random(self, runner, temp_output):
        """MissingData random mode with prob=1.0 makes all values NaN."""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "h",
            "--dims", "product:constant:A",
            "--mets", "sales:LinearTrend(slope=30)",
            "--anomalies", "sales:MissingData(probability=1.0)",
            "--seed", "42",
            "--output", temp_output,
        ])
        assert result.exit_code == 0, f"Error: {result.output}"

        import pandas as pd
        df = pd.read_csv(temp_output, index_col=0)
        assert df["sales"].isna().all()

    def test_missing_data_burst(self, runner, temp_output):
        """MissingData burst mode with burst_probability=1.0 creates NaN blocks."""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "h",
            "--dims", "product:constant:A",
            "--mets", "sales:LinearTrend(slope=30)",
            "--anomalies",
            "sales:MissingData(mode=burst,burst_probability=1.0,min_length=3,max_length=10)",
            "--seed", "42",
            "--output", temp_output,
        ])
        assert result.exit_code == 0, f"Error: {result.output}"

        import pandas as pd
        df = pd.read_csv(temp_output, index_col=0)
        # With burst_probability=1.0, bursts are triggered immediately,
        # so there should be NaN values present
        assert df["sales"].isna().any()

    def test_concept_drift(self, runner, temp_output):
        """ConceptDrift shifts values toward target distribution."""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "h",
            "--dims", "product:constant:A",
            "--mets", "sales:LinearTrend(slope=30)",
            "--anomalies",
            "sales:ConceptDrift(start_timestamp=2019-01-01T00:00:00,transition_window=18000,target_mean=100,"
            "target_std=2,hold_duration=360000,restore=false)",
            "--seed", "42",
            "--output", temp_output,
        ])
        assert result.exit_code == 0, f"Error: {result.output}"

        import pandas as pd
        df = pd.read_csv(temp_output, index_col=0)
        # After transition window (5), hold region should be near target_mean=100
        hold_values = df["sales"].iloc[6:]  # skip transition
        assert abs(hold_values.mean() - 100) < 5

    def test_multi_segment_concept_drift(self, runner, temp_output):
        """Repeating --anomalies for same metric merges ConceptDrift segments."""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "h",
            "--dims", "product:constant:A",
            "--mets", "sales:LinearTrend(slope=30)",
            "--anomalies",
            "sales:ConceptDrift(start_timestamp=2019-01-01T00:00:00,transition_window=10800,"
            "target_mean=50,target_std=1,hold_duration=36000,restore=false)",
            "--anomalies",
            "sales:ConceptDrift(start_timestamp=2019-01-01T15:00:00,transition_window=10800,"
            "target_mean=200,target_std=1,hold_duration=36000,restore=false)",
            "--seed", "42",
            "--output", temp_output,
        ])
        assert result.exit_code == 0, f"Error: {result.output}"

        import pandas as pd
        df = pd.read_csv(temp_output, index_col=0)
        # First segment: indices 3-12 -> ~50
        seg1 = df["sales"].iloc[3:13]
        # Second segment: indices 18-24 -> ~200
        seg2 = df["sales"].iloc[18:]
        assert abs(seg1.mean() - 50) < 10
        assert abs(seg2.mean() - 200) < 10

    def test_repeating_anomalies_multiple_types(self, runner, temp_output):
        """Repeating --anomalies for same metric applies specs in order."""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "h",
            "--dims", "product:constant:A",
            "--mets", "sales:LinearTrend(slope=30)",
            "--anomalies", "sales:PointAnomaly(probability=1.0,magnitude=0,mode=replacement)",
            "--anomalies", "sales:MissingData(probability=1.0)",
            "--seed", "42",
            "--output", temp_output,
        ])
        assert result.exit_code == 0, f"Error: {result.output}"

        import pandas as pd
        df = pd.read_csv(temp_output, index_col=0)
        # PointAnomaly sets all to 0, then MissingData sets all to NaN
        # MissingData runs last so all values should be NaN
        assert df["sales"].isna().all()

    def test_anomalies_with_metric_from_mets(self, runner, temp_output):
        """--anomalies links to metric defined via --mets."""
        result = runner.invoke(main, [
            "generate",
            "--start", "2019-01-01",
            "--end", "2019-01-02",
            "--granularity", "h",
            "--dims", "product:constant:A",
            "--mets", "sales:LinearTrend(slope=30)",
            "--mets", "orders:LinearTrend(slope=30)",
            "--anomalies", "sales:PointAnomaly(probability=1.0,magnitude=5,mode=additive)",
            "--seed", "42",
            "--output", temp_output,
        ])
        assert result.exit_code == 0, f"Error: {result.output}"

        import pandas as pd
        df = pd.read_csv(temp_output, index_col=0)
        assert "sales" in df.columns
        assert "orders" in df.columns
        # sales has anomalies, orders does not
        assert df["sales"].min() >= 5  # additive anomaly on every point


class TestConfigFileAnomalies:
    """Tests for anomalies field in JSON config files."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_config_with_anomalies(self, runner, temp_output):
        """Config file with anomalies array generates data with anomalies."""
        config = {
            "start": "2019-01-01",
            "end": "2019-01-02",
            "granularity": "h",
            "dimensions": ["product:constant:A"],
            "metrics": ["sales:LinearTrend(slope=30)"],
            "anomalies": ["sales:PointAnomaly(probability=1.0,magnitude=999,mode=replacement)"],
            "output": temp_output,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            config_path = f.name

        try:
            result = runner.invoke(main, ["generate", "--config", config_path])
            assert result.exit_code == 0, f"Error: {result.output}"

            import pandas as pd
            df = pd.read_csv(temp_output, index_col=0)
            assert (df["sales"] == 999).all()
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_config_with_seed_and_anomalies(self, runner, temp_output):
        """Config file with seed and anomalies produces deterministic output."""
        config = {
            "start": "2019-01-01",
            "end": "2019-01-02",
            "granularity": "h",
            "dimensions": ["product:constant:A"],
            "metrics": ["sales:LinearTrend(slope=30)"],
            "anomalies": [],
            "output": temp_output,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            config_path = f.name

        try:
            result = runner.invoke(main, [
                "generate", "--config", config_path, "--seed", "42",
            ])
            assert result.exit_code == 0, f"Error: {result.output}"
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestShowSampleConfig:
    """Tests for --show-sample-config flag."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_show_sample_config_outputs_valid_json(self, runner):
        """--show-sample-config should print valid JSON with expected keys."""
        result = runner.invoke(main, ["generate", "--show-sample-config"])
        assert result.exit_code == 0, f"Error: {result.output}"

        data = json.loads(result.output)
        assert "start" in data
        assert "end" in data
        assert "granularity" in data
        assert "dimensions" in data
        assert "metrics" in data
        assert "anomalies" in data
        assert isinstance(data["dimensions"], list)
        assert isinstance(data["metrics"], list)
        assert isinstance(data["anomalies"], list)

    @pytest.fixture
    def temp_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_show_sample_config_round_trip(self, runner, temp_output):
        """Saving sample config output and using it with --config should generate data."""
        result = runner.invoke(main, ["generate", "--show-sample-config"])
        assert result.exit_code == 0

        config_data = json.loads(result.output)
        config_data["output"] = temp_output

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            gen_result = runner.invoke(main, ["generate", "--config", config_path])
            assert gen_result.exit_code == 0, f"Error: {gen_result.output}"
            assert Path(temp_output).exists()
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_show_sample_config_exits_without_generation(self, runner):
        """--show-sample-config should not attempt data generation."""
        result = runner.invoke(main, ["generate", "--show-sample-config"])
        assert result.exit_code == 0
        # Should not contain the "Generated" message that data generation produces
        assert "Generated" not in result.output


class TestExpandDimensionsFlag:
    """Tests for the --expand-dimensions CLI flag (#55)."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    @staticmethod
    def _row_count(path: str) -> int:
        """Data rows in a generated CSV (excludes the single header row)."""
        content = Path(path).read_text()
        return len(content.strip().splitlines()) - 1

    # 4 daily timestamps x one random_choice dim with 3 values.
    BASE = [
        "generate",
        "--start", "2019-01-01",
        "--end", "2019-01-04",
        "--granularity", "D",
        "--dims", "product:random_choice:A,B,C",
        "--mets", "sales:LinearTrend(slope=1)",
    ]

    def _config(self, temp_output: str, expand: bool | None = None) -> str:
        config = {
            "start": "2019-01-01",
            "end": "2019-01-04",
            "granularity": "D",
            "dimensions": ["product:random_choice:A,B,C"],
            "metrics": ["sales:LinearTrend(slope=1)"],
            "output": temp_output,
        }
        if expand is not None:
            config["expand_dimensions"] = expand
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(config, f)
        f.flush()
        f.close()
        return f.name

    def test_flag_appears_in_help(self, runner):
        result = runner.invoke(main, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--expand-dimensions" in result.output
        assert "--no-expand-dimensions" in result.output

    def test_flag_off_by_default(self, runner, temp_output):
        result = runner.invoke(main, self.BASE + ["--output", temp_output])
        assert result.exit_code == 0, f"Error: {result.output}"
        assert self._row_count(temp_output) == 4  # one row per timestamp

    def test_flag_on_expands_rows(self, runner, temp_output):
        result = runner.invoke(main, self.BASE + ["--expand-dimensions", "--output", temp_output])
        assert result.exit_code == 0, f"Error: {result.output}"
        assert self._row_count(temp_output) == 12  # 4 timestamps x 3 products

    def test_no_expand_flag_explicit_off(self, runner, temp_output):
        result = runner.invoke(
            main, self.BASE + ["--no-expand-dimensions", "--output", temp_output]
        )
        assert result.exit_code == 0, f"Error: {result.output}"
        assert self._row_count(temp_output) == 4

    def test_config_file_expand_true(self, runner, temp_output):
        path = self._config(temp_output, expand=True)
        try:
            result = runner.invoke(main, ["generate", "--config", path])
            assert result.exit_code == 0, f"Error: {result.output}"
            assert self._row_count(temp_output) == 12
        finally:
            Path(path).unlink(missing_ok=True)

    def test_config_false_no_flag_not_expanded(self, runner, temp_output):
        path = self._config(temp_output, expand=False)
        try:
            result = runner.invoke(main, ["generate", "--config", path])
            assert result.exit_code == 0, f"Error: {result.output}"
            assert self._row_count(temp_output) == 4
        finally:
            Path(path).unlink(missing_ok=True)

    def test_cli_flag_overrides_config_true(self, runner, temp_output):
        # config says false, CLI flag says true -> expanded (CLI > config).
        path = self._config(temp_output, expand=False)
        try:
            result = runner.invoke(main, ["generate", "--config", path, "--expand-dimensions"])
            assert result.exit_code == 0, f"Error: {result.output}"
            assert self._row_count(temp_output) == 12
        finally:
            Path(path).unlink(missing_ok=True)

    def test_cli_flag_overrides_config_false(self, runner, temp_output):
        # config says true, CLI flag says false -> not expanded (CLI > config).
        path = self._config(temp_output, expand=True)
        try:
            result = runner.invoke(main, ["generate", "--config", path, "--no-expand-dimensions"])
            assert result.exit_code == 0, f"Error: {result.output}"
            assert self._row_count(temp_output) == 4
        finally:
            Path(path).unlink(missing_ok=True)

    def test_config_expand_overrides_preset(self, runner, temp_output):
        # Both --config (expand=True) and --preset given: config's expand value wins
        # over the preset's False. Asserted as a ratio so it holds regardless of the
        # pre-existing config/preset date+granularity interaction.
        path_off = self._config(temp_output, expand=False)
        temp_on = temp_output + ".on.csv"
        path_on = self._config(temp_on, expand=True)
        try:
            r_off = runner.invoke(
                main,
                ["generate", "--config", path_off, "--preset", "weekly-revenue",
                 "--output", temp_output],
            )
            assert r_off.exit_code == 0, f"Error: {r_off.output}"
            off = self._row_count(temp_output)

            r_on = runner.invoke(
                main,
                ["generate", "--config", path_on, "--preset", "weekly-revenue",
                 "--output", temp_on],
            )
            assert r_on.exit_code == 0, f"Error: {r_on.output}"
            on = self._row_count(temp_on)
            # config's product dim has 3 values -> expansion triples the rows.
            assert on == off * 3
        finally:
            Path(path_off).unlink(missing_ok=True)
            Path(path_on).unlink(missing_ok=True)
            Path(temp_on).unlink(missing_ok=True)

    def test_preset_default_not_expanded_flag_expands(self, runner, temp_output):
        # weekly-revenue preset has one enumerable dim (ordered_choice, 3 values)
        # and carries expand_dimensions=False. Without the flag: not expanded.
        result_off = runner.invoke(
            main, ["generate", "--preset", "weekly-revenue", "--output", temp_output]
        )
        assert result_off.exit_code == 0, f"Error: {result_off.output}"
        off_rows = self._row_count(temp_output)

        temp_on = temp_output + ".on.csv"
        result_on = runner.invoke(
            main,
            ["generate", "--preset", "weekly-revenue", "--expand-dimensions", "--output", temp_on],
        )
        assert result_on.exit_code == 0, f"Error: {result_on.output}"
        on_rows = self._row_count(temp_on)
        Path(temp_on).unlink(missing_ok=True)

        # 3 department values -> expanded rows = off rows x 3 (preset default is false).
        assert on_rows == off_rows * 3

    def test_non_enumerable_dim_with_flag_errors(self, runner, temp_output):
        result = runner.invoke(
            main,
            [
                "generate",
                "--start", "2019-01-01",
                "--end", "2019-01-02",
                "--granularity", "D",
                "--dims", "port:random_int:1,100",
                "--mets", "sales:LinearTrend(slope=1)",
                "--expand-dimensions",
                "--output", temp_output,
            ],
        )
        assert result.exit_code != 0
        # The clear ExpandError surfaces as the CLI's exception.
        from ts_data_generator.exceptions import ExpandError

        assert isinstance(result.exception, ExpandError)
        assert "cannot be expanded" in str(result.exception)

    def test_cli_presets_all_carry_false(self):
        for name, cfg in PRESETS.items():
            assert cfg.get("expand_dimensions") is False, name

    def test_parser_presets_all_carry_false(self):
        from ts_data_generator.schema.parser import PRESETS as PARSER_PRESETS

        for name, cfg in PARSER_PRESETS.items():
            assert cfg.expand_dimensions is False, name

    def test_generator_config_default_false(self):
        from ts_data_generator.cli import GeneratorConfig

        gc = GeneratorConfig(
            start="2019-01-01", end="2019-01-02", granularity="D", output="x.csv"
        )
        assert gc.expand_dimensions is False

    def test_generator_config_accepts_true(self):
        from ts_data_generator.cli import GeneratorConfig

        gc = GeneratorConfig(
            start="2019-01-01",
            end="2019-01-02",
            granularity="D",
            output="x.csv",
            expand_dimensions=True,
        )
        assert gc.expand_dimensions is True

    def test_sample_config_carries_field(self, runner):
        result = runner.invoke(main, ["generate", "--show-sample-config"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "expand_dimensions" in data
        assert data["expand_dimensions"] is False

    # -- per-dimension expand control via modern string-spec (#57) ---------

    def test_per_dim_expand_false_opts_out(self, runner, temp_output):
        # Modern `name=fn(args),expand=false` form: region opts out of the
        # product, so with the global flag on only env expands -> 3 x 2 = 6 rows
        # (not 3 x 2 x 2 = 12).
        result = runner.invoke(
            main,
            [
                "generate",
                "--start", "2024-01-01",
                "--end", "2024-01-03",
                "--granularity", "D",
                "--dims", "region=random_choice(US,EU),expand=false;env=ordered_choice(prod,dev)",
                "--mets", "sales:LinearTrend(offset=10)",
                "--expand-dimensions",
                "--output", temp_output,
            ],
        )
        assert result.exit_code == 0, f"Error: {result.output}"
        assert self._row_count(temp_output) == 6

    def test_per_dim_expand_true_forces_expansion_when_global_off(self, runner, temp_output):
        # `expand=true` forces region into the product even without --expand-dimensions.
        result = runner.invoke(
            main,
            [
                "generate",
                "--start", "2024-01-01",
                "--end", "2024-01-03",
                "--granularity", "D",
                "--dims", "region=random_choice(US,EU),expand=true",
                "--mets", "sales:LinearTrend(offset=10)",
                "--output", temp_output,
            ],
        )
        assert result.exit_code == 0, f"Error: {result.output}"
        assert self._row_count(temp_output) == 6  # 3 timestamps x 2 regions

    def test_per_dim_expand_false_escape_hatch_for_non_enumerable(self, runner, temp_output):
        # A non-enumerable dim marked expand=false is excluded from the product
        # and does NOT error with the global flag on.
        result = runner.invoke(
            main,
            [
                "generate",
                "--start", "2024-01-01",
                "--end", "2024-01-03",
                "--granularity", "D",
                "--dims", "port=random_int(1,100),expand=false;region=random_choice(US,EU)",
                "--mets", "sales:LinearTrend(offset=10)",
                "--expand-dimensions",
                "--output", temp_output,
            ],
        )
        assert result.exit_code == 0, f"Error: {result.output}"
        assert self._row_count(temp_output) == 6  # 3 x 2 regions; port within-series


class TestParseDimensionSpecExpand:
    """Unit tests for the CLI ``_parse_dimension_spec`` per-dim expand (#57) and weights."""

    def test_modern_form_expand_true(self):
        from ts_data_generator.cli import _parse_dimension_spec

        name, func_name, values, expand, weights = _parse_dimension_spec(
            "region=random_choice(US,EU),expand=true"
        )
        assert name == "region"
        assert func_name == "random_choice"
        assert expand is True
        assert weights is None

    def test_modern_form_expand_false(self):
        from ts_data_generator.cli import _parse_dimension_spec

        _, _, _, expand, _ = _parse_dimension_spec("port=random_int(1,100),expand=false")
        assert expand is False

    def test_modern_form_default_none(self):
        from ts_data_generator.cli import _parse_dimension_spec

        _, _, _, expand, weights = _parse_dimension_spec("region=random_choice(US,EU)")
        assert expand is None
        assert weights is None

    def test_legacy_colon_form_no_expand_support(self):
        from ts_data_generator.cli import _parse_dimension_spec

        _, _, _, expand, weights = _parse_dimension_spec("region:random_choice:US,EU")
        assert expand is None
        assert weights is None

    def test_modern_form_modifier_not_leaked_into_values(self):
        from ts_data_generator.cli import _parse_dimension_spec

        _, _, values, expand, _ = _parse_dimension_spec(
            "region=random_choice(US,EU),expand=true"
        )
        assert expand is True
        assert "expand" not in [str(v) for v in values]

    def test_modern_form_weights_parsing(self):
        from ts_data_generator.cli import _parse_dimension_spec

        name, func_name, values, expand, weights = _parse_dimension_spec(
            "region=random_choice(US,EU),weights={US:5.0,EU:2.0}"
        )
        assert name == "region"
        assert func_name == "random_choice"
        assert values == ("US", "EU")
        assert weights == {"US": 5.0, "EU": 2.0}

    def test_modern_form_weights_and_expand_combined(self):
        from ts_data_generator.cli import _parse_dimension_spec

        _, _, _, expand, weights = _parse_dimension_spec(
            "region=random_choice(US,EU),weights={US:5,EU:2},expand=true"
        )
        assert expand is True
        assert weights == {"US": 5.0, "EU": 2.0}


class TestCLIDimensionScaling:
    """CLI integration tests for weights and scale-variance."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_cli_explicit_weights(self, runner, temp_output):
        import pandas as pd

        result = runner.invoke(
            main,
            [
                "generate",
                "--start", "2024-01-01",
                "--end", "2024-01-02",
                "--granularity", "D",
                "--dims", "region=ordered_choice(US,EU),weights={US:5.0,EU:2.0}",
                "--mets", "sales:LinearTrend(offset=10,slope=0,noise_level=0)",
                "--expand-dimensions",
                "--seed", "42",
                "--output", temp_output,
            ],
        )
        assert result.exit_code == 0, f"Error: {result.output}"
        df = pd.read_csv(temp_output)
        us_sales = df[df["region"] == "US"]["sales"].to_numpy()
        eu_sales = df[df["region"] == "EU"]["sales"].to_numpy()
        assert (us_sales == 50.0).all()
        assert (eu_sales == 20.0).all()

    def test_cli_scale_variance(self, runner, temp_output):
        import pandas as pd

        result = runner.invoke(
            main,
            [
                "generate",
                "--start", "2024-01-01",
                "--end", "2024-01-02",
                "--granularity", "D",
                "--dims", "region=ordered_choice(US,EU)",
                "--mets", "sales:LinearTrend(offset=100,slope=0,noise_level=0)",
                "--expand-dimensions",
                "--scale-variance", "0.5",
                "--seed", "42",
                "--output", temp_output,
            ],
        )
        assert result.exit_code == 0, f"Error: {result.output}"
        df = pd.read_csv(temp_output)
        us_sales = df[df["region"] == "US"]["sales"].to_numpy()
        eu_sales = df[df["region"] == "EU"]["sales"].to_numpy()
        assert us_sales[0] != eu_sales[0]


class TestAggregateBySubset:
    """Tests for --aggregate paired with --by (subset dimension rollup)."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def temp_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_aggregate_rolls_up_to_subset(self, runner, temp_output):
        """--aggregate D --by region keeps region, drops the other dimension."""
        import pandas as pd

        result = runner.invoke(
            main,
            [
                "generate",
                "--start", "2024-01-01",
                "--end", "2024-01-03",
                "--granularity", "h",
                "--dims", "region:US,EU",
                "--dims", "env:prod,dev",
                "--mets", "sales:LinearTrend(offset=10,slope=0,noise_level=0)",
                "--expand-dimensions",
                "--seed", "42",
                "--aggregate", "D",
                "--by", "region",
                "--output", temp_output,
            ],
        )
        assert result.exit_code == 0, f"Error: {result.output}"
        df = pd.read_csv(temp_output)
        assert "region" in df.columns
        assert "env" not in df.columns
        # 3 days x 2 regions = 6 rows
        assert len(df) == 6

    def test_aggregate_without_by_keeps_all_dims(self, runner, temp_output):
        """--aggregate without --by keeps every dimension (historical behavior)."""
        import pandas as pd

        result = runner.invoke(
            main,
            [
                "generate",
                "--start", "2024-01-01",
                "--end", "2024-01-03",
                "--granularity", "h",
                "--dims", "region:US,EU",
                "--dims", "env:prod,dev",
                "--mets", "sales:LinearTrend(offset=10,slope=0,noise_level=0)",
                "--expand-dimensions",
                "--seed", "42",
                "--aggregate", "D",
                "--output", temp_output,
            ],
        )
        assert result.exit_code == 0, f"Error: {result.output}"
        df = pd.read_csv(temp_output)
        assert "region" in df.columns
        assert "env" in df.columns
        # 3 days x 2 regions x 2 envs = 12 rows
        assert len(df) == 12

    def test_aggregate_finer_granularity_errors(self, runner, temp_output):
        """--aggregate to a finer granularity is rejected."""
        result = runner.invoke(
            main,
            [
                "generate",
                "--start", "2024-01-01",
                "--end", "2024-01-02",
                "--granularity", "h",
                "--dims", "region:US,EU",
                "--mets", "sales:LinearTrend(offset=10)",
                "--aggregate", "5min",
                "--output", temp_output,
            ],
        )
        assert result.exit_code != 0
        assert "finer granularity" in result.output

    def test_aggregate_by_unknown_column_errors(self, runner, temp_output):
        """--by naming a non-dimension column is rejected."""
        result = runner.invoke(
            main,
            [
                "generate",
                "--start", "2024-01-01",
                "--end", "2024-01-03",
                "--granularity", "h",
                "--dims", "region:US,EU",
                "--mets", "sales:LinearTrend(offset=10,slope=0,noise_level=0)",
                "--expand-dimensions",
                "--seed", "42",
                "--aggregate", "D",
                "--by", "nonexistent",
                "--output", temp_output,
            ],
        )
        assert result.exit_code != 0
        assert "non-groupable" in result.output
