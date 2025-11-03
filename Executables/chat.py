import os
import base64
import requests
import uuid
import hashlib 
import json    
from stegano import lsb
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox,
    QListWidget, QListWidgetItem, QFileDialog,
    QInputDialog
)
from PySide6.QtGui import QFont, QColor, QPixmap
from PySide6.QtCore import Qt

from utils import CryptoEngine, vigenere_encrypt, vigenere_decrypt, encrypt_whitemist, decrypt_whitemist

class ChatPage(QWidget):
    def __init__(self, current_user, recipient_username, shared_password, message_manager, back_callback):
        super().__init__()
        self.current_user = current_user
        self.recipient_username = recipient_username
        self.message_manager = message_manager
        self.back_callback = back_callback
        
        self.chat_id = self.message_manager.get_chat_id(self.current_user, self.recipient_username)
        self.session_crypto = CryptoEngine(shared_password)
        
        self.api_url = "https://morsz.azeroth.site/"
        self.MAX_FILE_SIZE = 2 * 1024 * 1024 # 2MB
        
        # --- [REVISI RAPIKAN FOLDER] ---
        # 1. Definisikan folder data induk
        self.base_data_dir = "local_data" 
        
        # 2. Path Caching Teks (Per-User)
        self.cache_dir = os.path.join(self.base_data_dir, "user_caches")
        self.cache_file = os.path.join(self.cache_dir, f"cache_{self.current_user}.json")
        self.message_cache = self.load_cache()
        
        # 3. Path Caching File (Temporary)
        self.temp_stegano_dir = os.path.join(self.base_data_dir, "temp_stegano")
        self.temp_download_dir = os.path.join(self.base_data_dir, "temp_downloads")
        self.temp_decrypted_dir = os.path.join(self.base_data_dir, "temp_decrypted")
        # ------------------------------------
        
        self.init_ui()
        self.load_and_display_chat_history()

    # --- Fungsi Helper Cache ---
    def get_message_id(self, metadata):
        # ... (Tidak berubah) ...
        data = metadata.get('data')
        if not data:
            return None
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    def load_cache(self):
        # ... (Tidak berubah, sudah menggunakan self.cache_file) ...
        if not os.path.exists(self.cache_file):
            return {}
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {} 

    def save_to_cache(self, message_id, plain_text):
        # ... (Tidak berubah, sudah menggunakan self.cache_dir dan self.cache_file) ...
        if not message_id: return
        
        self.message_cache[message_id] = plain_text 
        
        try:
            if not os.path.exists(self.cache_dir):
                # os.makedirs akan membuat folder induk 'local_data' jika belum ada
                os.makedirs(self.cache_dir)
                
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.message_cache, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Peringatan: Gagal menyimpan cache ke file: {e}")
    # -------------------------------------------

    def init_ui(self):
        # ... (Tidak berubah) ...
        self.resize(600, 800)
        self.setStyleSheet("background-color: #0f172a;")
        layout = QVBoxLayout(self); layout.setContentsMargins(20, 20, 20, 20); layout.setSpacing(15)

        top_bar_layout = QHBoxLayout()
        back_btn = QPushButton("< Back"); back_btn.setStyleSheet(self.button_style("#4338ca", "#6366f1", "#312e81"))
        back_btn.clicked.connect(self.back_callback); back_btn.setFixedWidth(100)
        title = QLabel(f"Chat with: {self.recipient_username}"); title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #e0e7ff;"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_bar_layout.addWidget(back_btn); top_bar_layout.addWidget(title)
        
        self.chat_display = QListWidget()
        self.chat_display.setStyleSheet("""
            QListWidget { background-color: #1e3a8a; border: 2px solid #4338ca;
            border-radius: 12px; color: white; font-size: 14px; padding: 10px; }
        """)
        self.chat_display.itemClicked.connect(self.on_chat_item_clicked)

        input_bar_layout = QHBoxLayout()
        self.attach_btn = QPushButton("📎 Gbr"); self.attach_btn.setToolTip("Sembunyikan teks dari input ke dalam Gambar (.png)")
        self.attach_btn.setFont(QFont("Segoe UI", 12)); self.attach_btn.setStyleSheet(self.button_style("#4338ca", "#6366f1", "#312e81"))
        self.attach_btn.setFixedSize(70, 45)
        self.attach_btn.clicked.connect(self.handle_attach_image_stegano)

        self.attach_file_btn = QPushButton("📁 File"); 
        self.attach_file_btn.setToolTip("Enkripsi file (AES / White-Mist)")
        self.attach_file_btn.setFont(QFont("Segoe UI", 12)); self.attach_file_btn.setStyleSheet(self.button_style("#4338ca", "#6366f1", "#312e81"))
        self.attach_file_btn.setFixedSize(70, 45)
        self.attach_file_btn.clicked.connect(self.handle_attach_file) 

        self.message_input = QLineEdit(); self.message_input.setPlaceholderText("Ketik pesan...")
        self.message_input.setStyleSheet(self.input_style())
        self.message_input.returnPressed.connect(self.handle_send_message_super)

        self.send_btn = QPushButton("Send Txt"); self.send_btn.setToolTip("Kirim teks dengan Super Enkripsi (Vigenere -> White Mist -> AES Sesi)")
        self.send_btn.setFont(QFont("Segoe UI", 11, QFont.Bold)); self.send_btn.setStyleSheet(self.button_style("#6d28d9", "#818cf8", "#4c1d95"))
        self.send_btn.setFixedSize(100, 45)
        self.send_btn.clicked.connect(self.handle_send_message_super)

        input_bar_layout.addWidget(self.attach_btn); input_bar_layout.addWidget(self.attach_file_btn)
        input_bar_layout.addWidget(self.message_input); input_bar_layout.addWidget(self.send_btn)
        layout.addLayout(top_bar_layout); layout.addWidget(self.chat_display); layout.addLayout(input_bar_layout)


    def load_and_display_chat_history(self):
        # ... (Tidak berubah) ...
        self.chat_display.clear()
        messages = self.message_manager.load_messages(self.chat_id)
        
        for msg_data in messages:
            sender = msg_data['sender']
            display_text = ""
            
            if sender == self.current_user:
                align = "sent"
                prefix = "You"
            else:
                align = "received"
                prefix = sender

            msg_type = msg_data.get('type', 'unknown')
            
            if msg_type == 'text':
                message_id = self.get_message_id(msg_data)
                cached_text = self.message_cache.get(message_id)
                
                if cached_text:
                    display_text = f"{prefix}: {cached_text}"
                else:
                    display_text = f"{prefix}: [Pesan Teks Super-Terenkripsi]"
            elif msg_type == 'stegano':
                filename = os.path.basename(msg_data.get('filename', 'unknown.png'))
                display_text = f"{prefix}: [Gambar Stegano: {filename}]"
            elif msg_type == 'file':
                filename = msg_data.get('filename', 'unknown_file')
                method = msg_data.get('encryption_method', 'aes').upper()
                display_text = f"{prefix}: [File ({method}): {filename}]" 
            else:
                display_text = f"{prefix}: [Pesan tidak dikenal]"

            self.add_message_to_display(display_text, align, msg_data)

    def handle_send_message_super(self):
        # ... (Tidak berubah) ...
        message_text = self.message_input.text() 
        if not message_text: return
        
        user_key, ok = QInputDialog.getText(self, "Kunci Super Enkripsi", "Masukkan Kunci (untuk Vigenere + White Mist):")
        if not (ok and user_key): return 
        
        self.message_input.clear()
        
        try:
            # 1. VIGENERE
            vigenere_encrypted_text = vigenere_encrypt(message_text, user_key)
            # 2. WHITE MIST
            vigenere_encrypted_bytes = vigenere_encrypted_text.encode('utf-8')
            whitemist_encrypted_string = encrypt_whitemist(vigenere_encrypted_bytes, user_key)
            # 3. AES
            data_bytes_for_aes = whitemist_encrypted_string.encode('utf-8')
            encrypted_payload_bytes = self.session_crypto.encrypt(data_bytes_for_aes)
            
            metadata = {
                'type': 'text', 'sender': self.current_user,
                'recipient': self.recipient_username,
                'data': encrypted_payload_bytes.decode('utf-8'), 
                'vigenere_key_debug': user_key 
            }
            
            self.message_manager.save_message(self.chat_id, metadata)
            
            message_id = self.get_message_id(metadata)
            self.save_to_cache(message_id, message_text)
            
            self.add_message_to_display(f"You: {message_text}", "sent", metadata)
            
        except Exception as e:
            self.add_message_to_display(f"--- Error Super Enkripsi: {e} ---", "error")

    # [REVISI] Menggunakan path dari self.temp_stegano_dir
    def handle_attach_image_stegano(self):
        message_to_hide = self.message_input.text()
        if not message_to_hide:
            QMessageBox.warning(self, "Error", "Tulis dulu pesan di kotak teks untuk disembunyikan ke gambar.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih Gambar Pembawa (.png)", "", "Images (*.png)")
        if not file_path: return

        try:
            file_size = os.path.getsize(file_path)
            if file_size > self.MAX_FILE_SIZE:
                QMessageBox.warning(self, "File Terlalu Besar", 
                                  f"Ukuran file ({file_size // 1024} KB) melebihi batas 2MB ({self.MAX_FILE_SIZE // 1024} KB).")
                return
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Tidak dapat membaca file: {e}")
            return

        text_key, ok = QInputDialog.getText(self, "Kunci Steganografi", "Masukkan Kunci VIGENERE untuk teks yang akan disembunyikan:")
        if not (ok and text_key): return

        # Gunakan path dari __init__
        if not os.path.exists(self.temp_stegano_dir): 
            os.makedirs(self.temp_stegano_dir)
            
        base_filename = os.path.basename(file_path)
        # Gunakan path dari __init__
        temp_filename = os.path.join(self.temp_stegano_dir, f"stego_{uuid.uuid4()}.png") 

        try:
            encrypted_text_to_hide = vigenere_encrypt(message_to_hide, text_key)
            secret_image = lsb.hide(file_path, encrypted_text_to_hide)
            secret_image.save(temp_filename)

            self.add_message_to_display(f"--- Mengunggah {base_filename}... ---", "error")
            with open(temp_filename, "rb") as f:
                files = {'file': (base_filename, f, 'image/png')}
                upload_url = f"{self.api_url}/upload_file/{self.chat_id}"
                response = requests.post(upload_url, files=files, timeout=30)
            
            if response.status_code != 200 or not response.json().get("success"):
                if response.status_code == 413: 
                    raise Exception(f"Gagal unggah: {response.json().get('message')}")
                raise Exception(f"Gagal mengunggah file: {response.json().get('message', 'Error tidak diketahui')}")

            file_id = response.json().get("file_id")

            metadata = {
                'type': 'stegano', 'sender': self.current_user,
                'recipient': self.recipient_username, 'data': None,
                'file_id': file_id, 'filename': base_filename, 
                'text_key_debug': text_key
            }
            
            self.message_manager.save_message(self.chat_id, metadata)
            self.add_message_to_display(f"You: [Sent Stegano Image: {base_filename}]", "sent", metadata)
            self.message_input.clear()
            os.remove(temp_filename)

        except Exception as e:
            self.add_message_to_display(f"--- Error Steganografi/Upload: {e} ---", "error")
            if os.path.exists(temp_filename): os.remove(temp_filename)

    def handle_attach_file(self):
        # ... (Tidak berubah) ...
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih File Untuk Dienkripsi", "", "All Files (*.*)")
        if not file_path: return

        try:
            file_size = os.path.getsize(file_path)
            if file_size > self.MAX_FILE_SIZE:
                QMessageBox.warning(self, "File Terlalu Besar", 
                                  f"Ukuran file ({file_size // 1024} KB) melebihi batas 2MB ({self.MAX_FILE_SIZE // 1024} KB).")
                return
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Tidak dapat membaca file: {e}")
            return

        methods = ["AES (Modern)", "White-Mist (Eksperimental)"]
        method, ok = QInputDialog.getItem(self, "Pilih Metode Enkripsi", "Metode:", methods, 0, False)
        if not ok: return
        
        key, ok = QInputDialog.getText(self, f"Kunci Enkripsi ({method})", f"Masukkan Kunci untuk {method}:", QLineEdit.Password)
        if not (ok and key): return

        try:
            with open(file_path, "rb") as f: data_bytes = f.read()
            filename = os.path.basename(file_path)
            
            encrypted_payload_bytes = None
            metadata = {}

            if method == "AES (Modern)":
                temp_crypto = CryptoEngine(key)
                encrypted_payload_bytes = temp_crypto.encrypt(data_bytes)
                metadata = { 'type': 'file', 'sender': self.current_user, 'recipient': self.recipient_username, 'data': None, 'encryption_method': 'aes', 'aes_key_debug': key, 'filename': filename }
            elif method == "White-Mist (Eksperimental)":
                encrypted_string = encrypt_whitemist(data_bytes, key)
                encrypted_payload_bytes = encrypted_string.encode('utf-8')
                metadata = { 'type': 'file', 'sender': self.current_user, 'recipient': self.recipient_username, 'data': None, 'encryption_method': 'whitemist', 'aes_key_debug': key, 'filename': filename }
            else:
                return 

            self.add_message_to_display(f"--- Mengunggah {filename} ({method})... ---", "error")
            
            files = {'file': (f"{filename}.enc", encrypted_payload_bytes, 'application/octet-stream')}
            upload_url = f"{self.api_url}/upload_file/{self.chat_id}"
            response = requests.post(upload_url, files=files, timeout=60)
            
            if response.status_code != 200 or not response.json().get("success"):
                if response.status_code == 413: 
                    raise Exception(f"Gagal unggah: {response.json().get('message')}")
                raise Exception(f"Gagal mengunggah file: {response.json().get('message', 'Error tidak diketahui')}")
                
            file_id = response.json().get("file_id")
            metadata['file_id'] = file_id 

            self.message_manager.save_message(self.chat_id, metadata)
            self.add_message_to_display(f"You: [Sent File ({method}): {filename}]", "sent", metadata)
            
        except Exception as e:
            self.add_message_to_display(f"--- Error File Encryption/Upload: {e} ---", "error")

    # [REVISI] Menggunakan path dari variabel self.
    def on_chat_item_clicked(self, item):
        metadata = item.data(Qt.UserRole)
        
        if not metadata: return
        
        msg_box = QMessageBox(self)
        msg_type = metadata.get('type')
        file_id = metadata.get('file_id')
        
        # [REVISI] Gunakan variabel self. untuk membuat folder
        for folder in [self.temp_stegano_dir, self.temp_download_dir, self.temp_decrypted_dir]:
            if not os.path.exists(folder): 
                os.makedirs(folder)

        try:
            if msg_type == 'text':
                # ... (Logika Teks tidak berubah) ...
                message_id = self.get_message_id(metadata)
                if metadata['sender'] == self.current_user: return
                
                encrypted_data_b64 = metadata['data'].encode('utf-8')
                
                key, ok = QInputDialog.getText(self, "Dekripsi Teks", "Masukkan Kunci (White-Mist + Vigenere):")
                if ok and key:
                    # 1. AES
                    decrypted_bytes_from_aes = self.session_crypto.decrypt(encrypted_data_b64)
                    whitemist_encrypted_string = decrypted_bytes_from_aes.decode('utf-8')
                    # 2. WHITE MIST
                    vigenere_encrypted_bytes = decrypt_whitemist(whitemist_encrypted_string, key)
                    vigenere_encrypted_text = vigenere_encrypted_bytes.decode('utf-8')
                    # 3. VIGENERE
                    decrypted_text = vigenere_decrypt(vigenere_encrypted_text, key)
                    
                    if message_id:
                        self.save_to_cache(message_id, decrypted_text)
                    
                    prefix = metadata['sender']
                    item.setText(f"{prefix}: {decrypted_text}")
                    
                    msg_box.setWindowTitle("Pesan Teks Didekripsi")
                    msg_box.setText(f"Pesan Asli:\n\n{decrypted_text}")
                    msg_box.setInformativeText(f"(Debug: Kunci yg benar '{metadata['vigenere_key_debug']}')")
                    msg_box.exec()

            elif msg_type == 'file' and file_id:
                if metadata['sender'] == self.current_user: return
                
                # [REVISI] Gunakan self.temp_download_dir
                local_encrypted_path = os.path.join(self.temp_download_dir, file_id)
                filename = metadata['filename']

                if not os.path.exists(local_encrypted_path):
                    self.add_message_to_display(f"--- Mengunduh {filename}... ---", "error")
                    download_url = f"{self.api_url}/download_file/{self.chat_id}/{file_id}"
                    response = requests.get(download_url, timeout=60)
                    if response.status_code != 200:
                        raise Exception("Gagal mengunduh file dari server.")
                    with open(local_encrypted_path, "wb") as f: f.write(response.content)
                    self.add_message_to_display(f"--- Unduhan Selesai. Disimpan di cache. ---", "error")
                else:
                    self.add_message_to_display(f"--- Membuka {filename} dari cache... ---", "error")

                key, ok = QInputDialog.getText(self, "Dekripsi File", "Masukkan Kunci untuk file ini:", QLineEdit.Password)
                if not (ok and key): return

                with open(local_encrypted_path, "rb") as f: encrypted_bytes = f.read()
                
                decrypted_bytes = None
                method = metadata.get('encryption_method', 'aes')
                
                if method == 'aes':
                    self.add_message_to_display(f"--- Mendekripsi (AES)... ---", "error")
                    temp_crypto = CryptoEngine(key)
                    decrypted_bytes = temp_crypto.decrypt(encrypted_bytes)
                elif method == 'whitemist':
                    self.add_message_to_display(f"--- Mendekripsi (White-Mist)... ---", "error")
                    encrypted_string = encrypted_bytes.decode('utf-8')
                    decrypted_bytes = decrypt_whitemist(encrypted_string, key)
                else:
                    raise ValueError(f"Metode enkripsi '{method}' tidak dikenal.")

                # [REVISI] Gunakan self.temp_decrypted_dir
                decrypted_path = os.path.join(self.temp_decrypted_dir, f"DECRYPTED_{filename}")
                with open(decrypted_path, "wb") as f: f.write(decrypted_bytes)
                    
                msg_box.setWindowTitle("File Didekripsi")
                msg_box.setText(f"File '{filename}' ({method}) berhasil didekripsi!")
                msg_box.setInformativeText(f"Disimpan di: {decrypted_path}\n(Debug: Kunci yg benar '{metadata['aes_key_debug']}')")
                msg_box.exec()

            elif msg_type == 'stegano' and file_id:
                if metadata['sender'] == self.current_user: return
                
                filename = metadata.get('filename', f"{file_id}.png")
                # [REVISI] Gunakan self.temp_stegano_dir
                local_stegano_path = os.path.join(self.temp_stegano_dir, file_id) 

                if not os.path.exists(local_stegano_path):
                    self.add_message_to_display(f"--- Mengunduh gambar {filename}... ---", "error")
                    download_url = f"{self.api_url}/download_file/{self.chat_id}/{file_id}"
                    response = requests.get(download_url, timeout=60)
                    if response.status_code != 200:
                        raise Exception("Gagal mengunduh gambar dari server.")
                    with open(local_stegano_path, "wb") as f: f.write(response.content)
                    self.add_message_to_display(f"--- Gambar diterima. Disimpan di cache. ---", "error")
                else:
                    self.add_message_to_display(f"--- Membuka gambar {filename} dari cache... ---", "error")
                
                msg_box.setWindowTitle("Pesan Gambar Diterima")
                pixmap = QPixmap(local_stegano_path).scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                msg_box.setIconPixmap(pixmap)
                
                msg_box.setText("Gambar diterima. Ingin mendekripsi teks tersembunyi di dalamnya?")
                decrypt_button = msg_box.addButton("Dekripsi Teks Tersembunyi", QMessageBox.AcceptRole)
                msg_box.addButton(QMessageBox.Close)
                msg_box.exec()
                
                if msg_box.clickedButton() == decrypt_button:
                    key, ok = QInputDialog.getText(self, "Dekripsi Steganografi", "Masukkan Kunci VIGENERE untuk teks tersembunyi:")
                    if ok and key:
                        revealed_encrypted_text = lsb.reveal(local_stegano_path) 
                        if not revealed_encrypted_text:
                            QMessageBox.warning(self, "Gagal", "Tidak ada pesan tersembunyi yang ditemukan di gambar ini.")
                            return
                            
                        decrypted_message = vigenere_decrypt(revealed_encrypted_text, key)
                        
                        QMessageBox.information(self, "Teks Terungkap", 
                            f"Pesan tersembunyi adalah:\n\n{decrypted_message}\n\n"
                            f"(Debug: Kunci yg benar '{metadata['text_key_debug']}')")

        except ValueError as e:
             QMessageBox.warning(self, "Dekripsi Gagal", f"Tidak dapat mendekripsi: {e}")
        except ImportError as e:
             QMessageBox.critical(self, "Error Modul", f"{e}")
        except Exception as e:
             QMessageBox.critical(self, "Error", f"Terjadi error: {e}")

    def add_message_to_display(self, text, message_type, metadata=None):
        # ... (Tidak berubah) ...
        item = QListWidgetItem(text)
        if message_type == "sent":
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            item.setForeground(QColor("#c7d2fe"))
        elif message_type == "received":
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft)
            item.setForeground(QColor("#e0e7ff"))
        elif message_type == "error":
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor("#fca5a5"))
            
        if metadata:
            item.setData(Qt.UserRole, metadata)
            
        self.chat_display.addItem(item)
        self.chat_display.scrollToBottom()

    # ... (Fungsi style tidak berubah) ...
    def input_style(self): return "QLineEdit { background-color: #1e3a8a; border: 2px solid #6d28d9; border-radius: 8px; padding: 12px 10px; color: white; font-size: 14px; min-height: 25px; } QLineEdit:focus { border: 2px solid #818cf8; }"
    def button_style(self, base, hover, pressed): return f"QPushButton {{ background-color: {base}; color: white; border: none; border-radius: 8px; padding: 10px; font-weight: bold; }} QPushButton:hover {{ background-color: {hover}; }} QPushButton:pressed {{ background-color: {pressed}; }}"