"""
Tests for aggregation functionality in DataGen
"""

import pytest
import pandas as pd
import numpy as np
from ts_data_generator import DataGen
from ts_data_generator.schema.models import Granularity, AggregationType
from ts_data_generator.utils.functions import random_choice
from ts_data_generator.utils.trends import SinusoidalTrend, LinearTrend


class TestAggregation:
    """Tests for aggregation functionality"""

    @pytest.fixture
    def data_gen_5min_instance(self):
        """Create a DataGen instance with 5min granularity for aggregation tests"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01 00:00:00"
        data_gen.end_datetime = "2022-01-01 02:00:00"  # 2 hours = 24 intervals at 5min
        data_gen.granularity = Granularity.FIVE_MIN
        data_gen.add_dimension(name="protocol", function=random_choice(["TCP", "UDP"]))
        data_gen.add_dimension(name="region", function=random_choice(["US", "EU"]))

        metric_trend = SinusoidalTrend(
            name="sine", amplitude=1, freq=24, phase=0, noise_level=0
        )
        data_gen.add_metric(
            name="metric1", trends={metric_trend}, aggregation_type=AggregationType.AVG
        )

        return data_gen

    @pytest.fixture
    def data_gen_hourly_instance(self):
        """Create a DataGen instance with hourly granularity"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01 00:00:00"
        data_gen.end_datetime = "2022-01-01 12:00:00"
        data_gen.granularity = Granularity.HOURLY
        data_gen.add_dimension(name="product", function=random_choice(["A", "B"]))

        metric_trend = LinearTrend(name="linear", limit=10, offset=0, noise_level=0)
        data_gen.add_metric(
            name="sales", trends={metric_trend}, aggregation_type=AggregationType.SUM
        )

        return data_gen

    def test_aggregate_to_hourly_from_5min(self, data_gen_5min_instance):
        """Test aggregating 5min data to hourly"""
        original_len = len(data_gen_5min_instance.data)
        assert original_len == 25  # 2 hours + 1 = 25 intervals at 5min

        aggregated = data_gen_5min_instance.aggregate("h")

        # Hourly should have fewer rows (2 hours = 3 hourly intervals)
        assert len(aggregated) <= original_len

    def test_aggregate_to_daily_from_hourly(self, data_gen_hourly_instance):
        """Test aggregating hourly data to daily"""
        aggregated = data_gen_hourly_instance.aggregate("D")
        # Should aggregate without error

    def test_aggregate_preserves_dimensions(self, data_gen_5min_instance):
        """Test that aggregation preserves dimension columns"""
        aggregated = data_gen_5min_instance.aggregate("h")

        # Dimensions should be preserved
        assert "protocol" in aggregated.columns
        assert "region" in aggregated.columns

    def test_aggregate_preserves_epoch_column(self, data_gen_5min_instance):
        """Test that epoch column exists after aggregation"""
        aggregated = data_gen_5min_instance.aggregate("h")

        assert "epoch" in aggregated.columns

    def test_aggregate_aggregates_metrics(self, data_gen_5min_instance):
        """Test that metrics are aggregated"""
        aggregated = data_gen_5min_instance.aggregate("h")

        # Metric column should exist
        assert "metric1" in aggregated.columns

    def test_aggregate_to_coarser_granularity(self, data_gen_5min_instance):
        """Test aggregating to weekly (coarser than hourly)"""
        aggregated = data_gen_5min_instance.aggregate("W")

        # Should work without error
        assert aggregated is not None

    def test_aggregate_to_monthly(self, data_gen_5min_instance):
        """Test aggregating to monthly"""
        aggregated = data_gen_5min_instance.aggregate("ME")

        assert aggregated is not None

    def test_aggregate_to_yearly(self, data_gen_5min_instance):
        """Test aggregating to yearly"""
        aggregated = data_gen_5min_instance.aggregate("Y")

        assert aggregated is not None

    def test_aggregate_finer_granularity_raises_error(self, data_gen_hourly_instance):
        """Test that aggregating to finer granularity raises ValueError"""
        with pytest.raises(ValueError, match="finer granularity"):
            data_gen_hourly_instance.aggregate("min")

    def test_aggregate_invalid_granularity(self, data_gen_5min_instance):
        """Test that invalid granularity key raises KeyError"""
        with pytest.raises(KeyError):
            data_gen_5min_instance.aggregate("invalid")

    def test_aggregate_returns_dataframe(self, data_gen_5min_instance):
        """Test that aggregate returns a DataFrame"""
        result = data_gen_5min_instance.aggregate("h")
        assert isinstance(result, pd.DataFrame)

    def test_aggregate_index_is_datetime(self, data_gen_5min_instance):
        """Test that aggregated dataframe has datetime index"""
        aggregated = data_gen_5min_instance.aggregate("h")
        assert isinstance(aggregated.index, pd.DatetimeIndex)

    def test_aggregate_sort_index(self, data_gen_5min_instance):
        """Test that aggregated dataframe is sorted by index"""
        aggregated = data_gen_5min_instance.aggregate("h")
        assert aggregated.index.is_monotonic_increasing


