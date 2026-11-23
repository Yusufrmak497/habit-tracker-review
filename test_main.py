import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_create_and_list_habit():
    r = client.post("/habits", json={"name": "Read 20 minutes"})
    assert r.status_code == 200
    hid = r.json()["id"]
    r2 = client.get("/habits")
    assert r2.status_code == 200
    assert any(h["id"] == hid for h in r2.json())


def test_checkin_flow():
    hid = client.post("/habits", json={"name": "Stretch"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 200
    r2 = client.get(f"/habits/{hid}/checkins")
    assert r2.json() == ["2026-09-22"]


def test_checkin_unknown_habit_404():
    r = client.post("/habits/99999/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 404


def _error_messages(response) -> str:
    return " ".join(e["msg"] for e in response.json()["detail"])


@pytest.mark.parametrize("name", ["", "   ", "\t\n", "\u200b", "\u200b\u200d"])
def test_create_habit_rejects_empty_name(name):
    r = client.post("/habits", json={"name": name})
    assert r.status_code == 422
    assert "habit name must not be empty" in _error_messages(r)


def test_create_habit_rejects_missing_name():
    r = client.post("/habits", json={})
    assert r.status_code == 422


def test_create_habit_strips_whitespace():
    r = client.post("/habits", json={"name": "  Walk  "})
    assert r.status_code == 200
    assert r.json()["name"] == "Walk"


@pytest.mark.parametrize(
    "day", ["", "yesterday", "2026/09/22", "22-09-2026", "20260922", "2026-9-2"]
)
def test_checkin_rejects_malformed_day(day):
    hid = client.post("/habits", json={"name": "Meditate"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": day})
    assert r.status_code == 422
    assert "YYYY-MM-DD" in _error_messages(r)
    assert client.get(f"/habits/{hid}/checkins").json() == []


@pytest.mark.parametrize("day", ["2026-02-30", "2026-13-01", "2026-00-10"])
def test_checkin_rejects_impossible_date(day):
    hid = client.post("/habits", json={"name": "Journal"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": day})
    assert r.status_code == 422
    assert "not a valid calendar date" in _error_messages(r)
    assert client.get(f"/habits/{hid}/checkins").json() == []


def test_checkin_accepts_leap_day():
    hid = client.post("/habits", json={"name": "Run"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2028-02-29"})
    assert r.status_code == 200


def test_checkin_rejects_non_ascii_digits():
    hid = client.post("/habits", json={"name": "Read"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "٢٠٢٦-٠٩-٢٢"})
    assert r.status_code == 422
    assert "YYYY-MM-DD" in _error_messages(r)


def test_create_habit_rejects_too_long_name():
    r = client.post("/habits", json={"name": "x" * 101})
    assert r.status_code == 422
    assert "at most 100 characters" in _error_messages(r)


@pytest.mark.parametrize("body", [{"day": 20260922}, {"day": None}])
def test_checkin_rejects_wrong_json_type(body):
    hid = client.post("/habits", json={"name": "Typed"}).json()["id"]
    assert client.post(f"/habits/{hid}/checkin", json=body).status_code == 422
