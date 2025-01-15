"""
Tests for the DataGen class
"""
import pytest
import pandas as pd
import numpy as np
from ts_data_generator import DataGen
from ts_data_generator.schema.models import Granularity
from ts_data_generator.utils.functions import random_choice
from typing import Generator


class TestDataGen5minGenerator:
    # Setup method to initialize the Calculator instance
    
    
    @pytest.fixture
    def data_gen_instance(self):
        """Fixture to create a DataGen instance"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01"
        data_gen.end_datetime = "2022-01-02"
        # Create function that will return random choice from list
        protocol_choices = random_choice(["TCP", "UDP"])
        data_gen.add_dimension(name="protocol", function=protocol_choices)
        data_gen.add_metric(name="metric1", function_type="sine", frequency_in_hour=1, offset_in_minutes=0, scale=2)
        return data_gen

    def test_generated_data_is_pandas_instance(self, data_gen_instance):
        data_gen_instance.generate_data()
        assert isinstance(data_gen_instance.data, pd.DataFrame)

    
    def test_metric_generator_output(self, data_gen_instance):
        data_gen_instance.generate_data()
        expected_length = int(24*60/5)+1 #( 24 hours * 12 five-minute intervals in 1 hour)+1 to include end date
        assert len(data_gen_instance.metrics["metric1"]._data) == expected_length
        assert len(data_gen_instance.metrics["metric1"]._timestamps) == expected_length

    

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
        data_gen.add_metric(name="metric1", function_type="sine", frequency_in_hour=1, offset_in_minutes=0, scale=2)
        return data_gen

    def test_generated_data_is_pandas_instance(self, data_gen_instance):
        data_gen_instance.generate_data()
        assert isinstance(data_gen_instance.data, pd.DataFrame)

    
    def test_metric_generator_output(self, data_gen_instance):
        data_gen_instance.generate_data()
        expected_length = int(24)+1 #( 24 hours)+1 to include end date
        assert len(data_gen_instance.metrics["metric1"]._data) == expected_length
        assert len(data_gen_instance.metrics["metric1"]._timestamps) == expected_length

    def test_invalid_dimension_set(self, data_gen_instance):
        data_gen_instance.add_dimension(name="random", function="random")
        with pytest.raises(ValueError):
            data_gen_instance.generate_data()

    def test_update_dimension(self, data_gen_instance):
        assert isinstance(data_gen_instance.dimensions["protocol"].function, Generator)
        with pytest.raises(ValueError):
            data_gen_instance.update_dimension(name="non-present", function="random")
        data_gen_instance.update_dimension(name="protocol", function="random")
        assert isinstance(data_gen_instance.dimensions["protocol"].function, str)

    def test_update_metric(self, data_gen_instance):
        data_gen_instance.generate_data()
        assert isinstance(data_gen_instance.metrics["metric1"].to_json()["data"], np.ndarray)
        with pytest.raises(ValueError):
            data_gen_instance.update_metric(name="non-present", function_value="non-random")

        # add a new constant type metric
        data_gen_instance.add_metric(name="metric2", function_type="constant", function_value=3)
        data_gen_instance.generate_data()
        assert np.unique(data_gen_instance.metrics["metric2"].to_json()['data'])[0] == 3

        # update the metric value
        data_gen_instance.update_metric(name="metric2", function_value=2)
        data_gen_instance.generate_data()
        assert np.unique(data_gen_instance.metrics["metric2"].to_json()['data'])[0] == 2
