"""Integration tests for FastAPI REST API endpoints."""

import time
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "initializing")
    if data["status"] == "ok":
        assert data["brain_loaded"] is True
        assert "runtime_neurons" in data


def test_brain_info_endpoint():
    resp = client.get("/api/v1/brain")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dataset"] == "MaleCNS v1.0"
    assert "runtime_neurons" in data
    assert "runtime_edges" in data
    assert "input_neurons" in data
    assert "readout_neurons" in data


def test_demos_endpoints():
    # List demos
    resp = client.get("/api/v1/demos")
    assert resp.status_code == 200
    demos = resp.json()["demos"]
    assert len(demos) == 3
    demo_ids = [d["id"] for d in demos]
    assert "lorenz" in demo_ids
    assert "seasonal" in demo_ids
    assert "oscillator" in demo_ids

    # Download demo CSV
    resp_csv = client.get("/api/v1/demos/lorenz/csv")
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    assert b"x_chaotic" in resp_csv.content


def test_experiment_lifecycle():
    # 1. Submit experiment with demo_id
    resp = client.post(
        "/api/v1/experiments",
        data={
            "demo_id": "lorenz",
            "forecast_horizon": "5",
            "run_control": "true",
        },
    )
    assert resp.status_code == 200
    created = resp.json()
    exp_id = created["id"]
    assert exp_id is not None
    assert created["status"] == "queued"

    # 2. Poll for completion
    completed = False
    for _ in range(60):
        st_resp = client.get(f"/api/v1/experiments/{exp_id}")
        assert st_resp.status_code == 200
        st_data = st_resp.json()
        if st_data["status"] == "complete":
            completed = True
            break
        elif st_data["status"] == "failed":
            pytest.fail(f"Experiment failed: {st_data.get('error')}")
        time.sleep(0.5)

    assert completed, "Experiment did not complete within timeout"

    # 3. Retrieve results
    res_resp = client.get(f"/api/v1/experiments/{exp_id}/results")
    assert res_resp.status_code == 200
    res_data = res_resp.json()
    assert res_data["status"] == "complete"
    assert "result" in res_data
    assert "chart" in res_data
    assert res_data["result"]["winner"] in ("fly", "persistence", "autoregressive", "control")

    # 4. Download predictions CSV
    csv_resp = client.get(f"/api/v1/experiments/{exp_id}/predictions.csv")
    assert csv_resp.status_code == 200
    assert b"flycast" in csv_resp.content

    # 5. Download experiment JSON
    json_resp = client.get(f"/api/v1/experiments/{exp_id}/experiment.json")
    assert json_resp.status_code == 200
    assert json_resp.json()["experiment_id"] == exp_id

    # 6. Delete experiment
    del_resp = client.delete(f"/api/v1/experiments/{exp_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"
