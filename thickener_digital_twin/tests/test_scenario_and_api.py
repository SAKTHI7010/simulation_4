"""Integration tests for scenario analysis, FastAPI REST endpoints, and HTML pages."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_and_config_endpoints():
    h = client.get("/api/health")
    assert h.status_code == 200
    assert h.json()["status"] == "ok"

    c = client.get("/api/config")
    assert c.status_code == 200
    assert c.json()["metadata"]["data_status"] == "SYNTHETIC_UNVALIDATED"


def test_simulation_flux_dynamics_pump_mc_endpoints():
    assert client.post("/api/simulate", json={}).status_code == 200
    assert client.post("/api/flux", json={}).status_code == 200
    assert client.post("/api/dynamics", json={"duration_h": 6.0}).status_code == 200
    assert client.post("/api/pumpability", json={"underflow_solids_wt_pct": 63.0}).status_code == 200
    assert client.post("/api/monte-carlo", json={"n_simulations": 60, "random_seed": 42}).status_code == 200


def test_scenario_endpoint_project4_operator_question():
    resp = client.post("/api/scenario", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["deltas"]["dry_solids_feed_tph"]["pct_delta"] > 19.0
    assert data["deltas"]["flocculant_dose_gpt"]["pct_delta"] < -49.0
    assert data["deltas"]["limiting_flux_kg_m2_h"]["abs_delta"] < 0.0


def test_all_six_frontend_pages_served():
    for path in [
        "/",
        "/index.html",
        "/pages/flux.html",
        "/pages/dynamics.html",
        "/pages/pumpability.html",
        "/pages/monte_carlo.html",
        "/pages/scenario.html",
    ]:
        r = client.get(path)
        assert r.status_code == 200
        assert "Thickener Digital Twin" in r.text
