"""skills-service: the catalogue of skills neighbours offer, priced in hours."""
from flask import Flask, jsonify, request
import db

app = Flask(__name__)
CATEGORIES = ["Music", "Language", "Tech", "Cooking", "Crafts", "Fitness", "Home & Repair", "Other"]

SEED = [
    ("Anjali", "Guitar basics for beginners", "Music", "Chords, strumming, your first three songs.", 1),
    ("Rahul", "Conversational English practice", "Language", "Relaxed 1:1 chat to build confidence.", 1),
    ("Meera", "Build your first website", "Tech", "HTML + CSS from zero, bring a laptop.", 2),
    ("Joseph", "Kerala fish curry masterclass", "Cooking", "Cook it together, eat it together.", 2),
    ("Fatima", "Crochet a small amigurumi", "Crafts", "Yarn provided. Pick an animal!", 2),
    ("Arun", "Fix a leaking tap or switch", "Home & Repair", "Basic plumbing/electrical help at your home.", 1),
    ("Divya", "Morning yoga session", "Fitness", "Gentle 60 min flow, all levels.", 1),
]


def init():
    db.wait_for_db()
    db.run(f"""CREATE TABLE IF NOT EXISTS offers (
        id {db.PK}, member TEXT NOT NULL, title TEXT NOT NULL, category TEXT NOT NULL,
        description TEXT DEFAULT '', hours INTEGER NOT NULL)""")
    row, _ = db.run("SELECT COUNT(*) AS n FROM offers", fetch="one")
    if list(row.values())[0] == 0:
        for s in SEED:
            db.run("INSERT INTO offers (member,title,category,description,hours) VALUES (%s,%s,%s,%s,%s)", s)


@app.get("/health")
def health():
    db.run("SELECT 1")
    return {"status": "ok", "service": "skills"}


@app.get("/categories")
def categories():
    return jsonify(CATEGORIES)


@app.get("/offers")
def list_offers():
    cat, q = request.args.get("category"), request.args.get("q", "").strip().lower()
    sql, args = "SELECT * FROM offers WHERE 1=1", []
    if cat:
        sql += " AND category=%s"
        args.append(cat)
    if q:
        sql += " AND (LOWER(title) LIKE %s OR LOWER(description) LIKE %s)"
        args += [f"%{q}%"] * 2
    rows, _ = db.run(sql + " ORDER BY id DESC", args, "all")
    return jsonify(rows)


@app.get("/offers/<int:oid>")
def get_offer(oid):
    row, _ = db.run("SELECT * FROM offers WHERE id=%s", (oid,), "one")
    return (jsonify(row), 200) if row else (jsonify(error="offer not found"), 404)


@app.post("/offers")
def create_offer():
    d = request.get_json(silent=True) or {}
    member, title = str(d.get("member", "")).strip(), str(d.get("title", "")).strip()
    cat, desc = d.get("category", "Other"), str(d.get("description", "")).strip()[:300]
    try:
        hours = int(d.get("hours", 1))
    except (TypeError, ValueError):
        hours = 0
    if not member or not title or cat not in CATEGORIES or not 1 <= hours <= 5:
        return jsonify(error="member, title, valid category and hours (1-5) are required"), 400
    row, _ = db.run(
        "INSERT INTO offers (member,title,category,description,hours) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (member, title[:80], cat, desc, hours), "one")
    return jsonify(id=row["id"]), 201


@app.delete("/offers/<int:oid>")
def delete_offer(oid):
    member = request.args.get("member", "")
    _, n = db.run("DELETE FROM offers WHERE id=%s AND member=%s", (oid, member))
    return (jsonify(deleted=True), 200) if n else (jsonify(error="not found or not yours"), 404)


init()
