import os
import sqlite3
import time
from flask import Flask, request, send_from_directory, render_template_string, jsonify

app = Flask(__name__)

# Use /tmp for storage on Render (Ephemeral - data clears on restart)
STORAGE_ROOT = "/tmp" 
UPLOAD_DIR = os.path.join(STORAGE_ROOT, "captured_screens")
DB_FILE = os.path.join(STORAGE_ROOT, "monitoring_database.sqlite")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Initialize Database
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

@app.route('/', methods=['POST'])
def update_data():
    device_id = request.form.get("device_id", "Unknown_Laptop")
    window_title = request.form.get("window_title", "Desktop / Idle")
    file = request.files.get("screenshot")

    screenshot_path = ""
    if file:
        filename = f"{device_id}_{int(time.time())}.jpg"
        screenshot_path = os.path.join(UPLOAD_DIR, filename)
        file.save(screenshot_path)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO activity_logs (device_id, window_title, screenshot_path) VALUES (?, ?, ?)",
                   (device_id, window_title, screenshot_path))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"}), 200

@app.route('/tmp/captured_screens/<filename>')
def serve_image(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.route('/', methods=['GET'])
def dashboard():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT device_id FROM activity_logs")
    devices = cursor.fetchall()

    grid_html = ""
    for dev in devices:
        device_id = dev[0]
        cursor.execute("SELECT window_title, screenshot_path, timestamp FROM activity_logs WHERE device_id = ? ORDER BY timestamp DESC LIMIT 10", (device_id,))
        logs = cursor.fetchall()
        
        log_entries_html = ""
        for log in logs:
            win_title, img_path, ts = log
            # Use the route created to serve files from /tmp
            filename = os.path.basename(img_path) if img_path else ""
            img_tag = f'<div class="img-preview"><img src="/tmp/captured_screens/{filename}" alt="Desktop"></div>' if filename else ""
            log_entries_html += f"""
                <div class="log-entry">
                    <div class="log-meta"><span>🕒 {ts}</span></div>
                    <div class="log-title">🖥️ App: {win_title}</div>
                    {img_tag}
                </div>
            """
        grid_html += f'<div class="device-column"><div class="device-header">💻 {device_id}</div>{log_entries_html}</div>'
    conn.close()

    html = f"""<!DOCTYPE html>
    <html>
    <head><meta http-equiv="refresh" content="10">
    <style>body {{ font-family: sans-serif; margin: 30px; }} .grid-container {{ display: grid; gap: 20px; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }}</style>
    </head>
    <body><h1>Monitor Dashboard</h1><div class="grid-container">{grid_html}</div></body>
    </html>"""
    return render_template_string(html)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
