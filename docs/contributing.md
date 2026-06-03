---
layout: default
title: Contributing
permalink: /contributing
nav_order: 7
---

# Contributing

We welcome contributions to the **Synthetic Time Series Data Generator**! Whether you are fixing typos in documentation, optimising data generation speeds, or building new custom generators, your help is appreciated.

---

## 🛠️ Development Setup

The repository is built using modern Python tooling. We highly recommend using the ultra-fast `uv` tool for virtual environment management.

### 1. Clone the Repository:
```bash
git clone https://github.com/manojmanivannan/ts-data-generator.git
cd ts-data-generator
```

### 2. Set Up Virtual Environment & Dependencies:
```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Synchronize virtual env and install dev dependencies
uv sync --extra dev
```

### 3. Run the Test Suite:
Ensure everything is correctly configured by running `pytest`:
```bash
uv run pytest
```

---

## 🔌 Building Custom Extensions

You can extend `ts-data-generator` by adding custom **Trends** or **Anomalies**. To ensure your extensions play nicely with the deterministic seeding engine and pipeline, you must adhere to the correct base classes and method signatures.

### 📈 1. Creating a Custom Trend

A trend defines a clean base signal. To build a custom trend:
1.  Create a class that inherits from the abstract base class `Trends` (located in `ts_data_generator.utils.trends`).
2.  Implement the `generate(self, timestamps: pd.DatetimeIndex, rng: SeedableRNG | None = None) -> np.ndarray` method.
3.  Ensure your mathematical transformations return a NumPy array of floats matching the length of `timestamps`.
4.  **Important**: All stochastic choices *must* use the passed-down `rng` object to maintain determinism.

#### Composed Boilerplate Template:
```python
import numpy as np
import pandas as pd
from ts_data_generator.utils.trends import Trends
from ts_data_generator.random import SeedableRNG

class CustomStepTrend(Trends):
    """Generates a custom step wave that increments by a factor every N timestamps."""
    
    def __init__(self, name: str = "default", step_interval: int = 10, increment: float = 5.0) -> None:
        super().__init__(name)
        self._step_interval = step_interval
        self._increment = increment
        
    def generate(
        self, 
        timestamps: pd.DatetimeIndex, 
        rng: SeedableRNG | None = None
    ) -> np.ndarray:
        n = len(timestamps)
        # Create baseline array
        steps = np.arange(n) // self._step_interval
        base_signal = steps * self._increment
        
        # Add random minor fluctuations safely using the unified branching helper
        noise = SeedableRNG.normal_or_fallback(0, 0.1, n, rng=rng)
            
        return base_signal + noise
```

---

### 🛑 2. Creating a Custom Anomaly

An anomaly perturbs a metric *after* the baseline trends are compiled. To build a custom anomaly:
1.  Create a class that inherits from the abstract base class `Anomaly` (located in `ts_data_generator.anomalies.base`).
2.  Implement the `intervene(self, base_array: np.ndarray, timestamps: pd.DatetimeIndex, rng: SeedableRNG | None = None) -> np.ndarray` method.
3.  Mutate or copy `base_array` and return the contaminated NumPy array.

#### Composed Boilerplate Template:
```python
import numpy as np
import pandas as pd
from ts_data_generator.anomalies.base import Anomaly
from ts_data_generator.random import SeedableRNG

class CustomClippingAnomaly(Anomaly):
    """Clips or caps all metric values at a strict threshold stochastically."""
    
    def __init__(self, clip_limit: float = 100.0, trigger_probability: float = 0.05) -> None:
        self._clip_limit = clip_limit
        self._trigger_probability = trigger_probability
        
    def intervene(
        self, 
        base_array: np.ndarray, 
        timestamps: pd.DatetimeIndex, 
        rng: SeedableRNG | None = None
    ) -> np.ndarray:
        result = base_array.copy()
        n = len(base_array)
        
        # Determine stochastically if clipping happens at each timestamp
        # Use the seeded RNG when available to maintain determinism
        if rng is not None:
            mask = rng.random(n) < self._trigger_probability
        else:
            mask = np.random.random(n) < self._trigger_probability
            
        # Apply clipping intervention
        result[mask] = np.minimum(result[mask], self._clip_limit)
        
        return result
```

---

## 📝 Pull Request Checklist

Before submitting a Pull Request, please ensure you have completed the following:

1.  **Format and Lint**: Run formatting checks on your codebase using Ruff:
    ```bash
    uv run ruff format .
    uv run ruff check .
    ```
2.  **Add Unit Tests**: If you are adding a new trend or anomaly, add unit tests in the `tests/` directory verifying it works with various datetime indices.
3.  **Run Test Suite**: Confirm all tests pass (`uv run pytest`).
4.  **Update Docs**: If you have modified or added any public API, make sure to update the corresponding `.md` file inside the `docs/` directory.
