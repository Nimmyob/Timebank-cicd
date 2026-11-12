import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")

import pytest
import app as skills_app


@pytest.fixture()
def client():
    return skills_app.app.test_client()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json()["service"] == "skills"


def test_seed_data_and_categories(client):
    assert len(client.get("/offers").get_json()) >= 7
    assert "Music" in client.get("/categories").get_json()


def test_create_and_get_offer(client):
    r = client.post("/offers", json={"member": "Test", "title": "Chess lessons", "category": "Other", "hours": 2})
    assert r.status_code == 201
    oid = r.get_json()["id"]
    got = client.get(f"/offers/{oid}").get_json()
    assert got["title"] == "Chess lessons" and got["hours"] == 2


@pytest.mark.parametrize("body", [
    {"member": "T", "title": "", "category": "Other", "hours": 1},
    {"member": "T", "title": "x", "category": "Nope", "hours": 1},
    {"member": "T", "title": "x", "category": "Other", "hours": 9},
    {"title": "x", "category": "Other", "hours": 1},
])
def test_create_validation(client, body):
    assert client.post("/offers", json=body).status_code == 400


def test_filter_and_search(client):
    assert all(o["category"] == "Music" for o in client.get("/offers?category=Music").get_json())
    assert any("yoga" in o["title"].lower() for o in client.get("/offers?q=yoga").get_json())


def test_missing_offer_is_404(client):
    assert client.get("/offers/999999").status_code == 404


def test_only_owner_can_delete(client):
    oid = client.post("/offers", json={"member": "Owner", "title": "Temp", "category": "Other", "hours": 1}).get_json()["id"]
    assert client.delete(f"/offers/{oid}?member=Someone").status_code == 404
    assert client.delete(f"/offers/{oid}?member=Owner").status_code == 200
