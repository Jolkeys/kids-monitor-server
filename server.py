import os
import sqlite3
import time
import hashlib
from flask import Flask, request, jsonify, send_from_directory, render_template_string, abort

app = Flask(__name__)

# ---------------- CONFIG ----------------
UPLOAD_DIR = "/tmp/screens"
DB_FILE = "/tmp/monitor.db"
SECRET_TOKEN = "CHANGE_THIS_TO_SECURE_KEY"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- DB ----------------
def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            window_title TEXT,
            screenshot TEXT,
            allowed INTEGER,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- SECURITY ----------------
def verify_token(req):
    token = req.headers.get("Authorization")
    return token == f"Bearer {SECRET_TOKEN}"

# ---------------- SIMPLE AI HOOK ----------------
def analyze_content(title):
    unsafe = ["youtube", "tiktok", "instagram", "facebook", "roblox", "porn", "xvideos"]

    t = title.lower()
    for w in unsafe:
        if w in t:
            return False, f"Blocked: {w}"

    return True, "Safe"

# ---------------- UPLOAD ENDPOINT ----------------
@app.route("/api/upload", methods=["POST"])
def upload():
    if not verify_token(request):
        return jsonify({"error": "Unauthorized"}), 403

    device_id = request.form.get("device_id", "unknown")
    title = request.form.get("window_title", "idle")
    file = request.files.get("screenshot")

    filename = None

    if file:
        filename = f"{device_id}_{int(time.time())}.jpg"
        path = os.path.join(UPLOAD_DIR, filename)
        file.save(path)

    allowed, reason = analyze_content(title)

    conn = db()
    c = conn.cursor()

    c.execute("""
        INSERT INTO logs (device_id, window_title, screenshot, allowed, reason)
        VALUES (?, ?, ?, ?, ?)
    """, (device_id, title, filename, int(allowed), reason))

    conn.commit()
    conn.close()

    return jsonify({
        "allowed": allowed,
        "reason": reason
    })

# ---------------- IMAGE SERVER ----------------
@app.route("/screens/<filename>")
def screens(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ---------------- DASHBOARD ----------------
@app.route("/")
def dashboard():
    conn = db()
    c = conn.cursor()

    c.execute("SELECT DISTINCT device_id FROM logs")
    devices = c.fetchall()

    html = "<h1>AI Monitoring System</h1>"

    for d in devices:
        device = d["device_id"]

        c.execute("""
            SELECT * FROM logs
            WHERE device_id=?
            ORDER BY id DESC
            LIMIT 15
        """, (device,))

        logs = c.fetchall()

        html += f"<h2>Device: {device}</h2>"

        for log in logs:
            img = ""
            if log["screenshot"]:
                img = f'<br><img src="/screens/{log["screenshot"]}" width="250">'

            color = "green" if log["allowed"] else "red"

            html += f"""
            <div style="border:1px solid #ccc; margin:10px; padding:10px;">
                <b>{log['timestamp']}</b><br>
                🖥 {log['window_title']}<br>
                <span style="color:{color}">{log['reason']}</span>
                {img}
            </div>
            """

    return html

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
