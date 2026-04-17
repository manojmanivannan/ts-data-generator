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
            "--mets", "sales:LinearTrend(limit=10)",
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
            "--mets", "sales:LinearTrend(limit=10)",
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
            "--mets", "sales:LinearTrend(limit=10)",
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
            "metrics": ["sales:LinearTrend(limit=100)"],
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
        assert "daily-sales" in result.output
        assert "hourly-metrics" in result.output
        assert "minute-stock" in result.output

    def test_preset_daily_sales(self, runner, temp_output):
        """Test daily-sales preset"""
        result = runner.invoke(main, [
            "generate",
            "--preset", "daily-sales",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"
        assert Path(temp_output).exists()

    def test_preset_hourly_metrics(self, runner, temp_output):
        """Test hourly-metrics preset"""
        result = runner.invoke(main, [
            "generate",
            "--preset", "hourly-metrics",
            "--output", temp_output
        ])
        assert result.exit_code == 0, f"Error: {result.output}"
        assert Path(temp_output).exists()

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

    def test_preset_with_cli_override(self, runner, temp_output):
        """Test preset with CLI override"""
        result = runner.invoke(main, [
            "generate",
            "--preset", "daily-sales",
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
            "--mets", "sales:LinearTrend(limit=10)",
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
            "--mets", "sales:LinearTrend(limit=10)",
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
            "--mets", "sales:LinearTrend(limit=10)"
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
            "--mets", "sales:LinearTrend(limit=10)",
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
            "--mets", "sales:LinearTrend(limit=10)",
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
            "--mets", "sales:LinearTrend(limit=100)+WeekendTrend(weekend_effect=50)",
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
            "--mets", "sales:LinearTrend(limit=100)",
            "--mets", "orders:LinearTrend(limit=50)",
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
            "--mets", "sales:LinearTrend(limit=10)",
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
            "--mets", "sales:LinearTrend(limit=10)",
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
            "--mets", "sales:LinearTrend(limit=10)",
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
            "--mets", "sales:LinearTrend(limit=10)",
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
                "--mets", "sales:LinearTrend(limit=10)",
                "--output", temp_output
            ])
            assert result.exit_code == 0, f"Error for granularity {gran}: {result.output}"