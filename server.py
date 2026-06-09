import os
import sqlite3
import time
from flask import Flask, request, send_from_directory, render_template_string, jsonify

app = Flask(__name__)

# Use /tmp for Render (ephemeral storage)
STORAGE_ROOT = "/tmp"
UPLOAD_DIR = os.path.join(STORAGE_ROOT, "captured_screens")
DB_FILE = os.path.join(STORAGE_ROOT, "monitoring_database.sqlite")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# -----------------------------
# INIT DATABASE
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            window_title TEXT,
            screenshot_path TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# AI ANALYSIS PLACEHOLDER
# -----------------------------
def analyze_image(file_path, window_title):
    """
    THIS is where AI will go later.
    For now we simulate detection rules.
    """

    unsafe_keywords = [
        "youtube", "tiktok", "instagram", "facebook",
        "game", "roblox", "porn", "xvideos"
    ]

    title_lower = window_title.lower()

    for word in unsafe_keywords:
        if word in title_lower:
            return False, f"Blocked keyword detected: {word}"

    return True, "Safe activity"


# -----------------------------
# CLIENT UPLOAD + AI RESPONSE ENDPOINT
# -----------------------------
@app.route('/analyze', methods=['POST'])
def analyze():
    device_id = request.form.get("device_id", "Unknown_Laptop")
    window_title = request.form.get("window_title", "Desktop / Idle")
    file = request.files.get("screenshot")

    screenshot_path = ""

    if file:
        filename = f"{device_id}_{int(time.time())}.jpg"
        screenshot_path = os.path.join(UPLOAD_DIR, filename)
        file.save(screenshot_path)

    # Run AI analysis (currently rule-based)
    allowed, reason = analyze_image(screenshot_path, window_title)

    # Save log
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO activity_logs (device_id, window_title, screenshot_path)
        VALUES (?, ?, ?)
    """, (device_id, window_title, screenshot_path))
    conn.commit()
    conn.close()

    # Return decision to client
    return jsonify({
        "allowed": allowed,
        "reason": reason
    }), 200


# -----------------------------
# IMAGE SERVER
# -----------------------------
@app.route('/tmp/captured_screens/<filename>')
def serve_image(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# -----------------------------
# DASHBOARD
# -----------------------------
@app.route('/', methods=['GET'])
def dashboard():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT device_id FROM activity_logs")
    devices = cursor.fetchall()

    grid_html = ""

    for dev in devices:
        device_id = dev[0]

        cursor.execute("""
            SELECT window_title, screenshot_path, timestamp
            FROM activity_logs
            WHERE device_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        """, (device_id,))

        logs = cursor.fetchall()

        log_entries_html = ""

        for log in logs:
            win_title, img_path, ts = log

            filename = os.path.basename(img_path) if img_path else ""

            img_tag = ""
            if filename:
                img_tag = f'<img src="/tmp/captured_screens/{filename}" width="250">'

            log_entries_html += f"""
                <div style="border:1px solid #ddd; padding:10px; margin:10px;">
                    <div>🕒 {ts}</div>
                    <div>🖥️ {win_title}</div>
                    {img_tag}
                </div>
            """

        grid_html += f"""
        <div style="border:2px solid black; padding:10px; margin:10px;">
            <h3>💻 {device_id}</h3>
            {log_entries_html}
        </div>
        """

    conn.close()

    html = f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="10">
        <title>Monitor Dashboard</title>
    </head>
    <body>
        <h1>AI Monitoring Dashboard</h1>
        <div style="display:flex; flex-wrap:wrap;">
            {grid_html}
        </div>
    </body>
    </html>
    """

    return render_template_string(html)


# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
