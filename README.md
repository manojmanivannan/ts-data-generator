<!-- html title in the middle -->
<p style="text-align: center;">
    <h1 align="center">Data Generator Library</h1>
    <h3 align="center">A Python library for generating synthetic time series data</h3>
</p>






## Installation

### Repo
After cloning this repo and creating a virtual environment, run the following command:
```bash
pip install --editable .
```
### PyPi
Coming soon


## Usage

```python
from ts_data_generator import DataGen
from ts_data_generator.utils import some_function

# Create a data generator
gen = DataGen()

# Generate sample data
df = gen.generate_sample_data(rows=100)

# Use utility functions
processed_df = some_function(df)
```

#### Release method
1. `git tag <x.x.x>`
2. `git push origin <x.x.x>`