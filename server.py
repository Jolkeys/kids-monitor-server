```python
import os
import sqlite3
import time
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

# ---------------- CONFIG ----------------
UPLOAD_DIR = "/tmp/screens"
DB_FILE = "/tmp/monitor.db"

# Change this to your own secret key
SECRET_TOKEN = "CHANGE_THIS_TO_SECURE_KEY"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- DATABASE ----------------
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

    # During testing, allow requests without token.
    # Remove this block later if you want strict security.
    if not token:
        return True

    return token == f"Bearer {SECRET_TOKEN}"

# ---------------- AI CHECK ----------------
def analyze_content(title):
    title = (title or "").lower()

    unsafe = [
        "youtube",
        "tiktok",
        "instagram",
        "facebook",
        "roblox",
        "porn",
        "xvideos"
    ]

    for word in unsafe:
        if word in title:
            return False, f"Blocked: {word}"

    return True, "Safe"

# ---------------- HEALTH CHECK ----------------
@app.route("/health")
def health():
    return jsonify({
        "status": "online"
    })

# ---------------- UPLOAD ENDPOINTS ----------------
@app.route("/", methods=["POST"])
@app.route("/analyze", methods=["POST"])
@app.route("/api/upload", methods=["POST"])
def upload():

    if not verify_token(request):
        return jsonify({
            "error": "Unauthorized"
        }), 403

    device_id = request.form.get("device_id", "unknown")
    title = request.form.get("window_title", "idle")
    file = request.files.get("screenshot")

    filename = None

    try:
        if file:
            filename = f"{device_id}_{int(time.time())}.jpg"

            path = os.path.join(UPLOAD_DIR, filename)

            file.save(path)

        allowed, reason = analyze_content(title)

        conn = db()
        c = conn.cursor()

        c.execute("""
            INSERT INTO logs
            (device_id, window_title, screenshot, allowed, reason)
            VALUES (?, ?, ?, ?, ?)
        """, (
            device_id,
            title,
            filename,
            int(allowed),
            reason
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "allowed": allowed,
            "reason": reason,
            "device_id": device_id
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

# ---------------- SERVE SCREENSHOTS ----------------
@app.route("/screens/<filename>")
def screens(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():

    conn = db()
    c = conn.cursor()

    c.execute("""
        SELECT *
        FROM logs
        ORDER BY id DESC
        LIMIT 100
    """)

    logs = c.fetchall()

    html = """
    <html>
    <head>
        <title>Kids Monitor Dashboard</title>
        <meta http-equiv="refresh" content="10">
    </head>
    <body>
        <h1>Kids Monitor Dashboard</h1>
    """

    for log in logs:

        color = "green" if log["allowed"] else "red"

        html += f"""
        <div style="border:1px solid #ccc;padding:10px;margin:10px;">
            <b>Device:</b> {log['device_id']}<br>
            <b>Time:</b> {log['timestamp']}<br>
            <b>Window:</b> {log['window_title']}<br>
            <b>Status:</b>
            <span style="color:{color}">
                {log['reason']}
            </span>
        """

        if log["screenshot"]:
            html += f"""
            <br><br>
            <img src="/screens/{log['screenshot']}" width="300">
            """

        html += "</div>"

    html += """
    </body>
    </html>
    """

    conn.close()

    return html

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
```
