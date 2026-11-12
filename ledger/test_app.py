import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")

import pytest
import requests
import app as ledger_app


class FakeResp:
    def __init__(self, status, data=None):
        self.status_code, self._data = status, data or {}

    def json(self):
        return self._data


@pytest.fixture()
def client():
    return ledger_app.app.test_client()


@pytest.fixture()
def fake_skills(monkeypatch):
    """Pretend the skills service has offer 1 (Teacher, 2h) and nothing else."""
    def fake_get(url, timeout=None):
        if url.endswith("/offers/1"):
            return FakeResp(200, {"id": 1, "member": "Teacher", "title": "Guitar", "hours": 2})
        return FakeResp(404)
    monkeypatch.setattr(ledger_app.requests, "get", fake_get)


def test_health(client):
    assert client.get("/health").get_json()["service"] == "ledger"


def test_new_member_gets_welcome_credits(client):
    assert client.get("/members/NewPerson").get_json()["balance"] == 3


def test_booking_moves_credits(client, fake_skills):
    r = client.post("/bookings", json={"learner": "Alice", "offer_id": 1})
    assert r.status_code == 201 and r.get_json()["balance"] == 1
    assert client.get("/members/Teacher").get_json()["balance"] == 5
    assert client.get("/transactions?member=Alice").get_json()[0]["offer_title"] == "Guitar"


def test_not_enough_credits(client, fake_skills):
    client.post("/bookings", json={"learner": "Bob", "offer_id": 1})      # 3 -> 1
    r = client.post("/bookings", json={"learner": "Bob", "offer_id": 1})  # needs 2, has 1
    assert r.status_code == 402
    assert client.get("/members/Bob").get_json()["balance"] == 1


def test_cannot_book_own_skill(client, fake_skills):
    assert client.post("/bookings", json={"learner": "teacher", "offer_id": 1}).status_code == 400


def test_unknown_offer(client, fake_skills):
    assert client.post("/bookings", json={"learner": "Carol", "offer_id": 42}).status_code == 404


def test_skills_service_down(client, monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError()
    monkeypatch.setattr(ledger_app.requests, "get", boom)
    assert client.post("/bookings", json={"learner": "Dave", "offer_id": 1}).status_code == 503


def test_bad_input(client):
    assert client.post("/bookings", json={}).status_code == 400


def test_leaderboard(client, fake_skills):
    client.post("/bookings", json={"learner": "Eve", "offer_id": 1})
    board = client.get("/leaderboard").get_json()
    assert board[0]["name"] == "Teacher"
