import json
import os
import threading
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from . import summary_generator


PACKAGE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DAILY_SUMMARY_DATA_DIR", PACKAGE_DIR / "data"))
SUMMARY_DIR = DATA_DIR / "summaries"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

ENABLE_COLLECTOR = os.getenv("DAILY_SUMMARY_ENABLE_COLLECTOR", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ENABLE_DIGEST_SCHEDULER = os.getenv(
    "DAILY_SUMMARY_ENABLE_DIGEST_SCHEDULER", "true"
).strip().lower() in {"1", "true", "yes", "on"}
DIGEST_INTERVAL_MINUTES = max(
    5, int(os.getenv("DAILY_SUMMARY_DIGEST_INTERVAL_MINUTES", "30"))
)

LIVE_FILES = {
    "a_share": "jin10_live_scored_a.jsonl",
    "us_stock": "jin10_live_scored_us.jsonl",
    "a_share_digest": "jin10_gate_a_digest.jsonl",
    "us_analyst_digest": "jin10_us_analyst_digest.jsonl",
    "forex": "forex_digest.jsonl",
    "commodity": "jin10_commodity_scored.jsonl",
}

app = FastAPI(title="YSJ Daily Summary", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def read_jsonl(path: Path, limit: int = 1000) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows[-limit:]


def parse_time(row: dict[str, Any]) -> datetime:
    raw = str(row.get("time", ""))
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(raw[:19], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return datetime.min


def dedupe_latest(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    dedup: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("id") or row.get("content") or len(dedup))
        dedup[key] = row
    latest = sorted(dedup.values(), key=parse_time, reverse=True)
    return latest[:limit]


def public_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "time": row.get("time", ""),
        "content": row.get("content", ""),
        "market": row.get("score_market") or row.get("market", ""),
        "important": row.get("important", 0),
        "claude_score": row.get("claude_score"),
        "claude_confidence": row.get("claude_confidence"),
        "claude_reasoning": row.get("claude_reasoning", ""),
        "claude_gate_triggered": row.get("claude_gate_triggered"),
        "classify_names": row.get("classify_names", []),
        "cat5_commodity_type": row.get("cat5_commodity_type"),
    }


def latest_summary_payload() -> dict[str, Any] | None:
    path = SUMMARY_DIR / "daily_summary_latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def digest_loop() -> None:
    while True:
        try:
            summary_generator.generate(date.today().strftime("%Y-%m-%d"))
        except Exception as exc:
            print(f"[daily-summary-digest] failed: {exc}")
        time.sleep(DIGEST_INTERVAL_MINUTES * 60)


def collector_loop() -> None:
    try:
        from . import collector

        collector.main()
    except Exception as exc:
        print(f"[daily-summary-collector] failed: {exc}")


@app.on_event("startup")
def startup_event() -> None:
    if ENABLE_DIGEST_SCHEDULER:
        threading.Thread(target=digest_loop, daemon=True).start()

    if ENABLE_COLLECTOR:
        threading.Thread(target=collector_loop, daemon=True).start()


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "daily-summary",
        "time": datetime.now().isoformat(timespec="seconds"),
        "data_dir": str(DATA_DIR),
        "collector_enabled": ENABLE_COLLECTOR,
        "collector_configured": bool(os.getenv("JIN10_SECRET_KEY")),
        "claude_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
        "digest_scheduler_enabled": ENABLE_DIGEST_SCHEDULER,
        "files": {
            key: {
                "path": str(DATA_DIR / filename),
                "exists": (DATA_DIR / filename).exists(),
                "bytes": (DATA_DIR / filename).stat().st_size
                if (DATA_DIR / filename).exists()
                else 0,
            }
            for key, filename in LIVE_FILES.items()
        },
    }


@app.get("/api/daily-summary/live")
def live(limit: int = Query(80, ge=1, le=500)) -> dict[str, Any]:
    data = {}
    counts = {}
    for key, filename in LIVE_FILES.items():
        rows = dedupe_latest(read_jsonl(DATA_DIR / filename), limit=limit)
        data[key] = [public_record(row) for row in rows]
        counts[key] = len(rows)

    return {
        "status": "ok",
        "server_time": datetime.now().isoformat(timespec="seconds"),
        "data": data,
        "counts": counts,
    }


@app.get("/api/daily-summary/summary")
def summary() -> dict[str, Any]:
    payload = latest_summary_payload()
    if payload:
        payload["summary_available"] = True
        return payload

    return {
        "status": "empty",
        "summary_available": False,
        "date": date.today().strftime("%Y-%m-%d"),
        "generated_at": None,
        "summaries": {},
        "counts": {},
        "message": "No generated Daily Summary yet. Collector may still be warming up.",
    }


@app.post("/api/daily-summary/generate")
def generate(target_date: str | None = None) -> dict[str, Any]:
    try:
        return summary_generator.generate(target_date)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/daily_summary_latest.html", response_class=HTMLResponse)
def latest_html() -> HTMLResponse:
    path = SUMMARY_DIR / "daily_summary_latest.html"
    if not path.exists():
        return HTMLResponse("<p>No generated Daily Summary yet.</p>", status_code=404)
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/")
def root() -> JSONResponse:
    return JSONResponse({"ok": True, "service": "daily-summary"})
