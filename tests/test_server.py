from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fsort.config import Config
from fsort.models import Person
from fsort.server import app, progress_state
from fsort.service import FsortService


@pytest.fixture
def client_with_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[TestClient, FsortService]:
    cache = tmp_path / "cache"
    output = tmp_path / "output"
    config = Config()

    service = FsortService(cache, output, config)
    monkeypatch.setattr("fsort.server.get_service", lambda: service)

    client = TestClient(app)
    return client, service


def test_get_people_and_stats(
    client_with_service: tuple[TestClient, FsortService]
) -> None:
    client, service = client_with_service

    # Retrieve initial empty state
    resp = client.get("/people")
    assert resp.status_code == 200
    assert resp.json() == []

    resp = client.get("/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["people"] == 0
    assert stats["media_files"] == 0

    resp = client.get("/verify")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_maintenance_endpoints(
    client_with_service: tuple[TestClient, FsortService],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, service = client_with_service

    # Populate registry with a mock person
    person = Person.create("Person_001")
    service.store.save([person], {}, {})

    # Test GET /people returns the person
    resp = client.get("/people")
    assert resp.status_code == 200
    people = resp.json()
    assert len(people) == 1
    assert people[0]["display_name"] == "Person_001"

    # Mock FsortService methods to avoid side effects of folder sync during tests
    monkeypatch.setattr(
        service,
        "rename",
        lambda person_val, new_name, input_root=None: "Renamed OK",
    )
    monkeypatch.setattr(
        service,
        "merge",
        lambda target_val, source_val, input_root=None: "Merged OK",
    )
    monkeypatch.setattr(
        service,
        "split",
        lambda person_val, input_root=None: "Split OK",
    )

    # Test POST /rename
    resp = client.post(
        "/rename", json={"person": "Person_001", "new_name": "Mom"}
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Renamed OK"

    # Test POST /merge
    resp = client.post(
        "/merge", json={"target": "Person_001", "source": "Person_002"}
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Merged OK"

    # Test POST /split
    resp = client.post("/split", json={"person": "Person_001"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Split OK"


def test_extract_and_organize_endpoints(
    client_with_service: tuple[TestClient, FsortService],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, service = client_with_service
    source = tmp_path / "photos"
    source.mkdir()

    # Reset progress state
    global progress_state
    progress_state["status"] = "idle"
    progress_state["message"] = ""

    # Mock service.extract and service.organize
    monkeypatch.setattr(
        service,
        "extract",
        lambda input_root, show_progress=True, progress_callback=None: {
            "scanned": 1,
            "processed": 1,
            "skipped": 0,
            "failed": 0,
            "deleted": 0,
        },
    )
    monkeypatch.setattr(
        service,
        "organize",
        lambda input_root=None: {
            "assigned": 0,
            "people_created": 1,
            "files_written": 1,
            "files_removed": 0,
        },
    )

    # Test POST /organize
    resp = client.post("/organize", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["results"]["people_created"] == 1

    # Test POST /extract triggers background task
    resp = client.post("/extract", json={"input_root": str(source)})
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"

    # Verify progress state endpoint
    resp = client.get("/progress")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("running", "completed")


def test_new_api_endpoints(
    client_with_service: tuple[TestClient, FsortService],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, service = client_with_service

    # 1. Create a person via POST /api/person/create
    resp = client.post("/api/person/create", json={"name": "Alex"})
    assert resp.status_code == 200
    person_data = resp.json()["person"]
    assert person_data["display_name"] == "Alex"
    person_id = person_data["id"]

    # 2. Get the person details via GET /api/person/{id}
    resp = client.get(f"/api/person/{person_id}")
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Alex"

    # 3. List people via GET /api/people
    resp = client.get("/api/people?skip=0&limit=10&sort_by=name&order=asc")
    assert resp.status_code == 200
    res = resp.json()
    assert res["total"] == 3  # Alex, Unknown, Multiple Faces
    items = res["items"]
    ids = [item["id"] for item in items]
    assert "_unknown" in ids
    assert "_multiple" in ids
    assert person_id in ids

    # 4. Mock reassign_media and test POST /api/media/reassign
    monkeypatch.setattr(
        service,
        "reassign_media",
        lambda media_id, p_id, input_root=None: None,
    )
    resp = client.post("/api/media/reassign", json={"media_id": 42, "person_id": person_id})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # 5. Search for person
    resp = client.get("/api/search?query=Ale")
    assert resp.status_code == 200
    search_res = resp.json()
    assert len(search_res["people"]) == 1
    assert search_res["people"][0]["display_name"] == "Alex"
