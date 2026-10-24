import sqlite3
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)
DB = "food.db"
WARN_DAYS = 3  # items expiring within this many days are "soon"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                quantity INTEGER DEFAULT 1,
                location TEXT,
                expiry_date TEXT NOT NULL
            )
        """)


def with_status(row):
    item = dict(row)
    expiry = datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
    days_left = (expiry - date.today()).days
    item["days_left"] = days_left
    if days_left < 0:
        item["status"] = "expired"
    elif days_left <= WARN_DAYS:
        item["status"] = "soon"
    else:
        item["status"] = "fresh"
    return item


def fetch_items(search=""):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM items WHERE name LIKE ? ORDER BY expiry_date ASC",
            (f"%{search}%",),
        ).fetchall()
    return [with_status(r) for r in rows]


@app.route("/")
def index():
    search = request.args.get("q", "").strip()
    items = fetch_items(search)
    counts = {
        "total": len(items),
        "fresh": sum(i["status"] == "fresh" for i in items),
        "soon": sum(i["status"] == "soon" for i in items),
        "expired": sum(i["status"] == "expired" for i in items),
    }
    return render_template("index.html", items=items, counts=counts, search=search)


@app.route("/add", methods=["POST"])
def add():
    name = request.form["name"].strip()
    expiry = request.form["expiry_date"]
    if name and expiry:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO items (name, category, quantity, location, expiry_date) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    name,
                    request.form.get("category", ""),
                    int(request.form.get("quantity") or 1),
                    request.form.get("location", ""),
                    expiry,
                ),
            )
    return redirect(url_for("index"))


@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id):
    with get_db() as conn:
        conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    return redirect(url_for("index"))


@app.route("/api/items")
def api_items():
    return jsonify(fetch_items())


if __name__ == "__main__":
    init_db()
    app.run(debug=True)