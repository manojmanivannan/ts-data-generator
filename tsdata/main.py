"""FastAPI application for generating synthetic time series data over HTTP.

Provides REST endpoints that expose the ts-data-generator library's
:class:`DataGen` engine for use via FastAPI Cloud or any ASGI host.

Install the cloud extra to get FastAPI dependencies::

    pip install ts-data-generator[cloud]

Run locally::

    fastapi dev
"""

from __future__ import annotations

import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError
from pydantic import field_validator

from ts_data_generator import DataGen, __version__
from ts_data_generator.anomalies.base import Anomaly
from ts_data_generator.anomalies.drift import ConceptDrift, DriftSegment
from ts_data_generator.exceptions import (
    AggregationError,
    ConfigurationError,
    DataGeneratorError,
    DimensionError,
    MetricError,
    MultiItemError,
    RegistryError,
    ValidationError,
)
from ts_data_generator.schema.models import Granularity
from ts_data_generator.schema.parser import (
    PRESETS,
    parse_anomaly_spec,
    parse_dimension_spec,
    parse_trend_spec,
)
from ts_data_generator.utils.registry import Registry
from ts_data_generator.utils.trends import Trends

# ---------------------------------------------------------------------------
# Module-level registries (same as the CLI, but without Click dependency)
# ---------------------------------------------------------------------------

_dimension_registry = Registry(
    "ts_data_generator.utils.functions",
    name_filter=lambda n: not n.startswith("_"),
)
_trend_registry = Registry(
    "ts_data_generator.utils.trends",
    name_filter=lambda n: not n.startswith("_") and n != "Trends",
    base_class=Trends,
)
_anomaly_registry = Registry(
    "ts_data_generator.anomalies",
    name_filter=lambda n: not n.startswith("_") and n != "Anomaly",
    base_class=Anomaly,
)

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    """Request body for data generation.

    Field format mirrors the CLI JSON config so existing config files
    can be used directly.
    """

    start: str = Field(..., description="Start datetime (YYYY-MM-DD or ISO format)")
    end: str = Field(..., description="End datetime (YYYY-MM-DD or ISO format)")
    granularity: str = Field(
        ..., description="Time granularity: s, min, 5min, h, D, W, ME, or Y"
    )
    dimensions: list[str] = Field(
        default_factory=list,
        description="Dimension specs, e.g. ['product:random_choice:A,B,C']",
    )
    metrics: list[str] = Field(
        default_factory=list,
        description="Metric specs, e.g. ['sales:LinearTrend(slope=30)+WeekendTrend(weekend_effect=50)']",
    )
    anomalies: list[str] = Field(
        default_factory=list,
        description="Anomaly specs, e.g. ['sales:PointAnomaly(probability=0.01,magnitude=5)']",
    )
    seed: int | None = Field(
        default=None, description="Random seed for deterministic generation"
    )

    @field_validator("granularity")
    @classmethod
    def validate_granularity(cls, v: str) -> str:
        valid = [g.value for g in Granularity]
        if v not in valid:
            raise ValueError(
                f"Invalid granularity '{v}'. Valid values: {', '.join(valid)}"
            )
        return v


class GenerateResponse(BaseModel):
    """Response containing generated time series data."""

    rows: int
    columns: list[str]
    granularity: str
    seed: int | None
    data: list[dict[str, Any]]


class PresetGenerateRequest(BaseModel):
    """Request body for generating data from a preset (all fields optional overrides)."""

    start: str | None = Field(
        default=None, description="Override preset start datetime"
    )
    end: str | None = Field(default=None, description="Override preset end datetime")
    granularity: str | None = Field(
        default=None, description="Override preset granularity"
    )
    seed: int | None = Field(default=None, description="Override preset seed")


class PresetSummary(BaseModel):
    name: str
    start: str
    end: str
    granularity: str
    dimensions_count: int
    metrics_count: int


class PresetDetail(BaseModel):
    name: str
    config: dict[str, Any]


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

description = """
The ts-data-generator API allows you to generate synthetic time series data via HTTP requests. 
Refer [documentation](https://manojmanivannan.github.io/ts-data-generator/cli)"""
app = FastAPI(
    title="ts-data-generator API",
    description=description,
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

_STATUS_MAP: dict[type, int] = {
    ValidationError: 400,
    DimensionError: 400,
    MetricError: 400,
    MultiItemError: 400,
    RegistryError: 400,
    AggregationError: 400,
    ConfigurationError: 422,
}


def _make_json_serializable(obj: Any) -> Any:
    """Recursively convert objects to JSON-serializable types."""
    if isinstance(obj, Exception):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    else:
        return obj


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request, exc):  # noqa: ARG001
    """Handle FastAPI request validation errors with detailed error messages."""
    errors = exc.errors()
    error_messages = []
    for error in errors:
        loc = ".".join(str(x) for x in error.get("loc", []))
        msg = error.get("msg", str(error))
        error_messages.append(f"{loc}: {msg}")
    # Convert errors to JSON-serializable format
    serializable_errors = _make_json_serializable(errors)
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "detail": "\n".join(error_messages),
            "errors": serializable_errors,
        },
    )


