"""
Tests for the DataGen class
"""
import pytest
import pandas as pd
import numpy as np
from ts_data_generator import DataGen
from ts_data_generator.schema.models import Granularity
from ts_data_generator.utils.functions import random_choice, random_int
from typing import Generator
from ts_data_generator.utils.trends import SinusoidalTrend, LinearTrend, StockTrend, WeekendTrend


class TestDataGen5minGenerator:
    # Setup method to initialize the Calculator instance
    
    
    @pytest.fixture
    def data_gen_instance(self):
        """Fixture to create a DataGen instance"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01"
        data_gen.end_datetime = "2022-01-02"
        data_gen.granularity = Granularity.FIVE_MIN
        # Create function that will return random choice from list
        data_gen.add_dimension(name="protocol", function=random_choice(["TCP", "UDP"]))
        data_gen.add_dimension(name="port", function=random_int(1, 65536))

        metric1_trend = SinusoidalTrend(name="sine", amplitude=1, freq=24, phase=0, noise_level=1)
        data_gen.add_metric(name="sine1", trends=[metric1_trend])

        metric4_trend = WeekendTrend(name="weekend", weekend_effect=10, direction="up", noise_level=0.5, limit=10)
        data_gen.add_metric(name="weekend_trend1", trends=[metric4_trend])

        metric5_trend = StockTrend(name='stock', amplitude=10, direction='up', noise_level=0.5)
        metric5_linear = LinearTrend(name='Linear', offset=0, noise_level=1, limit=10)
        data_gen.add_metric(name="stock_like_trend1", trends=[metric5_trend, metric5_linear])

        return data_gen

    def test_generated_data_is_pandas_instance(self, data_gen_instance):
        data_gen_instance.generate_data()
        assert isinstance(data_gen_instance.data, pd.DataFrame)

    
    def test_metric_generator_output(self, data_gen_instance):
        data_gen_instance.generate_data()
        expected_length = int(24*60/5)+1 #( 24 hours * 12 five-minute intervals in 1 hour)+1 to include end date
        assert data_gen_instance.data.shape[0] == expected_length
        assert data_gen_instance.data.shape[1] == 5 # 3 columns: protocol, port, sine1, weekend_trend1, stock_like_trend1

    

class TestDataGenHourlyGenerator:
    # Setup method to initialize the Calculator instance
    
    
    @pytest.fixture
    def data_gen_instance(self):
        """Fixture to create a DataGen instance"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01"
        data_gen.end_datetime = "2022-01-02"
        data_gen.granularity = Granularity.HOURLY
        # Create function that will return random choice from list
        protocol_choices = random_choice(["TCP", "UDP"])
        data_gen.add_dimension(name="protocol", function=protocol_choices)
        metric1_trend = SinusoidalTrend(name="sine", amplitude=1, freq=24, phase=0, noise_level=1)
        data_gen.add_metric(name="metric1", trends=[metric1_trend])
        return data_gen

    def test_invalid_dimension_set(self, data_gen_instance):
        data_gen_instance.add_dimension(name="random", function="random")
        with pytest.raises(ValueError):
            data_gen_instance.generate_data()


