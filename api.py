import os
import json
import uuid 
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import zipfile
import io
import threading
import cv2
import numpy as np
from datetime import datetime, timezone

import face_service

# --- Konfigurasi ---
app = Flask(__name__)
base_dir = os.path.abspath(os.path.dirname(__file__))

user_db_path = os.path.join(base_dir, 'users.db')      
msg_db_path = os.path.join(base_dir, 'messages.db')    

upload_folder = os.path.join(base_dir, 'temp_uploads')
face_dataset_dir = os.path.join(base_dir, 'face_dataset')
face_model_dir = os.path.join(base_dir, 'face_model')   

CASCADE_FILE = os.path.join(base_dir, "haarcascade_frontalface_default.xml")
MODEL_FILE = os.path.join(face_model_dir, "model.yml")
MAPPING_FILE = os.path.join(face_model_dir, "name_mapping.json")

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{user_db_path}'
app.config['SQLALCHEMY_BINDS'] = {
    'messages': f'sqlite:///{msg_db_path}'
}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = upload_folder 
MAX_FILE_SIZE = 2 * 1024 * 1024 
db = SQLAlchemy(app)

RECOGNIZER = None
ID_TO_NAME_MAP = {}
FACE_DETECTOR = None

# --- Definisi Database (Model) ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    salt_hex = db.Column(db.String(32), nullable=False)
    hash_hex = db.Column(db.String(64), nullable=False)

class Message(db.Model):
    __bind_key__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(160), nullable=False, index=True)
    sender = db.Column(db.String(80), nullable=False)
    recipient = db.Column(db.String(80), nullable=False)
    message_data_json = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

