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
    QSizePolicy, QListView, QMenu, QAbstractItemView
)
from PySide6.QtGui import QFont, QColor, QPixmap, QAction, QCursor
from PySide6.QtCore import Qt, QSize, QTimer
from datetime import datetime, timezone 

# Pastikan utils.py ada di satu folder yang sama
from utils import CryptoEngine, vigenere_encrypt, vigenere_decrypt, encrypt_whitemist, decrypt_whitemist

class ChatPage(QWidget):
    
    # --- Palet Warna ---
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
    COLOR_BUBBLE_RECV = "#3E3C6E"
    # -------------------

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
        
        script_file_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_file_path)
        base_project_dir = os.path.dirname(script_dir)

        self.base_data_dir = os.path.join(base_project_dir, "local_data")
        self.cache_dir = os.path.join(self.base_data_dir, "user_caches")
        self.cache_file = os.path.join(self.cache_dir, f"cache_{self.current_user}.json")
        self.message_cache = self.load_cache()
        
        self.temp_stegano_dir = os.path.join(self.base_data_dir, "temp_stegano")
        self.temp_download_dir = os.path.join(self.base_data_dir, "temp_downloads")
        self.temp_decrypted_dir = os.path.join(self.base_data_dir, "temp_decrypted")
        
        self.rendered_message_ids = set()
        self.last_loaded_count = 0
        
        for folder in [self.base_data_dir, self.cache_dir, self.temp_stegano_dir, self.temp_download_dir, self.temp_decrypted_dir]:
            if not os.path.exists(folder):
                os.makedirs(folder)

        self.init_ui() 
        
        QTimer.singleShot(0, self.refresh_chat_display)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.refresh_chat_display)
        self.poll_timer.start(1000) 

    # --- Resize Event Fix: Recalculate heights on window resize ---
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Force re-layout of all items in list widget to fix wrapping
        # This prevents "Layout Ngaco" when window size changes
        for i in range(self.chat_display.count()):
            item = self.chat_display.item(i)
            widget = self.chat_display.itemWidget(item)
            if widget:
                widget.adjustSize()
                new_size = widget.sizeHint()
                new_size.setHeight(new_size.height() + 10)
                item.setSizeHint(new_size)
    # -------------------------------------------------------------

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

    def init_ui(self):
        self.resize(700, 800) 
        self.setStyleSheet(f"background-color: {self.COLOR_BACKGROUND};")
        layout = QVBoxLayout(self); layout.setContentsMargins(20, 20, 20, 20); layout.setSpacing(15)

        top_bar_layout = QHBoxLayout()
        back_btn = QPushButton("< Back")
        back_btn.setStyleSheet(self.button_style(
            base=self.COLOR_RED, hover=self.COLOR_RED_HOVER, pressed=self.COLOR_RED_PRESSED, radius=10
        ))
        
        back_btn.clicked.connect(self.handle_back_pressed)
        back_btn.setFixedWidth(100)
        
        title = QLabel(f"Chat with: {self.recipient_username}")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {self.COLOR_GOLD};"); 
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        top_bar_layout.addWidget(back_btn); top_bar_layout.addWidget(title)
        
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
        
        # --- [OPTIMASI RENDERING FINAL] ---
        # ScrollPerPixel = Smooth scrolling
        # UniformItemSizes = False (Karena tinggi chat beda-beda)
        # Batched = Render bertahap
        self.chat_display.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.chat_display.setUniformItemSizes(False) 
        self.chat_display.setResizeMode(QListView.ResizeMode.Adjust)
        self.chat_display.setLayoutMode(QListView.LayoutMode.Batched)
        self.chat_display.setBatchSize(10)
        # -----------------------------
        
        self.chat_display.itemClicked.connect(self.on_chat_item_clicked)

        input_bar_layout = QHBoxLayout()
        self.attach_btn = QPushButton("🖼️ Gbr"); self.attach_btn.setToolTip("Steganografi")
        self.attach_btn.setFont(QFont("Segoe UI", 12)); 
        self.attach_btn.setStyleSheet(self.button_style(
            base=self.COLOR_CARD, hover=self.COLOR_CARD_HOVER, pressed=self.COLOR_CARD_BG, radius=10
        ))
        self.attach_btn.setFixedSize(70, 45)
        self.attach_btn.clicked.connect(self.handle_attach_image_stegano)

        self.attach_file_btn = QPushButton("📂 File"); 
        self.attach_file_btn.setToolTip("Enkripsi file")
        self.attach_file_btn.setFont(QFont("Segoe UI", 12)); 
        self.attach_file_btn.setStyleSheet(self.button_style(
            base=self.COLOR_CARD, hover=self.COLOR_CARD_HOVER, pressed=self.COLOR_CARD_BG, radius=10
        ))
        self.attach_file_btn.setFixedSize(70, 45)
        self.attach_file_btn.clicked.connect(self.handle_attach_file) 

        self.message_input = QLineEdit(); self.message_input.setPlaceholderText("Ketik pesan...")
        self.message_input.setStyleSheet(self.input_style()) 
        self.message_input.returnPressed.connect(self.handle_send_message_super)

        self.send_btn = QPushButton("Send Txt"); self.send_btn.setToolTip("Kirim teks")
        self.send_btn.setFont(QFont("Segoe UI", 11, QFont.Bold)); 
        self.send_btn.setStyleSheet(self.button_style(
            base=self.COLOR_GOLD, hover=self.COLOR_GOLD_HOVER, pressed=self.COLOR_GOLD_PRESSED, 
            radius=22, text_color=self.COLOR_PANE_LEFT
        ))
        self.send_btn.setFixedSize(100, 45)
        self.send_btn.clicked.connect(self.handle_send_message_super)

        input_bar_layout.addWidget(self.attach_btn); input_bar_layout.addWidget(self.attach_file_btn)
        input_bar_layout.addWidget(self.message_input); input_bar_layout.addWidget(self.send_btn)
        layout.addLayout(top_bar_layout); layout.addWidget(self.chat_display); layout.addLayout(input_bar_layout)
        
    def handle_back_pressed(self):
        if hasattr(self, 'poll_timer') and self.poll_timer.isActive():
            self.poll_timer.stop()
        self.back_callback()

    def refresh_chat_display(self):
        all_messages = self.message_manager.load_messages(self.chat_id)
        current_count = len(all_messages)

        if current_count == self.last_loaded_count:
            return

        start_index = self.last_loaded_count
        if current_count < self.last_loaded_count:
            self.chat_display.clear()
            self.rendered_message_ids.clear()
            start_index = 0

        new_messages_list = all_messages[start_index:]
        new_messages_found = False

        for msg_data in new_messages_list:
            msg_id = self.get_message_id(msg_data)
            
            if msg_id and msg_id not in self.rendered_message_ids:
                align = "sent" if msg_data['sender'] == self.current_user else "received"
                cached_data = self.message_cache.get(msg_id)
                self.add_message_to_display(align, msg_data, cached_data)
                self.rendered_message_ids.add(msg_id)
                new_messages_found = True
        
        self.last_loaded_count = current_count

        if new_messages_found:
            QApplication.processEvents()
            self.chat_display.scrollToBottom()

    def handle_send_message_super(self):
        message_text = self.message_input.text() 
        if not message_text: return
        user_key, ok = QInputDialog.getText(self, "Kunci Super Enkripsi", "Masukkan Kunci (untuk Vigenere + White Mist):")
        if not (ok and user_key): return 
        self.message_input.clear()
        try:
            vigenere_encrypted_text = vigenere_encrypt(message_text, user_key)
            vigenere_encrypted_bytes = vigenere_encrypted_text.encode('utf-8')
            whitemist_encrypted_string = encrypt_whitemist(vigenere_encrypted_bytes, user_key, is_text=True)
            data_bytes_for_aes = whitemist_encrypted_string.encode('utf-8')
            encrypted_payload_bytes = self.session_crypto.encrypt(data_bytes_for_aes)
            metadata = { 
                'type': 'text', 'sender': self.current_user, 'recipient': self.recipient_username, 
                'data': encrypted_payload_bytes.decode('utf-8'), 'vigenere_key_debug': user_key,
                'db_timestamp': datetime.now(timezone.utc).astimezone().isoformat()
            }
            self.message_manager.save_message(self.chat_id, metadata)
            message_id = self.get_message_id(metadata)
            self.save_to_cache(message_id, message_text)
            self.refresh_chat_display()
        except Exception as e: 
            self.add_message_to_display("error", metadata=None, error_text=f"--- Error Super Enkripsi: {e} ---")

    def handle_attach_image_stegano(self):
        message_to_hide = self.message_input.text()
        if not message_to_hide:
            QMessageBox.warning(self, "Error", "Tulis dulu pesan.")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih Gambar", "", "Images (*.png)")
        if not file_path: return
        
        text_key, ok = QInputDialog.getText(self, "Kunci Steganografi", "Masukkan Kunci VIGENERE:")
        if not (ok and text_key): return
        
        if not os.path.exists(self.temp_stegano_dir): os.makedirs(self.temp_stegano_dir)
        base_filename = os.path.basename(file_path)
        temp_filename = os.path.join(self.temp_stegano_dir, f"stego_{uuid.uuid4()}.png") 
        
        try:
            encrypted_text_raw = vigenere_encrypt(message_to_hide, text_key)
            safe_payload = base64.b64encode(encrypted_text_raw.encode('utf-8')).decode('utf-8')
            header = f"<LEN:{len(safe_payload):010d}>"
            payload_final = header + safe_payload + "|||END_MORSZ|||"
            
            secret_image = lsb.hide(file_path, payload_final)
            secret_image.save(temp_filename)
            
            self.add_message_to_display("error", metadata=None, error_text=f"--- Mengunggah {base_filename}... ---")
            
            with open(temp_filename, "rb") as f:
                files = {'file': (base_filename, f, 'image/png')}
                upload_url = f"{self.api_url}/upload_file/{self.chat_id}"
                response = requests.post(upload_url, files=files, timeout=30)
            
            if response.status_code != 200 or not response.json().get("success"):
                raise Exception("Gagal upload")
                
            file_id = response.json().get("file_id")
            metadata = { 
                'type': 'stegano', 'sender': self.current_user, 'recipient': self.recipient_username, 
                'data': None, 'file_id': file_id, 'filename': base_filename, 
                'text_key_debug': text_key, 'db_timestamp': datetime.now(timezone.utc).astimezone().isoformat()
            }
            self.message_manager.save_message(self.chat_id, metadata)
            
            message_id = self.get_message_id(metadata)
            cached_stego_path = os.path.join(self.temp_stegano_dir, file_id)
            try:
                import shutil
                shutil.copy(temp_filename, cached_stego_path)
            except: pass
            
            cache_data = {"text": message_to_hide, "image_path": cached_stego_path} 
            self.save_to_cache(message_id, cache_data)
            self.refresh_chat_display()
            self.message_input.clear()
            os.remove(temp_filename)
            
        except Exception as e:
            self.add_message_to_display("error", metadata=None, error_text=f"Error: {e}")
            if os.path.exists(temp_filename): os.remove(temp_filename)
            
    def handle_attach_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih File", "", "All Files (*.*)")
        if not file_path: return
        
        methods = ["AES (Modern)", "White-Mist (Eksperimental)"]
        method, ok = QInputDialog.getItem(self, "Pilih Metode", "Metode:", methods, 0, False)
        if not ok: return
        key, ok = QInputDialog.getText(self, "Kunci", f"Masukkan Kunci {method}:", QLineEdit.Password)
        if not (ok and key): return
        try:
            with open(file_path, "rb") as f: data_bytes = f.read()
            filename = os.path.basename(file_path)
            encrypted_payload_bytes = None; metadata = {}
            if method == "AES (Modern)":
                temp_crypto = CryptoEngine(key); encrypted_payload_bytes = temp_crypto.encrypt(data_bytes)
                metadata = { 'type': 'file', 'sender': self.current_user, 'recipient': self.recipient_username, 'data': None, 'encryption_method': 'aes', 'aes_key_debug': key, 'filename': filename }
            else:
                encrypted_string = encrypt_whitemist(data_bytes, key); encrypted_payload_bytes = encrypted_string.encode('utf-8')
                metadata = { 'type': 'file', 'sender': self.current_user, 'recipient': self.recipient_username, 'data': None, 'encryption_method': 'whitemist', 'aes_key_debug': key, 'filename': filename }
            
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

    def show_loading_dialog(self, filename):
        dialog = QDialog(self)
        dialog.setModal(True)
        dialog.setWindowTitle("Mengunduh...")
        dialog.setStyleSheet(f"background-color: {self.COLOR_BACKGROUND}; color: {self.COLOR_TEXT}; font-size: 14px;")
        layout = QVBoxLayout()
        label = QLabel(f"Sedang mengunduh:\n{filename}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        dialog.setLayout(layout)
        dialog.setFixedSize(300, 150)
        dialog.show()
        QApplication.processEvents() 
        return dialog

    def on_chat_item_clicked(self, item):
        metadata = item.data(Qt.UserRole)
        if not metadata: return
        
        msg_type = metadata.get('type')
        file_id = metadata.get('file_id')
        
        try:
            if msg_type == 'text':
                message_id = self.get_message_id(metadata)
                encrypted_data_b64 = metadata.get('data')
                if not encrypted_data_b64: return
                
                encrypted_data_b64 = encrypted_data_b64.encode('utf-8')
                key, ok = QInputDialog.getText(self, "Dekripsi Teks", "Masukkan Kunci:")
                if ok and key:
                    decrypted_text = ""
                    try:
                        decrypted_bytes_from_aes = self.session_crypto.decrypt(encrypted_data_b64)
                        whitemist_encrypted_string = decrypted_bytes_from_aes.decode('utf-8')
                        try:
                            vigenere_encrypted_bytes = decrypt_whitemist(whitemist_encrypted_string, key, is_text=True)
                            vigenere_encrypted_text = vigenere_encrypted_bytes.decode('utf-8')
                        except:
                            vigenere_encrypted_text = whitemist_encrypted_string 
                        decrypted_text = vigenere_decrypt(vigenere_encrypted_text, key)
                    except:
                        decrypted_text = f"[DEKRIPSI GAGAL]"
                    
                    if message_id: self.save_to_cache(message_id, decrypted_text)
                    
                    # Update UI
                    new_widget = self.create_chat_bubble("received" if metadata['sender'] != self.current_user else "sent", metadata, decrypted_text, item)
                    new_widget.layout().activate(); new_widget.adjustSize()
                    real_size = new_widget.sizeHint()
                    real_size.setHeight(real_size.height() + 10)
                    item.setSizeHint(real_size)
                    self.chat_display.setItemWidget(item, new_widget)

            elif msg_type == 'file' and file_id:
                local_path = os.path.join(self.temp_download_dir, file_id)
                filename = metadata.get('filename', 'file.enc')
                if not os.path.exists(local_path):
                    loading_dialog = self.show_loading_dialog(filename)
                    download_url = f"{self.api_url}/download_file/{self.chat_id}/{file_id}"
                    response = requests.get(download_url, timeout=60)
                    loading_dialog.close() 
                    if response.status_code != 200: raise Exception("Gagal unduh.")
                    with open(local_path, "wb") as f: f.write(response.content)
                
                key, ok = QInputDialog.getText(self, "Dekripsi File", "Masukkan Kunci:", QLineEdit.Password)
                if not (ok and key): return
                
                with open(local_path, "rb") as f: encrypted_bytes = f.read()
                decrypted_bytes = None; method = metadata.get('encryption_method', 'aes')
                
                if method == 'aes':
                    temp_crypto = CryptoEngine(key); decrypted_bytes = temp_crypto.decrypt(encrypted_bytes)
                elif method == 'whitemist':
                    encrypted_string = encrypted_bytes.decode('utf-8'); 
                    decrypted_bytes = decrypt_whitemist(encrypted_string, key)
                
                decrypted_path = os.path.join(self.temp_decrypted_dir, f"DECRYPTED_{filename}")
                with open(decrypted_path, "wb") as f: f.write(decrypted_bytes)
                QMessageBox.information(self, "Sukses", f"Disimpan di:\n{decrypted_path}")

            elif msg_type == 'stegano' and file_id:
                filename = metadata.get('filename', f"{file_id}.png")
                local_stegano_path = os.path.join(self.temp_stegano_dir, file_id) 
                
                if not os.path.exists(local_stegano_path):
                    loading_dialog = self.show_loading_dialog(filename)
                    download_url = f"{self.api_url}/download_file/{self.chat_id}/{file_id}"
                    try:
                        response = requests.get(download_url, timeout=60)
                        loading_dialog.close() 
                        if response.status_code != 200: raise Exception("Gagal unduh.")
                        with open(local_stegano_path, "wb") as f: f.write(response.content)
                    except: loading_dialog.close(); raise
                
                msg_box = QMessageBox(self); msg_box.setWindowTitle("Pesan Gambar")
                pixmap = QPixmap(local_stegano_path).scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                msg_box.setIconPixmap(pixmap)
                msg_box.setText("Gambar Steganografi diterima.")
                decrypt_button = msg_box.addButton("Dekripsi", QMessageBox.AcceptRole)
                msg_box.addButton(QMessageBox.Close); msg_box.exec()
                
                if msg_box.clickedButton() == decrypt_button:
                    key, ok = QInputDialog.getText(self, "Dekripsi", "Masukkan Kunci VIGENERE:")
                    if ok and key:
                        try:
                            raw_revealed = lsb.reveal(local_stegano_path)
                            if not raw_revealed: raise ValueError("Kosong.")
                            
                            clean_payload = raw_revealed
                            if raw_revealed.startswith("<LEN:") and len(raw_revealed) >= 16:
                                len_str = raw_revealed[5:15]
                                expected_len = int(len_str)
                                clean_payload = raw_revealed[16:16 + expected_len]
                            elif "|||END_MORSZ|||" in raw_revealed:
                                clean_payload = raw_revealed.split("|||END_MORSZ|||")[0]
                            
                            try: vigenere_ciphertext = base64.b64decode(clean_payload).decode('utf-8')
                            except: vigenere_ciphertext = clean_payload

                            decrypted_message = vigenere_decrypt(vigenere_ciphertext, key)
                            
                            message_id = self.get_message_id(metadata)
                            if message_id:
                                cache_data = {"text": decrypted_message, "image_path": local_stegano_path}
                                self.save_to_cache(message_id, cache_data)
                            
                            # Update UI
                            new_widget = self.create_chat_bubble("received" if metadata['sender'] != self.current_user else "sent", metadata, cache_data, item)
                            new_widget.layout().activate(); new_widget.adjustSize()
                            real_size = new_widget.sizeHint()
                            real_size.setHeight(real_size.height() + 10)
                            item.setSizeHint(real_size); self.chat_display.setItemWidget(item, new_widget)
                            
                        except Exception as e:
                            QMessageBox.critical(self, "Gagal", f"Error: {e}")

        except Exception as e:
            print(f"Error di clicked: {e}")

    # --- [FIX UTAMA LAG & LAYOUT] ---
    def create_chat_bubble(self, align, metadata, cached_data=None, item=None):
        bubble_container = QWidget()
        container_layout = QHBoxLayout(bubble_container)
        container_layout.setContentsMargins(5, 5, 5, 5)
        container_layout.setSpacing(0)

        bubble_frame = QFrame()
        bubble_frame.setFrameShape(QFrame.Shape.StyledPanel)
        bubble_frame.setFrameShadow(QFrame.Shadow.Plain)
        bubble_frame.setLineWidth(0)
        
        # Policy untuk lebar
        bubble_frame.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        bubble_frame.setMinimumWidth(int(self.width() * 0.1)) 
        bubble_frame.setMaximumWidth(int(self.width() * 0.75))

        bubble_content_layout = QVBoxLayout(bubble_frame)
        bubble_content_layout.setContentsMargins(12, 10, 12, 8)
        bubble_content_layout.setSpacing(8)
        
        msg_type = metadata.get('type', 'unknown')
        content_max_width = int(self.width() * 0.75) - 24
        
        if align == "sent":
            name_label = QLabel("YOU")
            name_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
            name_label.setStyleSheet(f"color: {self.COLOR_GOLD};")
            bubble_content_layout.addWidget(name_label)
        elif align == "received":
            prefix = metadata.get('sender', 'Unknown')
            name_label = QLabel(prefix)
            name_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
            name_label.setStyleSheet(f"color: {self.COLOR_GOLD};")
            bubble_content_layout.addWidget(name_label)
        
        if msg_type == 'text':
            display_text = cached_data if cached_data else "[Pesan Teks Super-Terenkripsi]"
            
            # --- [SOLUSI LAG]: Kembali ke QLabel, tapi matikan interaksi mouse ---
            content_label = QLabel(display_text)
            content_label.setWordWrap(True)
            content_label.setMaximumWidth(content_max_width)
            
            # Gunakan PlainText format agar ringan
            content_label.setTextFormat(Qt.TextFormat.PlainText)
            content_label.setStyleSheet(f"color: {self.COLOR_TEXT}; font-size: 14px;")
            
            # [CRITICAL OPTIMIZATION]
            # Mematikan TextSelectableByMouse menghilangkan lag saat scroll.
            # Sebagai gantinya, user bisa klik kanan -> Copy.
            content_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            content_label.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
            
            # Tambahkan Context Menu untuk Copy
            content_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            content_label.customContextMenuRequested.connect(lambda pos, lbl=content_label: self.show_copy_menu(pos, lbl))
            
            bubble_content_layout.addWidget(content_label)

        elif msg_type == 'stegano':
            filename = metadata.get('filename', 'unknown.png')
            if cached_data and isinstance(cached_data, dict):
                secret_text = cached_data.get('text', '[ERROR CACHE]')
                image_path = cached_data.get('image_path')
                
                if image_path and os.path.exists(image_path):
                    # Tampilkan gambar dengan smooth scaling
                    pixmap = QPixmap(image_path).scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    img_label = QLabel()
                    img_label.setPixmap(pixmap)
                    img_label.setMinimumSize(200, 150)
                    bubble_content_layout.addWidget(img_label)
                else:
                    stegano_label = QLabel(f"🖼️ Stegano: {filename}")
                    stegano_label.setWordWrap(True)
                    bubble_content_layout.addWidget(stegano_label)
                
                text_label = QLabel(f"Pesan: {secret_text}")
                text_label.setWordWrap(True)
                text_label.setStyleSheet(f"color: {self.COLOR_TEXT}; font-size: 14px; font-style: italic;")
                # Optimasi Lag
                text_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
                text_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                text_label.customContextMenuRequested.connect(lambda pos, lbl=text_label: self.show_copy_menu(pos, lbl))
                
                bubble_content_layout.addWidget(text_label)
            else:
                content_label = QLabel(f"🖼️ Stegano Image: {filename}")
                content_label.setWordWrap(True)
                content_label.setStyleSheet(f"color: {self.COLOR_TEXT_SUBTLE}; font-size: 14px; font-style: italic;")
                bubble_content_layout.addWidget(content_label)

        elif msg_type == 'file':
            filename = metadata.get('filename', 'unknown_file')
            method = metadata.get('encryption_method', 'aes').upper()
            content_label = QLabel(f"📂 File ({method}): {filename}")
            content_label.setWordWrap(True)
            content_label.setStyleSheet(f"color: {self.COLOR_TEXT_SUBTLE}; font-size: 14px; font-style: italic;")
            bubble_content_layout.addWidget(content_label)
        else:
            content_label = QLabel("[Pesan tidak dikenal]")
            content_label.setStyleSheet(f"color: {self.COLOR_RED}; font-size: 14px;")
            bubble_content_layout.addWidget(content_label)
        
        # --- Timestamp & Refresh ---
        bottom_layout = QHBoxLayout(); bottom_layout.setContentsMargins(0, 5, 0, 0)
        timestamp_str = "..."
        timestamp_iso = metadata.get('db_timestamp')
        if timestamp_iso:
            try:
                dt_obj = datetime.fromisoformat(timestamp_iso)
                if dt_obj.tzinfo is None:
                    dt_obj = dt_obj.replace(tzinfo=timezone.utc)
                dt_local = dt_obj.astimezone()
                timestamp_str = dt_local.strftime("%H:%M") 
            except ValueError: timestamp_str = "err"
        
        time_label = QLabel(timestamp_str)
        time_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        time_label.setStyleSheet(f"color: {self.COLOR_TEXT_SUBTLE}; font-size: 10px; padding-top: 5px;")
        
        refresh_btn = QPushButton("🔄") 
        refresh_btn.setFixedSize(25, 25)
        refresh_btn.setStyleSheet(f"QPushButton {{ background-color: transparent; border: none; color: {self.COLOR_TEXT_SUBTLE}; font-size: 14px; }} QPushButton:hover {{ color: {self.COLOR_GOLD_HOVER}; }}")
        
        if item: refresh_btn.clicked.connect(lambda: self.on_chat_item_clicked(item))
            
        bottom_layout.addWidget(time_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(refresh_btn)
        
        bubble_content_layout.addLayout(bottom_layout)
        
        if align == "sent":
            bubble_frame.setStyleSheet(f"QFrame {{ background-color: {self.COLOR_BUBBLE_SENT}; border-radius: 12px; border-bottom-right-radius: 0px; }}")
            container_layout.addStretch()
            container_layout.addWidget(bubble_frame)
        else: # received
            bubble_frame.setStyleSheet(f"QFrame {{ background-color: {self.COLOR_BUBBLE_RECV}; border-radius: 12px; border-bottom-left-radius: 0px; }}")
            container_layout.addWidget(bubble_frame)
            container_layout.addStretch()

        return bubble_container

    def show_copy_menu(self, pos, label_widget):
        menu = QMenu(self)
        copy_action = QAction("Copy Text", self)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(label_widget.text()))
        menu.addAction(copy_action)
        menu.exec(label_widget.mapToGlobal(pos))

    def add_message_to_display(self, align, metadata, cached_data=None, error_text=None, is_loading_history=False):
        
        item = QListWidgetItem() 
        item.setData(Qt.UserRole, metadata)
        
        if error_text:
            item.setText(error_text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor(self.COLOR_RED))
            item.setSizeHint(QSize(0, 30))
            self.chat_display.addItem(item)
        else:
            bubble_widget = self.create_chat_bubble(align, metadata, cached_data, item)
            
            # Setup layout awal
            bubble_widget.layout().activate() 
            bubble_widget.adjustSize()
            
            # Hitung size hint yang benar agar tidak overlap
            real_size = bubble_widget.sizeHint()
            real_size.setHeight(real_size.height() + 10) # Padding extra
            
            item.setSizeHint(real_size) 
            self.chat_display.addItem(item)
            self.chat_display.setItemWidget(item, bubble_widget)

    # --- Helper Styling ---
    def input_style(self):
        return f"""
            QLineEdit {{
                background-color: {self.COLOR_CARD};
                border: 2px solid {self.COLOR_GOLD};
                border-radius: 22px;
                padding: 10px 20px;
                color: {self.COLOR_TEXT};
                font-size: 14px;
                min-height: 25px; 
            }}
            QLineEdit:focus {{ border-color: {self.COLOR_GOLD_HOVER}; }}
        """

    def button_style(self, base, hover, pressed, radius=12, text_color=None):
        text_col = text_color if text_color else self.COLOR_TEXT
        return f"""
            QPushButton {{
                background-color: {base}; color: {text_col};
                border: none; border-radius: {radius}px;
                padding: 10px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:pressed {{ background-color: {pressed}; }}
        """