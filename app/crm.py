"""Application tracker (CRM) stored in a local SQLite file."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "landed.db"
STATUSES = ["saved", "applied", "interview", "offer", "rejected"]
FOLLOW_UP_DAYS = 10

FIELDS = ["offer_id", "title", "company", "location", "url", "source", "score", "status",
          "notes", "contact", "applied_at", "next_step", "next_step_date", "letter", "cv_summary"]


def _conn():
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offer_id TEXT, title TEXT, company TEXT, location TEXT, url TEXT, source TEXT,
        score INTEGER, status TEXT DEFAULT 'saved', notes TEXT DEFAULT '', contact TEXT DEFAULT '',
        applied_at TEXT, next_step TEXT DEFAULT '', next_step_date TEXT,
        letter TEXT DEFAULT '', cv_summary TEXT DEFAULT '',
        created_at TEXT, updated_at TEXT)""")
    return c


def _row(r) -> dict:
    d = dict(r)
    d["follow_up"] = False
    if d["status"] == "applied" and d.get("applied_at"):
        try:
            days = (date.today() - date.fromisoformat(d["applied_at"][:10])).days
            d["days_since_applied"] = days
            d["follow_up"] = days >= FOLLOW_UP_DAYS
        except ValueError:
            pass
    return d


def list_all() -> list[dict]:
    with _conn() as c:
        return [_row(r) for r in c.execute("SELECT * FROM applications ORDER BY updated_at DESC")]


def get(app_id: int) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()
        return _row(r) if r else None


def create(data: dict) -> dict:
    now = datetime.now().isoformat(timespec="seconds")
    existing = None
    if data.get("offer_id"):
        with _conn() as c:
            r = c.execute("SELECT id FROM applications WHERE offer_id=?", (data["offer_id"],)).fetchone()
            existing = r["id"] if r else None
    if existing:  # already tracked: update instead of duplicating
        return update(existing, data)

    vals = {k: data.get(k) for k in FIELDS}
    vals["status"] = vals["status"] if vals["status"] in STATUSES else "saved"
    if vals["status"] == "applied" and not vals["applied_at"]:
        vals["applied_at"] = date.today().isoformat()
    cols = ", ".join(vals) + ", created_at, updated_at"
    q = ", ".join("?" for _ in vals) + ", ?, ?"
    with _conn() as c:
        cur = c.execute(f"INSERT INTO applications ({cols}) VALUES ({q})", [*vals.values(), now, now])
        new_id = cur.lastrowid
    return get(new_id)


def update(app_id: int, data: dict) -> dict:
    vals = {k: v for k, v in data.items() if k in FIELDS and v is not None}
    if "status" in vals:
        if vals["status"] not in STATUSES:
            raise ValueError("unknown status")
        cur = get(app_id)
        if vals["status"] == "applied" and cur and not cur.get("applied_at"):
            vals["applied_at"] = date.today().isoformat()
    if not vals:
        return get(app_id)
    vals["updated_at"] = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        c.execute(f"UPDATE applications SET {', '.join(k + '=?' for k in vals)} WHERE id=?",
                  [*vals.values(), app_id])
    return get(app_id)


def delete(app_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM applications WHERE id=?", (app_id,))


def stats() -> dict:
    apps = list_all()
    by = {s: sum(1 for a in apps if a["status"] == s) for s in STATUSES}
    sent = sum(by[s] for s in ("applied", "interview", "offer", "rejected"))
    answered = by["interview"] + by["offer"] + by["rejected"]
    scores = [a["score"] for a in apps if a.get("score") is not None]
    return {
        "total": len(apps),
        "by_status": by,
        "sent": sent,
        "response_rate": round(100 * answered / sent) if sent else 0,
        "interview_rate": round(100 * (by["interview"] + by["offer"]) / sent) if sent else 0,
        "avg_score": round(sum(scores) / len(scores)) if scores else 0,
        "follow_ups": [a for a in apps if a["follow_up"]],
    }