@app.exception_handler(PydanticValidationError)
async def pydantic_validation_error_handler(request, exc):  # noqa: ARG001
    """Handle Pydantic ValidationError from manual model instantiation."""
    errors = exc.errors()
    error_messages = []
    for error in errors:
        loc = ".".join(str(x) for x in error.get("loc", []))
        msg = error.get("msg", str(error))
        error_messages.append(f"{loc}: {msg}")
    # Convert errors to JSON-serializable format
    serializable_errors = _make_json_serializable(errors)
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "detail": "\n".join(error_messages),
            "errors": serializable_errors,
        },
    )


@app.exception_handler(DataGeneratorError)
async def datagen_error_handler(request, exc):  # noqa: ARG001
    """Map DataGeneratorError subclasses to HTTP status codes."""
    status = _STATUS_MAP.get(type(exc), 500)
    return JSONResponse(
        status_code=status,
        content={"error": exc.__class__.__name__, "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request, exc):  # noqa: ARG001
    """Catch-all handler for unexpected exceptions."""
    # Log the full traceback for debugging
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"error": exc.__class__.__name__, "detail": str(exc)},
    )


# ---------------------------------------------------------------------------
# Helper: build a DataGen instance from a GenerateRequest
# ---------------------------------------------------------------------------

_DIM_SEPARATOR = ";"


