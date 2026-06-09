
import os
import sqlite3
import time
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

# Configuration
UPLOAD_DIR = "/tmp/screens"
DB_FILE = "/tmp/monitor.db"
SECRET_TOKEN = "123"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Database Setup
def init_db():
    conn = sqlite3.connect(DB_FILE)
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

@app.route("/api/upload", methods=["POST"])
def upload():
    # Authentication check
    token = request.headers.get("Authorization")
    if token != f"Bearer {SECRET_TOKEN}":
        return jsonify({"error": "Unauthorized"}), 403

    device_id = request.form.get("device_id", "unknown")
    title = request.form.get("window_title", "idle")
    file = request.files.get("screenshot")

    filename = None
    if file:
        filename = f"{device_id}_{int(time.time())}.jpg"
        file.save(os.path.join(UPLOAD_DIR, filename))

    # Safety/Content logic
    unsafe = ["youtube", "tiktok", "roblox", "facebook", "game"]
    allowed = not any(word in title.lower() for word in unsafe)
    reason = "Safe" if allowed else "Blocked: Distraction detected"

    # Database Logging
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO logs (device_id, window_title, screenshot, allowed, reason) VALUES (?, ?, ?, ?, ?)",
              (device_id, title, filename, int(allowed), reason))
    conn.commit()
    conn.close()

    return jsonify({"allowed": allowed, "reason": reason})

@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 50")
    logs = c.fetchall()
    
    html = "<html><body><h1>Dashboard</h1>"
    for log in logs:
        color = "green" if log["allowed"] else "red"
        html += f"<div style='border:1px solid #ccc; margin:10px; padding:10px; color:{color}'><b>{log['timestamp']}</b> - {log['device_id']} - {log['reason']}</div>"
    return html + "</body></html>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
