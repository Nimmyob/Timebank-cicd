"""ledger-service: members, time-credit balances and bookings (credit transfers)."""
import os
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request
import db

SKILLS_URL = os.environ.get("SKILLS_URL", "http://localhost:5001")
WELCOME_CREDITS = 3

app = Flask(__name__)


def init():
    db.wait_for_db()
    db.run("CREATE TABLE IF NOT EXISTS members (name TEXT PRIMARY KEY, balance INTEGER NOT NULL CHECK (balance >= 0))")
    db.run(f"""CREATE TABLE IF NOT EXISTS transactions (
        id {db.PK}, ts TEXT NOT NULL, learner TEXT NOT NULL, provider TEXT NOT NULL,
        offer_id INTEGER NOT NULL, offer_title TEXT NOT NULL, hours INTEGER NOT NULL)""")


def ensure_member(name):
    db.run("INSERT INTO members (name, balance) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING", (name, WELCOME_CREDITS))
    row, _ = db.run("SELECT * FROM members WHERE name=%s", (name,), "one")
    return row


def clean(name):
    return str(name or "").strip()[:40]


@app.get("/health")
def health():
    db.run("SELECT 1")
    return {"status": "ok", "service": "ledger"}


@app.post("/members")
def join():
    name = clean((request.get_json(silent=True) or {}).get("name"))
    if not name:
        return jsonify(error="name required"), 400
    return jsonify(ensure_member(name))


@app.get("/members/<name>")
def member(name):
    return jsonify(ensure_member(clean(name)))


@app.post("/bookings")
def book():
    d = request.get_json(silent=True) or {}
    learner, oid = clean(d.get("learner")), d.get("offer_id")
    if not learner or not isinstance(oid, int):
        return jsonify(error="learner and offer_id required"), 400
    try:  # service-to-service call
        r = requests.get(f"{SKILLS_URL}/offers/{oid}", timeout=3)
    except requests.RequestException:
        return jsonify(error="skills service unavailable"), 503
    if r.status_code != 200:
        return jsonify(error="offer not found"), 404
    offer = r.json()
    provider, hours = offer["member"], offer["hours"]
    if provider.lower() == learner.lower():
        return jsonify(error="you can't book your own skill"), 400
    ensure_member(learner)
    ensure_member(provider)
    # Atomic guarded debit: fails if balance would go negative.
    _, n = db.run("UPDATE members SET balance=balance-%s WHERE name=%s AND balance>=%s", (hours, learner, hours))
    if not n:
        return jsonify(error=f"not enough credits - this needs {hours}h"), 402
    db.run("UPDATE members SET balance=balance+%s WHERE name=%s", (hours, provider))
    db.run("INSERT INTO transactions (ts,learner,provider,offer_id,offer_title,hours) VALUES (%s,%s,%s,%s,%s,%s)",
           (datetime.now(timezone.utc).isoformat(timespec="seconds"), learner, provider, oid, offer["title"], hours))
    bal, _ = db.run("SELECT balance FROM members WHERE name=%s", (learner,), "one")
    return jsonify(ok=True, balance=bal["balance"], provider=provider, hours=hours), 201


@app.get("/transactions")
def transactions():
    m = clean(request.args.get("member"))
    if m:
        rows, _ = db.run("SELECT * FROM transactions WHERE learner=%s OR provider=%s ORDER BY id DESC LIMIT 20", (m, m), "all")
    else:
        rows, _ = db.run("SELECT * FROM transactions ORDER BY id DESC LIMIT 10", (), "all")
    return jsonify(rows)


@app.get("/leaderboard")
def leaderboard():
    rows, _ = db.run("SELECT provider AS name, SUM(hours) AS hours_given FROM transactions "
                     "GROUP BY provider ORDER BY hours_given DESC LIMIT 5", (), "all")
    return jsonify(rows)


init()