def _build_datagen(request: GenerateRequest) -> DataGen:
    """Construct and configure a :class:`DataGen` from a request body.

    Mirrors the CLI ``generate`` command logic but raises
    :class:`HTTPException` on validation or registry errors.
    """
    dg = DataGen(seed=request.seed)
    dg.start_datetime = request.start
    dg.end_datetime = request.end
    dg.to_granularity(request.granularity)

    # --- Dimensions ---
    for dim_spec in request.dimensions:
        try:
            parsed = parse_dimension_spec(dim_spec)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            dim_fn = _dimension_registry.get(parsed.function_name)
        except RegistryError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            if isinstance(parsed.args, (tuple, list)) and len(parsed.args) > 1:
                dg.add_dimension(parsed.name, dim_fn(parsed.args))
            elif isinstance(parsed.args, (tuple, list)) and len(parsed.args) == 1:
                dg.add_dimension(parsed.name, dim_fn(parsed.args[0]))
            else:
                dg.add_dimension(parsed.name, dim_fn(*parsed.args))
        except TypeError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid parameters for dimension '{parsed.name}' "
                f"with function '{parsed.function_name}': {parsed.args}",
            ) from exc

    # --- Metrics (collect trends + anomalies keyed by metric name) ---
    metrics_data: dict[str, dict[str, list]] = {}

    for met_spec in request.metrics:
        parts = met_spec.split(":")
        metric_name = parts[0]
        trend_specs = parts[1].split("+") if len(parts) > 1 else []

        trends: list[Trends] = []
        for spec in trend_specs:
            try:
                parsed = parse_trend_spec(spec)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            try:
                trend_cls = _trend_registry.get(parsed.name)
            except RegistryError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            try:
                trends.append(trend_cls(**parsed.kwargs))
            except TypeError as exc:
                bad_param = str(exc)
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid parameters for trend '{parsed.name}': {bad_param}",
                ) from exc

        if metric_name not in metrics_data:
            metrics_data[metric_name] = {"trends": [], "anomalies": []}
        metrics_data[metric_name]["trends"].extend(trends)

    # --- Anomalies ---
    for anom_spec in request.anomalies:
        parts = anom_spec.split(":", 1)
        metric_name = parts[0]
        spec_strings = parts[1].split("+") if len(parts) > 1 else []

        if metric_name not in metrics_data:
            metrics_data[metric_name] = {"trends": [], "anomalies": []}

        for spec in spec_strings:
            try:
                parsed = parse_anomaly_spec(spec)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            try:
                anom_cls = _anomaly_registry.get(parsed.name)
            except RegistryError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            if parsed.name == "ConceptDrift":
                segment = DriftSegment(**parsed.kwargs)
                existing = metrics_data[metric_name]["anomalies"]
                found_cd = next(
                    (a for a in existing if isinstance(a, ConceptDrift)), None
                )
                if found_cd is not None:
                    found_cd.segments.append(segment)
                else:
                    metrics_data[metric_name]["anomalies"].append(
                        ConceptDrift(segments=[segment])
                    )
            else:
                try:
                    metrics_data[metric_name]["anomalies"].append(
                        anom_cls(**parsed.kwargs)
                    )
                except TypeError as exc:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid parameters for anomaly '{parsed.name}': {exc}",
                    ) from exc

    # --- Add metrics to DataGen ---
    for metric_name, data in metrics_data.items():
        try:
            dg.add_metric(
                name=metric_name,
                trends=data["trends"],
                anomalies=data["anomalies"] if data["anomalies"] else None,
            )
        except (MetricError, ValidationError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return dg


# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------

_HOME_PAGE_PATH = Path(__file__).parent / "home.html"


def _get_home_page() -> str:
    """Load the home page HTML and inject the current version."""
    return _HOME_PAGE_PATH.read_text().replace("{{version}}", __version__)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    """Serve the interactive home page."""
    return _get_home_page()


@app.get("/logo.svg")
def logo() -> Response:
    """Serve the tsdata logo SVG."""
    svg = (Path(__file__).parent / "tsdata-logo.svg").read_bytes()
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check and version info (JSON)."""
    return {"status": "ok", "version": __version__}


@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    """Generate synthetic time series data and return as JSON.

    Accepts a request body with the same field format as the CLI
    JSON config file.
    """
    try:
        dg = _build_datagen(request)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        df = dg.data
        if df.empty:
            raise HTTPException(
                status_code=400, detail="No data generated. Check your parameters."
            )

        # Convert DataFrame to list of dicts with datetime index as a field
        records = df.reset_index().to_dict(orient="records")
        # Convert Timestamp values to ISO strings for JSON serialization
        for record in records:
            for key, value in record.items():
                if hasattr(value, "isoformat"):
                    record[key] = value.isoformat()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Data generation error: {exc}"
        ) from exc

    return GenerateResponse(
        rows=len(df),
        columns=list(df.columns),
        granularity=request.granularity,
        seed=request.seed,
        data=records,
    )


@app.post("/generate/preset/{preset_name}", response_model=GenerateResponse)
def generate_from_preset(
    preset_name: str,
    overrides: PresetGenerateRequest | None = None,
) -> GenerateResponse:
    """Generate data from a named preset with optional overrides.

    Available presets: daily-sales, hourly-metrics, minute-stock,
    weekly-revenue, monthly-recurring.
    """
    if preset_name not in PRESETS:
        raise HTTPException(
            status_code=404, detail=f"Preset '{preset_name}' not found."
        )

    preset = PRESETS[preset_name]

    # Build GenerateRequest from preset + overrides
    try:
        request = GenerateRequest(
            start=overrides.start if overrides and overrides.start else preset.start,
            end=overrides.end if overrides and overrides.end else preset.end,
            granularity=(
                overrides.granularity
                if overrides and overrides.granularity
                else preset.granularity
            ),
            dimensions=list(preset.dimensions),
            metrics=list(preset.metrics),
            anomalies=list(preset.anomalies),
            seed=overrides.seed if overrides and overrides.seed is not None else None,
        )
    except PydanticValidationError as exc:
        # ValidationError from pydantic - return 422 with details
        errors = exc.errors()
        error_messages = []
        for error in errors:
            loc = ".".join(str(x) for x in error.get("loc", []))
            msg = error.get("msg", str(error))
            error_messages.append(f"{loc}: {msg}")
        raise HTTPException(
            status_code=422,
            detail="\n".join(error_messages),
        ) from exc
    except Exception as exc:
        # Any other exception - return 500
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        return generate(request)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/presets", response_model=list[PresetSummary])
def list_presets() -> list[PresetSummary]:
    """List all available preset configurations."""
    try:
        summaries = []
        for name, preset in PRESETS.items():
            summaries.append(
                PresetSummary(
                    name=name,
                    start=preset.start,
                    end=preset.end,
                    granularity=preset.granularity,
                    dimensions_count=len(preset.dimensions),
                    metrics_count=len(preset.metrics),
                )
            )
        return summaries
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/presets/{preset_name}", response_model=PresetDetail)
def get_preset(preset_name: str) -> PresetDetail:
    """Get the full configuration for a named preset."""
    if preset_name not in PRESETS:
        raise HTTPException(
            status_code=404, detail=f"Preset '{preset_name}' not found."
        )
    try:
        preset = PRESETS[preset_name]
        return PresetDetail(name=preset_name, config=asdict(preset))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
