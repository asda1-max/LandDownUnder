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
    QInputDialog, QFrame, QApplication, QDialog,
    QSizePolicy, QListView, QTextEdit
)
from PySide6.QtGui import QFont, QColor, QPixmap
from PySide6.QtCore import Qt, QSize, QTimer
from datetime import datetime, timezone 

# Pastikan utils.py ada di satu folder yang sama
from utils import CryptoEngine, vigenere_encrypt, vigenere_decrypt, encrypt_whitemist, decrypt_whitemist

class GroupChatPage(QWidget):
    
    # --- Palet Warna (Sama seperti chat.py) ---
    COLOR_BACKGROUND = "#1A1B2E"
    COLOR_PANE_LEFT = "#272540" 
    COLOR_PANE_RIGHT = "#1A1B2E"
    COLOR_CARD_BG = "#272540"
    COLOR_CARD = "#3E3C6E"     
    COLOR_CARD_HOVER = "#504E8A" 
    COLOR_TEXT = "#F0F0F5"
    COLOR_TEXT_SUBTLE = "#A9A8C0"
    COLOR_GOLD = "#D4AF37"
    COLOR_GOLD_HOVER = "#F0C44F"
    COLOR_GOLD_PRESSED = "#B8860B"
    COLOR_RED = "#ed4956"
    COLOR_RED_HOVER = "#ff7d6e"
    COLOR_RED_PRESSED = "#e63946"
    COLOR_BUBBLE_SENT = "#3C506E" 
    COLOR_BUBBLE_RECV = "#3E3C6E" # Warna bubble orang lain
    # -------------------

    def __init__(self, current_user, group_name, shared_password, message_manager, back_callback):
        super().__init__()
        self.current_user = current_user
        self.group_name = group_name # Menggantikan recipient_username
        self.message_manager = message_manager
        self.back_callback = back_callback
        
        # ID Chat untuk grup biasanya nama grup itu sendiri atau hash dari nama grup
        self.chat_id = f"GROUP_{self.group_name}"
        self.session_crypto = CryptoEngine(shared_password)
        
        self.api_url = "https://morsz.azeroth.site/"
        self.MAX_FILE_SIZE = 2 * 1024 * 1024 # 2MB
        
        script_file_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_file_path)
        base_project_dir = os.path.dirname(script_dir)

        self.base_data_dir = os.path.join(base_project_dir, "local_data")
        self.cache_dir = os.path.join(self.base_data_dir, "group_caches") # Cache khusus grup
        self.cache_file = os.path.join(self.cache_dir, f"cache_{self.chat_id}.json")
        self.message_cache = self.load_cache()
        
        self.temp_stegano_dir = os.path.join(self.base_data_dir, "temp_stegano")
        self.temp_download_dir = os.path.join(self.base_data_dir, "temp_downloads")
        self.temp_decrypted_dir = os.path.join(self.base_data_dir, "temp_decrypted")
        
        self.rendered_message_ids = set()
        
        for folder in [self.base_data_dir, self.cache_dir, self.temp_stegano_dir, self.temp_download_dir, self.temp_decrypted_dir]:
            if not os.path.exists(folder):
                os.makedirs(folder)

        self.init_ui() 
        
        QTimer.singleShot(0, self.refresh_chat_display)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.refresh_chat_display)
        self.poll_timer.start(1000) 

    # --- Cache Functions ---
    def get_message_id(self, metadata):
        msg_type = metadata.get('type')
        if msg_type == 'text':
            return hashlib.md5(metadata.get('data', '').encode('utf-8')).hexdigest()
        elif msg_type in ['stegano', 'file']:
            return metadata.get('file_id')
        return None

    def load_cache(self):
        if not os.path.exists(self.cache_file): return {}
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError): return {} 

    def save_to_cache(self, message_id, data_to_cache):
        if not message_id: return
        self.message_cache[message_id] = data_to_cache
        try:
            if not os.path.exists(self.cache_dir):
                os.makedirs(self.cache_dir)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.message_cache, f, indent=2, ensure_ascii=False)
        except IOError as e: print(f"Peringatan: Gagal menyimpan cache ke file: {e}")
    # -----------------------

    def init_ui(self):
        self.resize(700, 800) 
        self.setStyleSheet(f"background-color: {self.COLOR_BACKGROUND};")
        layout = QVBoxLayout(self); layout.setContentsMargins(20, 20, 20, 20); layout.setSpacing(15)

        # --- Top Bar ---
        top_bar_layout = QHBoxLayout()
        back_btn = QPushButton("< Back")
        back_btn.setStyleSheet(self.button_style(
            base=self.COLOR_RED, hover=self.COLOR_RED_HOVER, pressed=self.COLOR_RED_PRESSED, radius=10
        ))
        back_btn.clicked.connect(self.handle_back_pressed)
        back_btn.setFixedWidth(80)
        
        # Judul Grup
        title = QLabel(f"👥 Group: {self.group_name}")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {self.COLOR_GOLD};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # [INSTRUKSI 1] Tombol Invite
        invite_btn = QPushButton("Invite +")
        invite_btn.setToolTip("Undang orang ke grup")
        invite_btn.setStyleSheet(self.button_style(
            base=self.COLOR_CARD, hover=self.COLOR_CARD_HOVER, pressed=self.COLOR_CARD_BG, radius=10
        ))
        invite_btn.setFixedWidth(80)
        invite_btn.clicked.connect(self.handle_invite_user)
        
        top_bar_layout.addWidget(back_btn)
        top_bar_layout.addWidget(title)
        top_bar_layout.addWidget(invite_btn)
        
        # --- Area Chat ---
        self.chat_display = QListWidget()
        self.chat_display.setStyleSheet(f"""
            QListWidget {{ 
                background-color: {self.COLOR_PANE_LEFT}; 
                border: 2px solid {self.COLOR_GOLD};
                border-radius: 12px; 
                color: {self.COLOR_TEXT}; 
            }}
        """)
        self.chat_display.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.chat_display.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.chat_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.chat_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_display.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.chat_display.setUniformItemSizes(False)
        self.chat_display.setLayoutMode(QListView.LayoutMode.Batched)
        self.chat_display.setBatchSize(10)
        self.chat_display.setWordWrap(False)
        self.chat_display.itemClicked.connect(self.on_chat_item_clicked)

        # --- Input Bar ---
        input_bar_layout = QHBoxLayout()
        self.attach_btn = QPushButton("🖼️ Gbr"); 
        self.attach_btn.setToolTip("Steganografi")
        self.attach_btn.setFont(QFont("Segoe UI", 12))
        self.attach_btn.setStyleSheet(self.button_style(
            base=self.COLOR_CARD, hover=self.COLOR_CARD_HOVER, pressed=self.COLOR_CARD_BG, radius=10
        ))
        self.attach_btn.setFixedSize(70, 45)
        self.attach_btn.clicked.connect(self.handle_attach_image_stegano)

        self.attach_file_btn = QPushButton("📂 File"); 
        self.attach_file_btn.setToolTip("Enkripsi file")
        self.attach_file_btn.setFont(QFont("Segoe UI", 12))
        self.attach_file_btn.setStyleSheet(self.button_style(
            base=self.COLOR_CARD, hover=self.COLOR_CARD_HOVER, pressed=self.COLOR_CARD_BG, radius=10
        ))
        self.attach_file_btn.setFixedSize(70, 45)
        self.attach_file_btn.clicked.connect(self.handle_attach_file) 

        self.message_input = QLineEdit(); self.message_input.setPlaceholderText(f"Pesan di #{self.group_name}...")
        self.message_input.setStyleSheet(self.input_style()) 
        self.message_input.returnPressed.connect(self.handle_send_message_super)

        self.send_btn = QPushButton("Send"); 
        self.send_btn.setFont(QFont("Segoe UI", 11, QFont.Bold)); 
        self.send_btn.setStyleSheet(self.button_style(
            base=self.COLOR_GOLD, hover=self.COLOR_GOLD_HOVER, pressed=self.COLOR_GOLD_PRESSED, 
            radius=22, text_color=self.COLOR_PANE_LEFT
        ))
        self.send_btn.setFixedSize(90, 45)
        self.send_btn.clicked.connect(self.handle_send_message_super)

        input_bar_layout.addWidget(self.attach_btn); input_bar_layout.addWidget(self.attach_file_btn)
        input_bar_layout.addWidget(self.message_input); input_bar_layout.addWidget(self.send_btn)
        layout.addLayout(top_bar_layout); layout.addWidget(self.chat_display); layout.addLayout(input_bar_layout)

    def handle_back_pressed(self):
        if hasattr(self, 'poll_timer') and self.poll_timer.isActive():
            self.poll_timer.stop()
        self.back_callback()

    # [INSTRUKSI 1] Fitur Invite
    def handle_invite_user(self):
        username, ok = QInputDialog.getText(self, "Invite User", "Masukkan username untuk diundang:")
        if ok and username:
            # Mengirim pesan sistem ke grup sebagai notifikasi invite
            system_msg = f"--- INFO: {self.current_user} mengundang {username} ke grup ---"
            
            # Kita enkripsi pesan sistem ini agar aman
            # Menggunakan AES Sesi grup saja (tanpa vigenere user/whitemist yg rumit untuk notif)
            try:
                data_bytes = system_msg.encode('utf-8')
                encrypted_payload = self.session_crypto.encrypt(data_bytes)
                
                metadata = {
                    'type': 'text',
                    'sender': 'SYSTEM',
                    'recipient': self.chat_id, # Targetnya adalah Grup ID
                    'data': encrypted_payload.decode('utf-8'),
                    'is_system_msg': True,
                    'db_timestamp': datetime.now(timezone.utc).astimezone().isoformat()
                }
                self.message_manager.save_message(self.chat_id, metadata)
                QMessageBox.information(self, "Sukses", f"Undangan dikirim ke {username} (simulasi).")
                self.refresh_chat_display()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Gagal invite: {e}")

    def refresh_chat_display(self):
        all_messages = self.message_manager.load_messages(self.chat_id)
        new_messages_found = False

        for msg_data in all_messages:
            msg_id = self.get_message_id(msg_data)
            
            if msg_id and msg_id not in self.rendered_message_ids:
                # Logika Align: Kanan jika saya pengirim, Kiri jika orang lain
                align = "sent" if msg_data['sender'] == self.current_user else "received"
                cached_data = self.message_cache.get(msg_id)
                
                self.add_message_to_display(align, msg_data, cached_data)
                
                self.rendered_message_ids.add(msg_id)
                new_messages_found = True
        
        if new_messages_found:
            QApplication.processEvents()
            self.chat_display.scrollToBottom()

    def handle_send_message_super(self):
        message_text = self.message_input.text() 
        if not message_text: return
        
        # Di Group chat, kita bisa menggunakan shared key grup untuk Vigenere juga
        # Atau meminta input kunci lagi. Untuk konsistensi dengan chat.py, kita minta input.
        user_key, ok = QInputDialog.getText(self, "Kunci Pesan Grup", "Masukkan Kunci Enkripsi Pesan:")
        if not (ok and user_key): return 
        
        self.message_input.clear()
        try:
            vigenere_encrypted_text = vigenere_encrypt(message_text, user_key)
            vigenere_encrypted_bytes = vigenere_encrypted_text.encode('utf-8')
            whitemist_encrypted_string = encrypt_whitemist(vigenere_encrypted_bytes, user_key, is_text=True)
            
            data_bytes_for_aes = whitemist_encrypted_string.encode('utf-8')
            encrypted_payload_bytes = self.session_crypto.encrypt(data_bytes_for_aes)
            
            metadata = { 
                'type': 'text', 
                'sender': self.current_user, 
                'recipient': self.chat_id, # Recipient adalah ID Grup
                'data': encrypted_payload_bytes.decode('utf-8'), 
                'vigenere_key_debug': user_key,
                'db_timestamp': datetime.now(timezone.utc).astimezone().isoformat()
            }
            self.message_manager.save_message(self.chat_id, metadata)
            message_id = self.get_message_id(metadata)
            self.save_to_cache(message_id, message_text)
            self.refresh_chat_display()
            
        except Exception as e: 
            self.add_message_to_display("error", metadata=None, error_text=f"Error: {e}")

    # --- Stegano & File logic sama dengan Chat.py, disesuaikan sedikit untuk Grup ---
    def handle_attach_image_stegano(self):
        message_to_hide = self.message_input.text()
        if not message_to_hide:
            QMessageBox.warning(self, "Error", "Tulis pesan dulu.")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih Gambar (.png)", "", "Images (*.png)")
        if not file_path: return
        
        text_key, ok = QInputDialog.getText(self, "Kunci Stegano", "Masukkan Kunci Vigenere:")
        if not (ok and text_key): return
        
        if not os.path.exists(self.temp_stegano_dir): os.makedirs(self.temp_stegano_dir)
        base_filename = os.path.basename(file_path)
        temp_filename = os.path.join(self.temp_stegano_dir, f"stego_group_{uuid.uuid4()}.png") 
        
        try:
            encrypted_text_raw = vigenere_encrypt(message_to_hide, text_key)
            safe_payload = base64.b64encode(encrypted_text_raw.encode('utf-8')).decode('utf-8')
            header = f"<LEN:{len(safe_payload):010d}>"
            payload_final = header + safe_payload + "|||END_MORSZ|||"
            
            secret_image = lsb.hide(file_path, payload_final)
            secret_image.save(temp_filename)
            
            self.add_message_to_display("error", metadata=None, error_text=f"--- Mengunggah {base_filename}... ---")
            
            # Gunakan chat_id grup untuk folder upload
            with open(temp_filename, "rb") as f:
                files = {'file': (base_filename, f, 'image/png')}
                upload_url = f"{self.api_url}/upload_file/{self.chat_id}"
                response = requests.post(upload_url, files=files, timeout=30)
            
            if response.status_code != 200: raise Exception("Gagal upload")
                
            file_id = response.json().get("file_id")
            metadata = { 
                'type': 'stegano', 'sender': self.current_user, 'recipient': self.chat_id, 
                'data': None, 'file_id': file_id, 'filename': base_filename, 
                'text_key_debug': text_key,
                'db_timestamp': datetime.now(timezone.utc).astimezone().isoformat()
            }
            self.message_manager.save_message(self.chat_id, metadata)
            
            # Cache
            message_id = self.get_message_id(metadata)
            cached_stego_path = os.path.join(self.temp_stegano_dir, file_id)
            import shutil
            shutil.copy(temp_filename, cached_stego_path)
            cache_data = {"text": message_to_hide, "image_path": cached_stego_path} 
            self.save_to_cache(message_id, cache_data)

            self.refresh_chat_display()
            self.message_input.clear()
            os.remove(temp_filename)
            
        except Exception as e:
            self.add_message_to_display("error", metadata=None, error_text=f"Error Stegano: {e}")

    def handle_attach_file(self):
        # Logika file sama, hanya recipient = self.chat_id
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih File", "", "All Files (*.*)")
        if not file_path: return
        
        method, ok = QInputDialog.getItem(self, "Metode", "Metode:", ["AES (Modern)", "White-Mist"], 0, False)
        if not ok: return
        key, ok = QInputDialog.getText(self, "Kunci", f"Masukkan Kunci {method}:", QLineEdit.Password)
        if not (ok and key): return
        
        try:
            with open(file_path, "rb") as f: data_bytes = f.read()
            filename = os.path.basename(file_path)
            if method == "AES (Modern)":
                temp_crypto = CryptoEngine(key); encrypted_payload_bytes = temp_crypto.encrypt(data_bytes)
                metadata = { 'type': 'file', 'sender': self.current_user, 'recipient': self.chat_id, 'data': None, 'encryption_method': 'aes', 'aes_key_debug': key, 'filename': filename }
            else:
                encrypted_string = encrypt_whitemist(data_bytes, key); encrypted_payload_bytes = encrypted_string.encode('utf-8')
                metadata = { 'type': 'file', 'sender': self.current_user, 'recipient': self.chat_id, 'data': None, 'encryption_method': 'whitemist', 'aes_key_debug': key, 'filename': filename }
            
            self.add_message_to_display("error", metadata=None, error_text=f"--- Mengunggah {filename}... ---")
            
            files = {'file': (f"{filename}.enc", encrypted_payload_bytes, 'application/octet-stream')}
            upload_url = f"{self.api_url}/upload_file/{self.chat_id}"
            response = requests.post(upload_url, files=files, timeout=60)
            if response.status_code != 200: raise Exception("Gagal upload")
            
            file_id = response.json().get("file_id")
            metadata['file_id'] = file_id 
            metadata['db_timestamp'] = datetime.now(timezone.utc).astimezone().isoformat()
            self.message_manager.save_message(self.chat_id, metadata)
            self.refresh_chat_display()
        except Exception as e: 
             self.add_message_to_display("error", metadata=None, error_text=f"Error Upload: {e}")

    def on_chat_item_clicked(self, item):
        # Logika dekripsi sama persis dengan chat.py, 
        # kecuali pengecekan sender untuk align bubble
        metadata = item.data(Qt.UserRole)
        if not metadata: return
        
        # Handle System Message (Invite Info)
        if metadata.get('is_system_msg'):
            try:
                encrypted_data = metadata.get('data').encode('utf-8')
                decrypted_bytes = self.session_crypto.decrypt(encrypted_data)
                QMessageBox.information(self, "Info Sistem", decrypted_bytes.decode('utf-8'))
            except:
                QMessageBox.information(self, "Info Sistem", "Pesan sistem tidak dapat didekripsi.")
            return

        # Panggil logic dekripsi (copy paste dari chat.py logic)
        self.decrypt_content(item, metadata)

    def decrypt_content(self, item, metadata):
        # ... (Logika dekripsi sama dengan chat.py, disederhanakan disini untuk hemat tempat 
        # tapi fungsinya harus ada. Saya akan menggunakan struktur yg sama) ...
        msg_type = metadata.get('type')
        file_id = metadata.get('file_id')
        
        if msg_type == 'text':
             message_id = self.get_message_id(metadata)
             encrypted_data_b64 = metadata.get('data')
             if not encrypted_data_b64: return
             key, ok = QInputDialog.getText(self, "Dekripsi", "Masukkan Kunci Pesan:")
             if ok and key:
                try:
                    decrypted_bytes_from_aes = self.session_crypto.decrypt(encrypted_data_b64.encode('utf-8'))
                    whitemist_encrypted_string = decrypted_bytes_from_aes.decode('utf-8')
                    try:
                        vigenere_encrypted_bytes = decrypt_whitemist(whitemist_encrypted_string, key, is_text=True)
                        vigenere_encrypted_text = vigenere_encrypted_bytes.decode('utf-8')
                    except:
                        vigenere_encrypted_text = whitemist_encrypted_string 
                    decrypted_text = vigenere_decrypt(vigenere_encrypted_text, key)
                    
                    if message_id: self.save_to_cache(message_id, decrypted_text)
                    self.update_bubble_content(item, metadata, decrypted_text)
                except Exception as e: QMessageBox.warning(self, "Gagal", f"Dekripsi gagal: {e}")
        
        elif msg_type == 'stegano' and file_id:
             # Logic sama dengan Chat.py
             local_path = os.path.join(self.temp_stegano_dir, file_id)
             if not os.path.exists(local_path):
                 # Download logic...
                 url = f"{self.api_url}/download_file/{self.chat_id}/{file_id}"
                 r = requests.get(url); 
                 with open(local_path, "wb") as f: f.write(r.content)
             
             # Show & Decrypt Dialog...
             msg_box = QMessageBox(self); msg_box.setText("Dekripsi Gambar?")
             msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
             if msg_box.exec() == QMessageBox.Ok:
                 key, ok = QInputDialog.getText(self, "Kunci", "Kunci Stegano:")
                 if ok and key:
                     try:
                         raw = lsb.reveal(local_path)
                         if "|||END_MORSZ|||" in raw: raw = raw.split("|||END_MORSZ|||")[0]
                         if raw.startswith("<LEN:"): raw = raw[16:16+int(raw[5:15])]
                         try: ct = base64.b64decode(raw).decode('utf-8')
                         except: ct = raw
                         pt = vigenere_decrypt(ct, key)
                         
                         QMessageBox.information(self, "Pesan", pt)
                         message_id = self.get_message_id(metadata)
                         if message_id: self.save_to_cache(message_id, {"text": pt, "image_path": local_path})
                         self.update_bubble_content(item, metadata, {"text": pt, "image_path": local_path})
                     except Exception as e: QMessageBox.warning(self, "Error", str(e))

        elif msg_type == 'file' and file_id:
             # Logic sama dengan Chat.py
             local_path = os.path.join(self.temp_download_dir, file_id)
             if not os.path.exists(local_path):
                 url = f"{self.api_url}/download_file/{self.chat_id}/{file_id}"
                 r = requests.get(url)
                 with open(local_path, "wb") as f: f.write(r.content)
             
             key, ok = QInputDialog.getText(self, "Dekripsi File", "Kunci File:", QLineEdit.Password)
             if ok and key:
                 try:
                     with open(local_path, "rb") as f: enc_data = f.read()
                     method = metadata.get('encryption_method')
                     if method == 'aes': dec_data = CryptoEngine(key).decrypt(enc_data)
                     else: dec_data = decrypt_whitemist(enc_data.decode('utf-8'), key)
                     
                     save_path = os.path.join(self.temp_decrypted_dir, f"DEC_{metadata.get('filename')}")
                     with open(save_path, "wb") as f: f.write(dec_data)
                     QMessageBox.information(self, "Sukses", f"File disimpan di:\n{save_path}")
                 except Exception as e: QMessageBox.warning(self, "Gagal", str(e))

    def update_bubble_content(self, item, metadata, content):
        align = "sent" if metadata['sender'] == self.current_user else "received"
        new_widget = self.create_chat_bubble(align, metadata, content, item)
        new_widget.layout().activate(); new_widget.adjustSize()
        real_size = new_widget.size(); real_size.setHeight(real_size.height() + 10)
        item.setSizeHint(real_size); self.chat_display.setItemWidget(item, new_widget)

    def create_chat_bubble(self, align, metadata, cached_data=None, item=None):
        # Bubble creation logic (mirip chat.py)
        bubble_container = QWidget()
        container_layout = QHBoxLayout(bubble_container); container_layout.setContentsMargins(5,5,5,5)
        
        bubble_frame = QFrame()
        bubble_frame.setMinimumWidth(200); bubble_frame.setMaximumWidth(450)
        content_layout = QVBoxLayout(bubble_frame)
        
        sender_name = "YOU" if align == "sent" else metadata.get('sender', 'Unknown')
        lbl_name = QLabel(sender_name); lbl_name.setStyleSheet(f"color: {self.COLOR_GOLD}; font-weight: bold;")
        content_layout.addWidget(lbl_name)
        
        msg_type = metadata.get('type')
        if msg_type == 'text':
            txt = cached_data if isinstance(cached_data, str) else "🔒 [Pesan Terenkripsi]"
            lbl_msg = QLabel(txt); lbl_msg.setWordWrap(True); lbl_msg.setStyleSheet(f"color: {self.COLOR_TEXT};")
            content_layout.addWidget(lbl_msg)
        elif msg_type == 'stegano':
            lbl_msg = QLabel("🖼️ Gambar Stegano"); lbl_msg.setStyleSheet(f"color: {self.COLOR_TEXT_SUBTLE}; font-style: italic;")
            content_layout.addWidget(lbl_msg)
            if isinstance(cached_data, dict):
                 lbl_hidden = QLabel(f"Isi: {cached_data.get('text')}"); lbl_hidden.setStyleSheet(f"color: {self.COLOR_TEXT};")
                 content_layout.addWidget(lbl_hidden)
        elif msg_type == 'file':
            lbl_msg = QLabel(f"📂 File: {metadata.get('filename')}"); lbl_msg.setStyleSheet(f"color: {self.COLOR_TEXT_SUBTLE};")
            content_layout.addWidget(lbl_msg)

        # Timestamp & Refresh
        row_btm = QHBoxLayout()
        ts = metadata.get('db_timestamp', '')[11:16]
        lbl_time = QLabel(ts); lbl_time.setStyleSheet("color: gray; font-size: 10px;")
        btn_ref = QPushButton("🔄"); btn_ref.setFixedSize(20,20); btn_ref.setStyleSheet("background: transparent; color: white;")
        if item: btn_ref.clicked.connect(lambda: self.on_chat_item_clicked(item))
        row_btm.addWidget(lbl_time); row_btm.addStretch(); row_btm.addWidget(btn_ref)
        content_layout.addLayout(row_btm)
        
        if align == "sent":
            bubble_frame.setStyleSheet(f"background-color: {self.COLOR_BUBBLE_SENT}; border-radius: 10px; border-bottom-right-radius: 0;")
            container_layout.addStretch(); container_layout.addWidget(bubble_frame)
        else:
            bubble_frame.setStyleSheet(f"background-color: {self.COLOR_BUBBLE_RECV}; border-radius: 10px; border-bottom-left-radius: 0;")
            container_layout.addWidget(bubble_frame); container_layout.addStretch()
            
        return bubble_container

    def add_message_to_display(self, align, metadata, cached_data=None, error_text=None):
        item = QListWidgetItem(); item.setData(Qt.UserRole, metadata)
        if error_text:
            item.setText(error_text); item.setForeground(QColor(self.COLOR_RED)); item.setTextAlignment(Qt.AlignCenter)
            self.chat_display.addItem(item)
        else:
            wid = self.create_chat_bubble(align, metadata, cached_data, item)
            wid.adjustSize()
            item.setSizeHint(QSize(wid.size().width(), wid.size().height()+10))
            self.chat_display.addItem(item); self.chat_display.setItemWidget(item, wid)

    # Styles
    def input_style(self):
        return f"QLineEdit {{ background-color: {self.COLOR_CARD}; border: 2px solid {self.COLOR_GOLD}; border-radius: 22px; padding: 10px; color: {self.COLOR_TEXT}; }}"
    def button_style(self, base, hover, pressed, radius=12, text_color=None):
        tc = text_color if text_color else self.COLOR_TEXT
        return f"QPushButton {{ background-color: {base}; color: {tc}; border-radius: {radius}px; padding: 8px; font-weight: bold; }} QPushButton:hover {{ background-color: {hover}; }} QPushButton:pressed {{ background-color: {pressed}; }}"