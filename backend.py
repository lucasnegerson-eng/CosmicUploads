# Cosmic Uploads Backend
from flask import Flask, request, jsonify, send_file
from cryptography.fernet import Fernet
from apscheduler.schedulers.background import BackgroundScheduler
import os, time, uuid

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
MAX_STORAGE = 10 * 1024 * 1024 * 1024  # 10GB
FILES = {}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
key = Fernet.generate_key()
cipher = Fernet(key)
scheduler = BackgroundScheduler()

# Cleanup old files
def cleanup_old_files():
    now = time.time()
    to_delete = [f for f, info in FILES.items() if now - info['time'] > 86400]
    for f in to_delete:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, f))
        except:
            pass
        FILES.pop(f, None)
    # Delete oldest if storage exceeded
    files_by_time = sorted(FILES.items(), key=lambda x: x[1]['time'])
    while sum(info['size'] for _, info in FILES.items()) > MAX_STORAGE:
        oldest, info = files_by_time.pop(0)
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, oldest))
        except:
            pass
        FILES.pop(oldest, None)

scheduler.add_job(cleanup_old_files, 'interval', minutes=10)
scheduler.start()

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if len(file.read()) > 1024**3:  # 1GB limit
        return jsonify({"error": "File too large"}), 400
    file.seek(0)
    file_id = str(uuid.uuid4())
    encrypted_path = os.path.join(UPLOAD_FOLDER, file_id)
    with open(encrypted_path, 'wb') as f:
        f.write(cipher.encrypt(file.read()))
    FILES[file_id] = {'time': time.time(), 'size': os.path.getsize(encrypted_path)}
    return jsonify({"link": f"/download/{file_id}"}), 200

@app.route('/download/<file_id>', methods=['GET'])
def download_file(file_id):
    if file_id not in FILES:
        return "File not found", 404
    path = os.path.join(UPLOAD_FOLDER, file_id)
    with open(path, 'rb') as f:
        data = cipher.decrypt(f.read())
    return data, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
