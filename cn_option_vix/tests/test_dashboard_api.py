from fastapi.testclient import TestClient

from cn_option_vix.web import app as web_app
from cn_option_vix.web.storage import upsert_points


def test_dashboard_api_serves_both_resolutions(tmp_path, monkeypatch):
    db = tmp_path / "live.sqlite"
    monkeypatch.setattr(web_app, "DB_PATH", db)
    row = {
        "timestamp": "2026-07-14 14:35",
        "overall": 20.0,
        "index_vix": 21.0,
        "blue_chip": 19.0,
        "sz_growth": 23.0,
        "mid_small": 24.0,
        "hard_tech": 26.0,
        "n_instruments": 12,
        "expected_instruments": 12,
    }
    upsert_points([row], resolution="5m", source="test", db_path=db)
    half = dict(row, timestamp="2026-07-14 11:30", session="AM")
    upsert_points([half], resolution="halfday", source="test", db_path=db)

    client = TestClient(web_app.app)
    latest = client.get("/api/latest")
    assert latest.status_code == 200
    assert len(latest.json()["cards"]) == 6
    assert latest.json()["cards"][-1]["spread"] == 6.0

    five = client.get("/api/series", params={"resolution": "5m"})
    halfday = client.get("/api/series", params={"resolution": "halfday"})
    assert five.json()["count"] == 1
    assert halfday.json()["count"] == 1


def test_dashboard_api_exposes_averages_and_ytd(tmp_path, monkeypatch):
    db = tmp_path / "live.sqlite"
    monkeypatch.setattr(web_app, "DB_PATH", db)
    rows = []
    for i, day in enumerate(__import__('pandas').bdate_range("2026-01-02", periods=60)):
        rows.append({
            "timestamp": f"{day.date()} 15:00",
            "overall": 20.0 + i / 10,
            "index_vix": 21.0 + i / 10,
            "blue_chip": 19.0 + i / 10,
            "sz_growth": 23.0 + i / 10,
            "mid_small": 24.0 + i / 10,
            "hard_tech": 26.0 + i / 10,
            "n_instruments": 12,
            "expected_instruments": 12,
            "session": "PM",
        })
    upsert_points(rows, resolution="halfday", source="test", db_path=db)
    live = dict(rows[-1], timestamp="2026-07-14 14:35")
    upsert_points([live], resolution="5m", source="test", db_path=db)

    client = TestClient(web_app.app)
    averages = client.get("/api/averages")
    assert averages.status_code == 200
    payload = averages.json()
    assert len(payload["rows"]) == 6
    assert payload["rows"][0]["count_30"] == 30
    assert payload["rows"][0]["count_60"] == 60

    halfday = client.get("/api/series", params={"resolution": "halfday"})
    assert halfday.status_code == 200
    assert halfday.json()["points"][0]["timestamp"].startswith("2026-")
