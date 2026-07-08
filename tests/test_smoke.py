import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient


def test_app_starts_with_temporary_database(monkeypatch, tmp_path):
    db_path = tmp_path / "akichance-test.db"
    monkeypatch.setenv("AKICHANCE_DB_PATH", str(db_path))

    import app as app_module

    reloaded = importlib.reload(app_module)
    client = TestClient(reloaded.app)

    response = client.get("/api/seats")
    assert response.status_code == 200
    assert response.json() == []

    seat_response = client.post(
        "/api/seats",
        json={"seat_number": "A1", "zone": "North", "is_active": True, "description": "Smoke test seat"},
    )
    assert seat_response.status_code == 201
    assert seat_response.json()["seat_number"] == "A1"
    assert db_path.exists()
    assert not Path("akichance.db").exists()