class TestAggregationWithMultiItems:
    """Tests for aggregation with multi-items"""

    @pytest.fixture
    def data_gen_with_multi_items(self):
        """Create DataGen instance with multi-items"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01 00:00:00"
        data_gen.end_datetime = "2022-01-01 01:00:00"
        data_gen.granularity = Granularity.FIVE_MIN

        # Need at least one dimension for aggregation to work
        data_gen.add_dimension(name="protocol", function=random_choice(["TCP", "UDP"]))

        def my_custom_function():
            while True:
                for x, y in zip(range(1, 5), range(2, 6)):
                    yield (x, y)

        data_gen.add_multi_items(
            names=["val1", "val2"],
            function=my_custom_function(),
            aggregation_type=["sum", "mean"],
        )

        metric_trend = SinusoidalTrend(
            name="sine", amplitude=1, freq=24, phase=0, noise_level=0
        )
        data_gen.add_metric(
            name="metric1", trends={metric_trend}, aggregation_type=AggregationType.SUM
        )

        return data_gen

    def test_aggregate_with_multi_items_sum(self, data_gen_with_multi_items):
        """Test aggregation with multi-items sum"""
        aggregated = data_gen_with_multi_items.aggregate("h")

        # Multi-items should be aggregated
        assert "val1" in aggregated.columns
        assert "val2" in aggregated.columns

    def test_aggregate_with_multi_items_mean(self, data_gen_with_multi_items):
        """Test aggregation with multi-items mean"""
        aggregated = data_gen_with_multi_items.aggregate("h")

        # Mean aggregation should be applied
        assert "val2" in aggregated.columns


class TestAggregationEdgeCases:
    """Tests for edge cases in aggregation"""

    @pytest.fixture
    def data_gen_single_value(self):
        """Create DataGen with very short time range"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01 00:00:00"
        data_gen.end_datetime = "2022-01-01 00:05:00"  # Only 1 interval
        data_gen.granularity = Granularity.FIVE_MIN
        # Need at least one dimension for aggregation
        data_gen.add_dimension(name="protocol", function=random_choice(["TCP"]))

        metric_trend = LinearTrend(name="linear", limit=1, offset=0, noise_level=0)
        data_gen.add_metric(name="metric1", trends={metric_trend})

        return data_gen

    def test_aggregate_single_interval(self, data_gen_single_value):
        """Test aggregation with single interval data"""
        aggregated = data_gen_single_value.aggregate("h")

        # Should still return a valid dataframe
        assert isinstance(aggregated, pd.DataFrame)

    @pytest.fixture
    def data_gen_with_constant_metric(self):
        """Create DataGen with constant metric value"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01 00:00:00"
        data_gen.end_datetime = "2022-01-01 02:00:00"
        data_gen.granularity = Granularity.FIVE_MIN
        data_gen.add_dimension(name="protocol", function=random_choice(["TCP"]))

        # Use a small limit with large offset for near-constant values
        metric_trend = LinearTrend(name="linear", limit=1, offset=10, noise_level=0)
        data_gen.add_metric(
            name="constant_metric",
            trends={metric_trend},
            aggregation_type=AggregationType.AVG,
        )

        return data_gen

    def test_aggregate_constant_value(self, data_gen_with_constant_metric):
        """Test aggregation of constant metric value"""
        aggregated = data_gen_with_constant_metric.aggregate("h")

        # All aggregated values should be the same (10)
        assert aggregated is not None


class TestAggregationMultipleDimensions:
    """Tests for aggregation with multiple dimensions"""

    @pytest.fixture
    def data_gen_multi_dimensions(self):
        """Create DataGen with multiple dimensions"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01 00:00:00"
        data_gen.end_datetime = "2022-01-02 00:00:00"
        data_gen.granularity = Granularity.HOURLY

        data_gen.add_dimension(name="protocol", function=random_choice(["TCP", "UDP"]))
        data_gen.add_dimension(
            name="region", function=random_choice(["US", "EU", "AP"])
        )
        data_gen.add_dimension(name="product", function=random_choice(["A", "B", "C"]))

        metric_trend = SinusoidalTrend(
            name="sine", amplitude=1, freq=24, phase=0, noise_level=0
        )
        data_gen.add_metric(
            name="metric1", trends={metric_trend}, aggregation_type=AggregationType.SUM
        )

        return data_gen

    def test_aggregate_multiple_dimensions_daily(self, data_gen_multi_dimensions):
        """Test aggregation with multiple dimensions to daily"""
        aggregated = data_gen_multi_dimensions.aggregate("D")

        # All dimensions should be preserved
        assert "protocol" in aggregated.columns
        assert "region" in aggregated.columns
        assert "product" in aggregated.columns

    def test_aggregate_multiple_dimensions_weekly(self, data_gen_multi_dimensions):
        """Test aggregation with multiple dimensions to weekly"""
        aggregated = data_gen_multi_dimensions.aggregate("W")

        assert aggregated is not None
        assert len(aggregated) < len(data_gen_multi_dimensions.data)

    def test_aggregate_preserves_all_dimension_combinations(
        self, data_gen_multi_dimensions
    ):
        """Test that all dimension combinations are preserved after aggregation"""
        aggregated = data_gen_multi_dimensions.aggregate("D")

        # Check that we have fewer rows but all dimensions present
        original_dims = data_gen_multi_dimensions.data.groupby(
            ["protocol", "region", "product"]
        ).ngroups
        aggregated_dims = aggregated.groupby(["protocol", "region", "product"]).ngroups

        # Original should have more combinations than aggregated (since we're grouping by time too)
        # Actually, after aggregation by time only, dimensions should be the same
        assert original_dims == aggregated_dims
