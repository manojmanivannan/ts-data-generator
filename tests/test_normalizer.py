"""Tests for the Normalizer and normalization strategy classes."""

from __future__ import annotations

import pandas as pd
import pytest

from ts_data_generator.exceptions import ValidationError
from ts_data_generator.transforms.normalizer import (
    MinMaxStrategy,
    NormalizationStrategy,
    Normalizer,
    StandardStrategy,
    create_normalizer,
)


class TestMinMaxStrategy:
    """Unit tests for MinMaxStrategy."""

    @pytest.fixture
    def strategy(self) -> MinMaxStrategy:
        return MinMaxStrategy()

    def test_fit_computes_min_max(self, strategy: MinMaxStrategy) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [10.0, 20.0, 30.0]})
        strategy.fit(data)
        assert strategy._min is not None
        assert strategy._max is not None
        assert strategy._min["a"] == 1.0
        assert strategy._max["a"] == 3.0
        assert strategy._min["b"] == 10.0
        assert strategy._max["b"] == 30.0

    def test_fit_skips_non_numeric(self, strategy: MinMaxStrategy) -> None:
        data = pd.DataFrame({"a": [1, 2, 3], "label": ["x", "y", "z"]})
        strategy.fit(data)
        # 'label' should not appear in _min/_max
        assert "label" not in strategy._min.index
        assert "label" not in strategy._max.index

    def test_transform_scales_to_zero_one(self, strategy: MinMaxStrategy) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        strategy.fit(data)
        scaled = strategy.transform(data)
        assert scaled["a"].iloc[0] == pytest.approx(0.0)
        assert scaled["a"].iloc[1] == pytest.approx(0.5)
        assert scaled["a"].iloc[2] == pytest.approx(1.0)

    def test_transform_returns_copy(self, strategy: MinMaxStrategy) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        strategy.fit(data)
        scaled = strategy.transform(data)
        assert scaled is not data  # should not mutate in place

    def test_inverse_transform_restores_original(self, strategy: MinMaxStrategy) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [10.0, 20.0, 30.0]})
        strategy.fit(data)
        scaled = strategy.transform(data)
        restored = strategy.inverse_transform(scaled)
        pd.testing.assert_frame_equal(restored, data.astype(float))

    def test_zero_division_handling(self, strategy: MinMaxStrategy) -> None:
        """When col min == max, transform returns 0.0, inverse returns the constant."""
        data = pd.DataFrame({"a": [5.0, 5.0, 5.0]})
        strategy.fit(data)
        scaled = strategy.transform(data)
        assert scaled["a"].iloc[0] == pytest.approx(0.0)

        restored = strategy.inverse_transform(scaled)
        assert restored["a"].iloc[0] == pytest.approx(5.0)

    def test_transform_before_fit_raises(self, strategy: MinMaxStrategy) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        with pytest.raises(ValidationError, match="fit before transform"):
            strategy.transform(data)

    def test_inverse_transform_before_fit_raises(self, strategy: MinMaxStrategy) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        with pytest.raises(ValidationError, match="fit before inverse_transform"):
            strategy.inverse_transform(data)


class TestStandardStrategy:
    """Unit tests for StandardStrategy (z-score)."""

    @pytest.fixture
    def strategy(self) -> StandardStrategy:
        return StandardStrategy()

    def test_fit_computes_mean_std(self, strategy: StandardStrategy) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        strategy.fit(data)
        assert strategy._mean is not None
        assert strategy._std is not None
        assert strategy._mean["a"] == pytest.approx(2.0)
        assert strategy._std["a"] == pytest.approx(1.0)

    def test_transform_center_to_zero(self, strategy: StandardStrategy) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        strategy.fit(data)
        scaled = strategy.transform(data)
        # mean of z-scores should be ~0, std ~1
        assert scaled["a"].mean() == pytest.approx(0.0, abs=1e-14)
        assert scaled["a"].std() == pytest.approx(1.0)

    def test_inverse_transform_restores_original(self, strategy: StandardStrategy) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        strategy.fit(data)
        scaled = strategy.transform(data)
        restored = strategy.inverse_transform(scaled)
        pd.testing.assert_frame_equal(restored, data.astype(float))

    def test_zero_std_handling(self, strategy: StandardStrategy) -> None:
        """When std == 0, transform returns 0.0, inverse returns the mean."""
        data = pd.DataFrame({"a": [5.0, 5.0, 5.0]})
        strategy.fit(data)
        scaled = strategy.transform(data)
        assert scaled["a"].iloc[0] == pytest.approx(0.0)

        restored = strategy.inverse_transform(scaled)
        assert restored["a"].iloc[0] == pytest.approx(5.0)

    def test_transform_before_fit_raises(self, strategy: StandardStrategy) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        with pytest.raises(ValidationError, match="fit before transform"):
            strategy.transform(data)

    def test_inverse_transform_before_fit_raises(self, strategy: StandardStrategy) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        with pytest.raises(ValidationError, match="fit before inverse_transform"):
            strategy.inverse_transform(data)


class TestNormalizer:
    """Tests for the Normalizer class."""

    def test_normalize_minmax(self) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0], "label": ["x", "y", "z"]})
        normalizer = Normalizer(MinMaxStrategy())
        result = normalizer.normalize(data)

        # Label column untouched
        assert list(result["label"]) == ["x", "y", "z"]
        # Numeric column scaled
        assert result["a"].min() == pytest.approx(0.0)
        assert result["a"].max() == pytest.approx(1.0)

    def test_denormalize_restores(self) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        normalizer = Normalizer(MinMaxStrategy())
        normalizer.normalize(data)
        normalizer.denormalize(data)
        assert data["a"].iloc[0] == pytest.approx(1.0)
        assert data["a"].iloc[1] == pytest.approx(2.0)
        assert data["a"].iloc[2] == pytest.approx(3.0)

    def test_normalize_standard(self) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        normalizer = Normalizer(StandardStrategy())
        normalizer.normalize(data)
        assert data["a"].mean() == pytest.approx(0.0, abs=1e-14)
        assert data["a"].std() == pytest.approx(1.0)

    def test_denormalize_standard_restores(self) -> None:
        data = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        normalizer = Normalizer(StandardStrategy())
        normalizer.normalize(data)
        normalizer.denormalize(data)
        pd.testing.assert_frame_equal(data, pd.DataFrame({"a": [1.0, 2.0, 3.0]}))

    @pytest.mark.parametrize("method,strategy_cls", [
        ("min-max", MinMaxStrategy),
        ("mean-std", StandardStrategy),
    ])
    def test_create_normalizer(self, method: str, strategy_cls: type) -> None:
        normalizer = create_normalizer(method)
        assert isinstance(normalizer, Normalizer)
        assert isinstance(normalizer.strategy, strategy_cls)

    def test_create_normalizer_unknown(self) -> None:
        with pytest.raises(ValidationError, match="Unknown"):
            create_normalizer("invalid-method")

    def test_normalizer_strategy_property(self) -> None:
        s = MinMaxStrategy()
        n = Normalizer(s)
        assert n.strategy is s


class TestNormalizationStrategyBase:
    """Tests for the abstract base class."""

    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError):
            NormalizationStrategy()