# [BARU] Model Group untuk manajemen akses
class Group(db.Model):
    __bind_key__ = 'messages' # Simpan di database messages
    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(80), unique=True, nullable=False)
    creator = db.Column(db.String(80), nullable=False) # Siapa pembuatnya
    # Kita simpan anggota sebagai JSON Text sederhana '["rakha", "ucup"]' agar simpel
    members_json = db.Column(db.Text, default="[]", nullable=False)

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head><meta charset="UTF-8"><title>API Status</title></head>
<body><h1>API Berjalan</h1><p>Layanan Kriptografi & Group Management Aktif.</p></body>
</html>
"""

@app.route('/')
def hello(): return render_template_string(HTML_TEMPLATE)

# --- Endpoint User Auth ---
@app.route('/register', methods=['POST'])
def register_user():
    data = request.json
    username = data['username']
    if User.query.filter_by(username=username).first():
        return jsonify({"success": False, "message": "Username sudah ada."}), 400
    new_user = User(username=username, salt_hex=data['salt_hex'], hash_hex=data['hash_hex'])
    db.session.add(new_user); db.session.commit()
    return jsonify({"success": True, "message": "Akun berhasil dibuat!"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data['username']
    user = User.query.filter_by(username=username).first()
    if not user: return jsonify({"salt_hex": "0"*32, "hash_hex": "0"*64})
    return jsonify({"salt_hex": user.salt_hex, "hash_hex": user.hash_hex})

# --- [BARU] Endpoint Group Management ---

@app.route('/create_group', methods=['POST'])
def create_group():
    data = request.json
    group_name = data.get('group_name')
    creator = data.get('creator')
    
    if Group.query.filter_by(group_name=group_name).first():
        return jsonify({"success": False, "message": "Nama grup sudah dipakai."}), 400
    
    # Buat grup baru, member awal adalah creator
    members = [creator]
    new_group = Group(
        group_name=group_name,
        creator=creator,
        members_json=json.dumps(members)
    )
    db.session.add(new_group)
    db.session.commit()
    return jsonify({"success": True, "message": f"Grup {group_name} dibuat."})

@app.route('/invite_user', methods=['POST'])
def invite_user():
    data = request.json
    group_name = data.get('group_name')
    requester = data.get('requester') # Siapa yang request invite
    target_user = data.get('target_user') # Siapa yang diinvite
    
    group = Group.query.filter_by(group_name=group_name).first()
    if not group:
        return jsonify({"success": False, "message": "Grup tidak ditemukan."}), 404
        
    # VALIDASI: Hanya Creator yang boleh invite
    if group.creator != requester:
        return jsonify({"success": False, "message": "Hanya pembuat grup yang bisa mengundang."}), 403
    
    # Cek apakah user target valid (ada di tabel User)
    if not User.query.filter_by(username=target_user).first():
         return jsonify({"success": False, "message": "Username tidak ditemukan."}), 404

    # Update member list
    members = json.loads(group.members_json)
    if target_user in members:
        return jsonify({"success": False, "message": "User sudah ada di grup."}), 400
        
    members.append(target_user)
    group.members_json = json.dumps(members)
    db.session.commit()
    
    return jsonify({"success": True, "message": f"{target_user} berhasil diundang."})

@app.route('/my_groups/<username>', methods=['GET'])
def get_my_groups(username):
    # Cari semua grup di mana username ada di dalam list members_json
    # Karena sqlite tidak punya fungsi JSON native yang kuat di SQLAlchemy versi lama, 
    # kita ambil semua lalu filter di python (untuk skala kecil ini oke)
    all_groups = Group.query.all()
    my_groups = []
    
    for g in all_groups:
        members = json.loads(g.members_json)
        if username in members:
            # Kirim info grup
            my_groups.append({
                "group_name": g.group_name,
                "creator": g.creator,
                "is_creator": (g.creator == username)
            })
            
    return jsonify({"success": True, "groups": my_groups})

# --- Endpoint Messaging ---
@app.route('/save_message', methods=['POST'])
def save_message():
    data = request.json
    chat_id = data['chat_id']; sender = data['sender']; recipient = data['recipient']
    
    # [TAMBAHAN KEAMANAN] Jika chat ke GROUP, cek keanggotaan dulu
    if recipient.startswith("GROUP_"):
        group_name = recipient.replace("GROUP_", "")
        group = Group.query.filter_by(group_name=group_name).first()
        if group:
            members = json.loads(group.members_json)
            if sender not in members and sender != 'SYSTEM': 
                # SYSTEM boleh kirim (misal notif invite), user luar tidak boleh
                return jsonify({"success": False, "message": "Anda bukan anggota grup."}), 403

    if 'data' in data and data.get('type') in ['stegano', 'file']:
        data['data'] = None 
    message_json = json.dumps(data)
    new_message = Message(
        chat_id=chat_id, sender=sender, recipient=recipient, message_data_json=message_json
    )
    db.session.add(new_message); db.session.commit()
    return jsonify({"success": True})

@app.route('/load_messages/<chat_id>', methods=['GET'])
def load_messages(chat_id):
    messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.id.asc()).all()
    message_list = []
    for msg in messages:
        try:
            data = json.loads(msg.message_data_json)
            timestamp = msg.timestamp
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            data['db_timestamp'] = timestamp.isoformat()
            message_list.append(data)
        except json.JSONDecodeError: pass
    return jsonify(message_list)

# --- Vigenere Logic (Sama) ---
def vigenere_encrypt_logic(plain_text, key):
    encrypted_text = ""; key_index = 0; key = key.lower()
    if not key: key = "defaultkey"
    for char in plain_text:
        if 'a' <= char <= 'z':
            key_char = key[key_index % len(key)]; key_offset = ord(key_char) - ord('a')
            new_char_code = (ord(char) - ord('a') + key_offset) % 26
            encrypted_text += chr(new_char_code + ord('a')); key_index += 1
        elif 'A' <= char <= 'Z':
            key_char = key[key_index % len(key)]; key_offset = ord(key_char) - ord('a')
            new_char_code = (ord(char) - ord('A') + key_offset) % 26
            encrypted_text += chr(new_char_code + ord('A')); key_index += 1
        else: encrypted_text += char
    return encrypted_text

def vigenere_decrypt_logic(encrypted_text, key):
    decrypted_text = ""; key_index = 0; key = key.lower()
    if not key: key = "defaultkey"
    for char in encrypted_text:
        if 'a' <= char <= 'z':
            key_char = key[key_index % len(key)]; key_offset = ord(key_char) - ord('a')
            new_char_code = (ord(char) - ord('a') - key_offset) % 26
            decrypted_text += chr(new_char_code + ord('a')); key_index += 1
        elif 'A' <= char <= 'Z':
            key_char = key[key_index % len(key)]; key_offset = ord(key_char) - ord('a')
            new_char_code = (ord(char) - ord('A') - key_offset) % 26
            decrypted_text += chr(new_char_code + ord('A')); key_index += 1
        else: decrypted_text += char
    return decrypted_text

@app.route('/encrypt/vigenere', methods=['POST'])
def api_vigenere_encrypt():
    data = request.json
    return jsonify({"result": vigenere_encrypt_logic(data.get('text'), data.get('key'))})

@app.route('/decrypt/vigenere', methods=['POST'])
def api_vigenere_decrypt():
    data = request.json
    return jsonify({"result": vigenere_decrypt_logic(data.get('text'), data.get('key'))})

# --- Endpoint Dashboard ---
@app.route('/get_chats/<username>', methods=['GET'])
def get_chats(username):
    # Ambil kontak personal saja, grup diambil via endpoint /my_groups
    try:
        sent_to = db.session.query(Message.recipient).filter(Message.sender == username).distinct()
        received_from = db.session.query(Message.sender).filter(Message.recipient == username).distinct()
        contacts = set()
        for r in sent_to: 
            if not r.recipient.startswith("GROUP_"): contacts.add(r.recipient)
        for s in received_from: 
            if not s.sender.startswith("GROUP_"): contacts.add(s.sender)
        return jsonify({"success": True, "contacts": list(contacts)})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# --- File Handling (Sama) ---
@app.route('/upload_file/<chat_id>', methods=['POST'])
def upload_file(chat_id):
    if 'file' not in request.files: return jsonify({"success": False}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({"success": False}), 400
    try:
        file.seek(0, os.SEEK_END); file_size = file.tell(); file.seek(0)
        if file_size > MAX_FILE_SIZE: return jsonify({"success": False, "message": "File > 2MB"}), 413
        ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        path = os.path.join(app.config['UPLOAD_FOLDER'], chat_id)
        os.makedirs(path, exist_ok=True)
        file.save(os.path.join(path, unique_filename))
        return jsonify({"success": True, "file_id": unique_filename})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

@app.route('/download_file/<chat_id>/<file_id>', methods=['GET'])
def download_file(chat_id, file_id):
    try: return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], chat_id), file_id, as_attachment=True)
    except: return jsonify({"success": False}), 404

# --- Face Auth (Sama, disingkat) ---
def run_training_in_background(app_context, dataset_dir, model_path, mapping_path):
    global RECOGNIZER, ID_TO_NAME_MAP
    with app_context:
        if face_service.train_model(dataset_dir, model_path, mapping_path):
            try:
                RECOGNIZER = cv2.face.LBPHFaceRecognizer_create()
                RECOGNIZER.read(MODEL_FILE)
                with open(MAPPING_FILE, 'r') as f:
                    ID_TO_NAME_MAP = {int(v): k for k, v in json.load(f).items()}
            except: pass

@app.route('/register-face', methods=['POST'])
def register_face():
    # ... (Sama seperti sebelumnya)
    username = request.form['username']
    file = request.files['file']
    if not User.query.filter_by(username=username).first(): return jsonify({"success": False}), 404
    path = os.path.join(face_dataset_dir, username)
    os.makedirs(path, exist_ok=True)
    try:
        with zipfile.ZipFile(io.BytesIO(file.read()), 'r') as z: z.extractall(path)
    except: return jsonify({"success": False}), 500
    threading.Thread(target=run_training_in_background, args=(app.app_context(), face_dataset_dir, MODEL_FILE, MAPPING_FILE)).start()
    return jsonify({"success": True})

@app.route('/login-face', methods=['POST'])
def login_face():
    # ... (Sama seperti sebelumnya)
    if 'file' not in request.files: return jsonify({"success": False}), 400
    if not RECOGNIZER: return jsonify({"success": False}), 503
    name, msg = face_service.recognize_face(request.files['file'].stream, RECOGNIZER, ID_TO_NAME_MAP, FACE_DETECTOR)
    return jsonify({"success": True, "username": name}) if name and name != "Unknown" else jsonify({"success": False, "message": msg})

# --- Init ---
with app.app_context():
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(face_dataset_dir, exist_ok=True)
    os.makedirs(face_model_dir, exist_ok=True)
    db.create_all()
    try:
        if os.path.exists(CASCADE_FILE): FACE_DETECTOR = cv2.CascadeClassifier(CASCADE_FILE)
        if os.path.exists(MODEL_FILE):
            RECOGNIZER = cv2.face.LBPHFaceRecognizer_create()
            RECOGNIZER.read(MODEL_FILE)
            with open(MAPPING_FILE, 'r') as f: ID_TO_NAME_MAP = {int(v): k for k, v in json.load(f).items()}
    except: pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)