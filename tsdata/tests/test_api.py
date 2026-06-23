"""Tests for the tsdata FastAPI application endpoints."""

import pytest
from fastapi.testclient import TestClient
from tsdata.main import app


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Home page & Health check
# ---------------------------------------------------------------------------


class TestHomeAndHealth:
    def test_home_page_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "html" in resp.headers["content-type"]
        assert "ts-data-generator" in resp.text

    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


# ---------------------------------------------------------------------------
# POST /generate
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_basic_generate(self, client):
        resp = client.post(
            "/generate",
            json={
                "start": "2024-01-01",
                "end": "2024-01-02",
                "granularity": "h",
                "dimensions": ["product:random_choice:A,B,C"],
                "metrics": ["sales:LinearTrend(slope=30)"],
                "seed": 42,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rows"] > 0
        assert "columns" in data
        assert "data" in data

    def test_generate_with_concept_drift(self, client):
        resp = client.post(
            "/generate",
            json={
                "start": "2024-01-01",
                "end": "2024-01-02",
                "granularity": "h",
                "metrics": ["value:LinearTrend(slope=1)"],
                "anomalies": [
                    "value:ConceptDrift(start_timestamp=2024-01-01T12:00:00,"
                    "target_mean=50,target_std=5,transition_window=1800,hold_duration=7200)"
                ],
                "seed": 42,
            },
        )
        assert resp.status_code == 200

    def test_generate_minimal(self, client):
        """Generate with no dimensions or anomalies."""
        resp = client.post(
            "/generate",
            json={
                "start": "2024-01-01",
                "end": "2024-01-02",
                "granularity": "D",
                "metrics": ["value:LinearTrend(slope=10)"],
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) > 0

    def test_generate_multiple_metrics(self, client):
        resp = client.post(
            "/generate",
            json={
                "start": "2024-01-01",
                "end": "2024-01-02",
                "granularity": "h",
                "metrics": [
                    "sales:LinearTrend(slope=30)",
                    "temperature:SinusoidalTrend(amplitude=10,freq=24)",
                ],
                "seed": 1,
            },
        )
        assert resp.status_code == 200
        columns = resp.json()["columns"]
        assert "sales" in columns
        assert "temperature" in columns

    def test_generate_invalid_granularity(self, client):
        resp = client.post(
            "/generate",
            json={
                "start": "2024-01-01",
                "end": "2024-01-02",
                "granularity": "invalid",
                "metrics": ["value:LinearTrend(slope=1)"],
            },
        )
        assert resp.status_code == 422

    def test_generate_invalid_trend(self, client):
        resp = client.post(
            "/generate",
            json={
                "start": "2024-01-01",
                "end": "2024-01-02",
                "granularity": "D",
                "metrics": ["value:NonExistentTrend(slope=1)"],
            },
        )
        assert resp.status_code == 400
        assert "NonExistentTrend" in resp.json()["detail"]

    def test_generate_invalid_dimension_function(self, client):
        resp = client.post(
            "/generate",
            json={
                "start": "2024-01-01",
                "end": "2024-01-02",
                "granularity": "D",
                "dimensions": ["region:nonexistent_func:US,EU"],
                "metrics": ["value:LinearTrend(slope=1)"],
            },
        )
        assert resp.status_code == 400

    def test_generate_with_random_int_dimension(self, client):
        """Dimension functions that require multiple args should be unpacked correctly."""
        resp = client.post(
            "/generate",
            json={
                "start": "2024-01-01",
                "end": "2024-01-02",
                "granularity": "h",
                "dimensions": ["batch_number:random_int:1,100"],
                "metrics": ["value:LinearTrend(slope=1)"],
                "seed": 42,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["rows"] > 0
        first_row = data["data"][0]
        assert isinstance(first_row["batch_number"], int)
        assert 1 <= first_row["batch_number"] <= 100

    def test_generate_invalid_anomaly(self, client):
        resp = client.post(
            "/generate",
            json={
                "start": "2024-01-01",
                "end": "2024-01-02",
                "granularity": "D",
                "metrics": ["value:LinearTrend(slope=1)"],
                "anomalies": ["value:FakeAnomaly(probability=0.01)"],
            },
        )
        assert resp.status_code == 400

    def test_generate_datetime_fields_in_response(self, client):
        """Datetime index should be serialized as ISO strings."""
        resp = client.post(
            "/generate",
            json={
                "start": "2024-01-01",
                "end": "2024-01-02",
                "granularity": "D",
                "metrics": ["value:LinearTrend(slope=1)"],
                "seed": 42,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "datetime" in data["columns"]
        first_row = data["data"][0]
        assert "datetime" in first_row
        assert isinstance(first_row["datetime"], str)
        assert "index" not in first_row


# ---------------------------------------------------------------------------
# POST /generate/preset/{name}
# ---------------------------------------------------------------------------


class TestGenerateFromPreset:
    def test_generate_from_preset(self, client):
        resp = client.post("/generate/preset/daily-sales")
        assert resp.status_code == 200
        data = resp.json()
        assert data["rows"] > 0
        assert data["seed"] is None  # presets have no seed by default

    def test_generate_from_preset_with_overrides(self, client):
        resp = client.post(
            "/generate/preset/daily-sales",
            json={"seed": 42},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["seed"] == 42

    def test_generate_from_preset_not_found(self, client):
        resp = client.post("/generate/preset/nonexistent")
        assert resp.status_code == 404

    def test_all_presets_are_generatable(self, client):
        """Every named preset should produce data without error."""
        for name in [
            "daily-sales",
            "hourly-metrics",
            "minute-stock",
            "weekly-revenue",
            "monthly-recurring",
            "scientific-mock",
            "economics-cycle",
            "sociology-mobility",
            "electronics-reliability",
            "epidemiology-wave",
        ]:
            resp = client.post(f"/generate/preset/{name}")
            assert resp.status_code == 200, f"Preset {name} failed: {resp.text}"


# ---------------------------------------------------------------------------
# GET /presets
# ---------------------------------------------------------------------------


class TestPresets:
    def test_list_presets(self, client):
        resp = client.get("/presets")
        assert resp.status_code == 200
        presets = resp.json()
        assert len(presets) > 0
        assert all("name" in p for p in presets)
        assert all("start" in p for p in presets)
        assert all("granularity" in p for p in presets)

    def test_get_preset_detail(self, client):
        resp = client.get("/presets/daily-sales")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["name"] == "daily-sales"
        assert "config" in detail
        assert "start" in detail["config"]

    def test_get_preset_not_found(self, client):
        resp = client.get("/presets/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /dimensions, /trends, /anomalies, /granularities
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_list_dimensions(self, client):
        resp = client.get("/dimensions")
        assert resp.status_code == 200
        dims = resp.json()
        assert len(dims) > 0
        names = [d["name"] for d in dims]
        assert "random_choice" in names

    def test_list_trends(self, client):
        resp = client.get("/trends")
        assert resp.status_code == 200
        trends = resp.json()
        assert len(trends) > 0
        names = [t["name"] for t in trends]
        assert "LinearTrend" in names

    def test_list_anomalies(self, client):
        resp = client.get("/anomalies")
        assert resp.status_code == 200
        anomalies = resp.json()
        assert len(anomalies) > 0
        names = [a["name"] for a in anomalies]
        assert "PointAnomaly" in names

    def test_list_granularities(self, client):
        resp = client.get("/granularities")
        assert resp.status_code == 200
        granularities = resp.json()
        assert len(granularities) == len(["s", "min", "5min", "h", "D", "W", "ME", "Y"])
        values = [g["value"] for g in granularities]
        assert "h" in values
        assert "D" in values
