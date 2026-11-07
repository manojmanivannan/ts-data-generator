  ──────
  ### 1. Fragmented Public Namespace & Deep Imports

  __init__.py:22-25 only exports DataGen and __version__. Even the library's own 6-line quickstart requires three separate import paths:

    from ts_data_generator import DataGen
    from ts_data_generator.schema import Granularity
    from ts_data_generator.utils.trends import SinusoidalTrend
    from ts_data_generator.utils.functions import random_choice

  • Core primitives buried in utils: Putting primary user-facing building blocks (SinusoidalTrend, LinearTrend, random_choice) inside ts_data_generator.utils.* is an
  anti-pattern. In Python packages, utils conventionally signals internal helpers, not core domain objects.
  • How to improve: Re-export core types (DataGen, Granularity, AggregationType, common trends/functions) at the top-level __init__.py, and expose clean top-level
  submodules like ts_data_generator.trends instead of ts_data_generator.utils.trends.
  ──────
  ### 2. Inconsistent Naming Conventions

  • Package vs. Main Class: The package is named ts_data_generator, so users and LLMs naturally guess DataGenerator, but the class is abbreviated to DataGen.
  Providing DataGenerator = DataGen as an alias would prevent this friction.
  • Plural class names for singular objects: In models.py:97-98 and utils/trends.py, single-instance classes are named in the plural:
      • Metrics (represents a single metric; type annotations read list[Metrics])
      • Dimensions (represents a single dimension; type annotations read list[Dimensions])
      • MultiItems (represents a single multi-item group)
      • Trends (abstract base class, while its subclasses are singular LinearTrend, SinusoidalTrend, and Anomaly in anomalies/base.py is singular).
  • Inconsistent Granularity enum names: Granularity mixes numbered noun phrases with adjectives:
      • ONE_SECOND = "s", ONE_MIN = "min", FIVE_MIN = "5min"
      • HOURLY = "h", DAILY = "D", WEEKLY = "W", MONTHLY = "ME", YEARLY = "Y"

  ──────
  ### 3. Packaging & Static Typing Gaps

  • Missing PEP 561 py.typed marker: The package has inline type annotations throughout, but does not ship a py.typed file in ts_data_generator/. Compliant type
  checkers (mypy, pyright) require py.typed to officially recognize a third-party package as typed.
  • Contradictory type annotations on DataGen:
      • DataGen.__init__ types granularity: Granularity = Granularity.FIVE_MIN (disallowing strings like "s" or "h" in __init__), whereas the granularity` setter
      accepts Granularity | str and the getter returns str. Making Granularity(StrEnum) and typing granularity: Granularity | str in __init__ would make both enum
      members and pandas frequency strings first-class everywhere.
      • DataGen.__init__ types start_datetime: str | datetime | pd.Timestamp, but _validate_dates() runs datetime.fromisoformat(cast(str, self._start_datetime)),
      which raises a TypeError at runtime if you actually pass a datetime or pd.Timestamp!

  ──────
  ### 4. Ergonomics & Execution Model Pitfalls

  • Using set for trends in add_metric:
  The API encourages dg.add_metric("temperature", {SinusoidalTrend(...)})—passing a Python set of trend instances. Sets are unordered and require custom objects to be
  hashable; accepting Trend | Sequence[Trend] is much more idiomatic.
  • Repeated eager regeneration on mutation:
  In DataGen, once start_datetime and end_datetime are set, every subsequent property assignment or add_* call triggers self._request_regeneration() → self.
  _generate_data(). Following the library's own quickstart order:
    dg = DataGen()
    dg.start_datetime = "2024-01-01"
    dg.end_datetime = "2024-01-07"      # Generates data (#1)
    dg.to_granularity("h")              # Regenerates data (#2)
    dg.add_dimension("region", ...)     # Regenerates data (#3)
    dg.add_metric("temperature", ...)   # Regenerates data (#4)
  Evaluating lazily when .data is accessed (or via an explicit .generate() method) would avoid wasted recomputation on every configuration step.
  • Dead subpackages: __init__.py is an empty leftover package containing only a 1-line docstring.
