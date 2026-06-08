import os
import sqlite3
import time
from flask import Flask, request, send_from_directory, render_template_string, jsonify

app = Flask(__name__)

UPLOAD_DIR = "captured_screens"
DB_FILE = "monitoring_database.sqlite"

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
    # Flask cleanly handles multipart forms automatically
    device_id = request.form.get("device_id", "Unknown_Laptop")
    window_title = request.form.get("window_title", "Desktop / Idle")
    file = request.files.get("screenshot")

    screenshot_path = ""
    if file:
        try:
            clean_id = "".join(c for c in device_id if c.isalnum() or c in ('_', '-'))
            filename = f"{clean_id}_{int(time.time())}.jpg"
            screenshot_path = os.path.join(UPLOAD_DIR, filename)
            file.save(screenshot_path)
        except Exception as e:
            print(f"Error saving image: {e}")

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO activity_logs (device_id, window_title, screenshot_path) VALUES (?, ?, ?)",
                       (device_id, window_title, screenshot_path))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/captured_screens/<filename>')
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
            # Fix pathing for cloud serving
            web_img_path = img_path.replace("\\", "/") if img_path else ""
            img_tag = f'<div class="img-preview"><img src="/{web_img_path}" alt="Desktop"></div>' if web_img_path else ""
            log_entries_html += f"""
                <div class="log-entry">
                    <div class="log-meta"><span>🕒 {ts}</span></div>
                    <div class="log-title">🖥️ App: <span style="font-weight:normal; color:#4b5563;">{win_title}</span></div>
                    {img_tag}
                </div>
            """
        
        grid_html += f"""
            <div class="device-column">
                <div class="device-header">💻 {device_id}</div>
                {log_entries_html}
            </div>
        """
    conn.close()

    html = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Multi-Laptop Control Dashboard</title>
        <meta http-equiv="refresh" content="10">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f3f4f6; margin: 30px; color: #333; }}
            .grid-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 25px; }}
            .device-column {{ background: #ffffff; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); padding: 20px; max-height: 85vh; overflow-y: auto; }}
            .device-header {{ font-size: 1.3em; font-weight: bold; color: #1e3a8a; border-bottom: 3px solid #3b82f6; padding-bottom: 10px; margin-bottom: 15px; position: sticky; top: 0; background: white; }}
            .log-entry {{ border-bottom: 1px solid #e5e7eb; padding: 12px 0; display: flex; flex-direction: column; gap: 8px; }}
            .log-meta {{ display: flex; justify-content: space-between; font-size: 0.8em; color: #6b7280; }}
            .log-title {{ font-weight: 600; font-size: 0.95em; word-break: break-all; }}
            .img-preview img {{ width: 100%; border-radius: 6px; border: 1px solid #e5e7eb; cursor: zoom-in; max-height: 180px; object-fit: cover; }}
            .img-preview img:hover {{ object-fit: contain; max-height: none; cursor: zoom-out; }}
        </style>
    </head>
    <body>
        <h1 style="color: #1e3a8a; margin-bottom: 5px;">Multi-Device Activity Control Center</h1>
        <p style="color: #6b7280; margin-bottom: 30px;">Live grid view monitoring columns of all active laptops.</p>
        <div class="grid-container">{grid_html if grid_html else "<p>Waiting for data from laptops...</p>"}</div>
    </body>
    </html>"""
    return render_template_string(html)

if __name__ == "__main__":
    # Dynamically reads the port assigned by the cloud platform
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)