"""
Tests for the DataGen class
"""
import pytest
import pandas as pd
import numpy as np
from ts_data_generator import DataGen
from ts_data_generator.schema.models import Granularity
from ts_data_generator.utils.functions import random_choice, random_int, random_multi_choice
from enum import Enum
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
        assert isinstance(data_gen_instance.data, pd.DataFrame)

    
    def test_metric_generator_output(self, data_gen_instance):
        expected_length = int(24*60/5)+1 #( 24 hours * 12 five-minute intervals in 1 hour)+1 to include end date
        assert data_gen_instance.data.shape[0] == expected_length
        assert data_gen_instance.data.shape[1] == 6 # 6 columns: protocol, epoch, port, sine1, weekend_trend1, stock_like_trend1

    def test_remove_dimension(self, data_gen_instance):
        dimension_to_remove = "port"
        data_gen_instance.remove_dimension(name=dimension_to_remove)
        assert not(dimension_to_remove in list(data_gen_instance.dimensions.keys())) is True

    def test_remove_metric(self, data_gen_instance):
        metric_to_remove = "weekend_trend1"
        data_gen_instance.remove_metric(name=metric_to_remove)
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
        
        with pytest.raises(IndexError):
            data_gen_instance.add_dimension(name="random", function=[])


class TestDataGenDailyGenerator:
    # Setup method to initialize the Calculator instance
    
    
    @pytest.fixture
    def data_gen_instance(self):
        """Fixture to create a DataGen instance"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01"
        data_gen.end_datetime = "2022-01-02"
        data_gen.granularity = Granularity.DAILY
        # Create function that will return random choice from list
        protocol_choices = random_choice(["TCP", "UDP"])
        data_gen.add_dimension(name="protocol", function=protocol_choices)
        metric1_trend = SinusoidalTrend(name="sine", amplitude=1, freq=24, phase=0, noise_level=1)
        data_gen.add_metric(name="metric1", trends=[metric1_trend])
        return data_gen

    def test_invalid_dimension_set(self, data_gen_instance):
        
        with pytest.raises(IndexError):
            data_gen_instance.add_dimension(name="random", function=[])



class TestDataGenSecondlyGenerator:
    # Setup method to initialize the Calculator instance
    
    
    @pytest.fixture
    def data_gen_instance(self):
        """Fixture to create a DataGen instance"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01"
        data_gen.end_datetime = "2022-01-02"
        data_gen.granularity = Granularity.ONE_SECOND
        # Create function that will return random choice from list
        protocol_choices = random_choice(["TCP", "UDP"])
        data_gen.add_dimension(name="protocol", function=protocol_choices)
        metric1_trend = SinusoidalTrend(name="sine", amplitude=1, freq=24, phase=0, noise_level=1)
        data_gen.add_metric(name="metric1", trends=[metric1_trend])
        return data_gen

    def test_granularity(self, data_gen_instance):
        assert data_gen_instance.granularity == 's'
        assert data_gen_instance.data['epoch'].iloc[1] - data_gen_instance.data['epoch'].iloc[0] == np.int64(1)

class TestDataScaleGenerator:
    # Setup method to initialize the Calculator instance
    
    
    @pytest.fixture
    def data_gen_instance(self):
        """Fixture to create a DataGen instance"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01"
        data_gen.end_datetime = "2022-01-02"
        data_gen.granularity = Granularity.HOURLY
        # Create function that will return random choice from list
        data_gen.add_dimension(name="protocol", function=random_choice("TCP UDP".split()))
        data_gen.add_dimension(name="interface", function="X Y Z".split())
        metric1_trend = SinusoidalTrend(name="sine", amplitude=1, freq=24, phase=0, noise_level=1)
        data_gen.add_metric(name="metric1", trends=[metric1_trend])
        return data_gen

    def test_granularity(self, data_gen_instance):
        assert data_gen_instance.data['epoch'].iloc[1] - data_gen_instance.data['epoch'].iloc[0] == np.int64(3600)

    def test_scale(self,data_gen_instance):
        with pytest.raises(NotImplementedError):
            data_gen_instance.normalize(method='invalid')
        
        saved = data_gen_instance.data['metric1'].iloc[0]

        data_gen_instance.normalize()
        assert data_gen_instance.data['metric1'].min() == 0
        assert data_gen_instance.data['metric1'].max() == 1
        assert data_gen_instance.data['metric1'].iloc[0] != pytest.approx(saved)


        data_gen_instance.denormalize()
        assert data_gen_instance.data['metric1'].iloc[0] == pytest.approx(saved)


    def test_linked_dimension(self, data_gen_instance):
        import random
        def my_custom_function():
            while True:
                val1 = random.randint(1,100)
                val2 =  random.randint(1,100)
                val3 = val1 + val2
                yield (val1, val2, val3)
                
        data_gen_instance.add_multi_items(names=['dim1','dim2','dim3'],function=my_custom_function())
        assert np.True_ is ((data_gen_instance.data['dim1'] + data_gen_instance.data['dim2'] == data_gen_instance.data['dim3']).values.all())
        with pytest.raises(ValueError):
            data_gen_instance.add_multi_items(names='dim1 dim2'.split(),function=my_custom_function())
            
        with pytest.raises(ValueError):
            data_gen_instance.add_multi_items(names='dim1 dim5 dim6'.split(),function=my_custom_function())
            
        data_gen_instance.remove_multi_item(['dim1'])
        assert 'dim2' not in data_gen_instance.data.columns
            

class TestDataAggregation:
    # Setup method to initialize the Calculator instance
    
    
    @pytest.fixture
    def data_gen_instance(self):
        """Fixture to create a DataGen instance"""
        data_gen = DataGen()
        data_gen.start_datetime = "2022-01-01 00:00:00"
        data_gen.end_datetime = "2022-01-01 00:15:00"
        data_gen.granularity = Granularity.FIVE_MIN
        # Create function that will return random choice from list
        data_gen.add_dimension(name="protocol", function=random_choice("TCP UDP".split()))
        data_gen.add_dimension(name="interface", function="X Y Z".split())
        def my_custom_function():
            while True:
                for x,y,z in zip(range(1,10),range(2,11),range(3,12)):
                    yield (x,y,z)

        data_gen.add_multi_items(names="val1 val2 val3".split(), function=my_custom_function(), aggregation_type="sum mean max".split())
        return data_gen
    
    def test_aggregate(self, data_gen_instance):
        print(data_gen_instance.data)
        print(data_gen_instance.aggregate("W"))
        print(data_gen_instance.data)
        