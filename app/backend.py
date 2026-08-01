import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = '/opt/goa_app/uploads'
DB_PATH = '/opt/goa_app/goa_trip.db'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Database Initialization & Pre-seeding ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Crew Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crew (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'Ready for Goa 🌴'
        )
    ''')

    # Create Photos Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uploader TEXT NOT NULL,
            filename TEXT NOT NULL,
            caption TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Pre-seed Crew Names
    crew_members = ['Sajith', 'Aslam', 'Noble', 'Vishnu', 'Sandy', 'Anku']
    for member in crew_members:
        cursor.execute('INSERT OR IGNORE INTO crew (name) VALUES (?)', (member,))
    
    conn.commit()
    conn.close()

init_db()

# --- API Endpoints ---
@app.route('/api/crew', methods=['GET'])
def get_crew():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, status FROM crew')
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "name": r[1], "status": r[2]} for r in rows])

@app.route('/api/photos', methods=['GET'])
def get_photos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT uploader, filename, caption, uploaded_at FROM photos ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"uploader": r[0], "url": f"/uploads/{r[1]}", "caption": r[2], "date": r[3]} for r in rows])

@app.route('/api/upload', methods=['POST'])
def upload_photo():
    if 'photo' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    file = request.files['photo']
    uploader = request.form.get('uploader', 'Anonymous')
    caption = request.form.get('caption', 'Goa Memories')

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO photos (uploader, filename, caption) VALUES (?, ?, ?)',
                   (uploader, filename, caption))
    conn.commit()
    conn.close()

    return jsonify({"message": "Photo uploaded successfully!", "url": f"/uploads/{filename}"}), 201

@app.route('/uploads/<filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)