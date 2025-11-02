import os
import base64
import requests  # <-- [BARU] Diperlukan untuk upload/download
import uuid      # <-- [BARU]
from stegano import lsb
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox,
    QListWidget, QListWidgetItem, QFileDialog,
    QInputDialog
)
from PySide6.QtGui import QFont, QColor, QPixmap
from PySide6.QtCore import Qt

# Impor fungsi kripto dari utils.py
from utils import CryptoEngine, vigenere_encrypt, vigenere_decrypt

class ChatPage(QWidget):
    def __init__(self, current_user, recipient_username, shared_password, message_manager, back_callback):
        super().__init__()
        self.current_user = current_user
        self.recipient_username = recipient_username
        self.message_manager = message_manager
        self.back_callback = back_callback
        
        self.chat_id = self.message_manager.get_chat_id(self.current_user, self.recipient_username)
        self.session_crypto = CryptoEngine(shared_password)
        
        # [BARU] URL API untuk upload/download
        self.api_url = "https://morsz.azeroth.site/"
        
        self.init_ui()
        self.load_and_display_chat_history()

    def init_ui(self):
        # ... (Fungsi init_ui tidak ada perubahan) ...
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

        self.attach_file_btn = QPushButton("📁 File"); self.attach_file_btn.setToolTip("Enkripsi file apa saja dengan Kunci AES per-pesan")
        self.attach_file_btn.setFont(QFont("Segoe UI", 12)); self.attach_file_btn.setStyleSheet(self.button_style("#4338ca", "#6366f1", "#312e81"))
        self.attach_file_btn.setFixedSize(70, 45)
        self.attach_file_btn.clicked.connect(self.handle_attach_file_aes)

        self.message_input = QLineEdit(); self.message_input.setPlaceholderText("Ketik pesan...")
        self.message_input.setStyleSheet(self.input_style())
        self.message_input.returnPressed.connect(self.handle_send_message_super)

        self.send_btn = QPushButton("Send Txt"); self.send_btn.setToolTip("Kirim teks dengan Super Enkripsi (Kunci Vigenere per-pesan + Kunci Sesi AES)")
        self.send_btn.setFont(QFont("Segoe UI", 11, QFont.Bold)); self.send_btn.setStyleSheet(self.button_style("#6d28d9", "#818cf8", "#4c1d95"))
        self.send_btn.setFixedSize(100, 45)
        self.send_btn.clicked.connect(self.handle_send_message_super)

        input_bar_layout.addWidget(self.attach_btn); input_bar_layout.addWidget(self.attach_file_btn)
        input_bar_layout.addWidget(self.message_input); input_bar_layout.addWidget(self.send_btn)
        layout.addLayout(top_bar_layout); layout.addWidget(self.chat_display); layout.addLayout(input_bar_layout)


    def load_and_display_chat_history(self):
        # ... (Fungsi ini tidak berubah) ...
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
                display_text = f"{prefix}: [Pesan Teks Terenkripsi]"
            elif msg_type == 'stegano':
                filename = os.path.basename(msg_data.get('filename', 'unknown.png'))
                display_text = f"{prefix}: [Gambar Stegano: {filename}]"
            elif msg_type == 'file':
                filename = msg_data.get('filename', 'unknown_file')
                display_text = f"{prefix}: [File Terenkripsi: {filename}]"
            else:
                display_text = f"{prefix}: [Pesan tidak dikenal]"

            self.add_message_to_display(display_text, align, msg_data)

    def handle_send_message_super(self):
        # ... (Fungsi ini tidak berubah, karena tidak menangani file) ...
        message_text = self.message_input.text()
        if not message_text: return

        vigenere_key, ok = QInputDialog.getText(self, "Kunci Super Enkripsi", "Masukkan Kunci VIGENERE (klasik) untuk pesan ini:")
        if not (ok and vigenere_key): return 

        self.message_input.clear()
        try:
            classic_encrypted = vigenere_encrypt(message_text, vigenere_key)
            data_bytes = classic_encrypted.encode('utf-8')
            encrypted_payload = self.session_crypto.encrypt(data_bytes)
            
            metadata = {
                'type': 'text',
                'sender': self.current_user,
                'recipient': self.recipient_username,
                'data': encrypted_payload.decode('utf-8'),
                'vigenere_key_debug': vigenere_key
            }
            
            self.message_manager.save_message(self.chat_id, metadata)
            self.add_message_to_display(f"You: {message_text}", "sent", metadata)
            
        except Exception as e:
            self.add_message_to_display(f"--- Error Super Enkripsi: {e} ---", "error")

    # [INSTRUKSI 3: DIUBAH TOTAL]
    def handle_attach_image_stegano(self):
        message_to_hide = self.message_input.text()
        if not message_to_hide:
            QMessageBox.warning(self, "Error", "Tulis dulu pesan di kotak teks untuk disembunyikan ke gambar.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih Gambar Pembawa (.png)", "", "Images (*.png)")
        if not file_path: return

        text_key, ok = QInputDialog.getText(self, "Kunci Steganografi", "Masukkan Kunci VIGENERE untuk teks yang akan disembunyikan:")
        if not (ok and text_key): return

        if not os.path.exists("temp_stegano"): os.makedirs("temp_stegano")
        base_filename = os.path.basename(file_path)
        output_filename = os.path.join("temp_stegano", f"stego_{base_filename}")

        try:
            # 1. Buat gambar steganografi secara lokal
            encrypted_text_to_hide = vigenere_encrypt(message_to_hide, text_key)
            secret_image = lsb.hide(file_path, encrypted_text_to_hide)
            secret_image.save(output_filename)

            # 2. [BARU] Unggah gambar stego ke API
            self.add_message_to_display(f"--- Mengunggah {base_filename}... ---", "error")
            with open(output_filename, "rb") as f:
                files = {'file': (base_filename, f, 'image/png')}
                upload_url = f"{self.api_url}/upload_file/{self.chat_id}"
                response = requests.post(upload_url, files=files, timeout=30)
            
            if response.status_code != 200 or not response.json().get("success"):
                raise Exception(f"Gagal mengunggah file: {response.json().get('message')}")

            file_id = response.json().get("file_id")

            # 3. [BARU] Kirim metadata (TANPA data gambar)
            metadata = {
                'type': 'stegano',
                'sender': self.current_user,
                'recipient': self.recipient_username,
                'data': None,  # Data tidak lagi dikirim di JSON
                'file_id': file_id, # Kirim file_id sebagai gantinya
                'filename': base_filename, 
                'text_key_debug': text_key
            }
            
            self.message_manager.save_message(self.chat_id, metadata)
            self.add_message_to_display(f"You: [Sent Stegano Image: {base_filename}]", "sent", metadata)
            self.message_input.clear()
            os.remove(output_filename) # Hapus file stego lokal

        except Exception as e:
            self.add_message_to_display(f"--- Error Steganografi/Upload: {e} ---", "error")

    # [INSTRUKSI 3: DIUBAH TOTAL]
    def handle_attach_file_aes(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih File Untuk Dienkripsi (AES)", "", "All Files (*.*)")
        if not file_path: return

        aes_key, ok = QInputDialog.getText(self, "Kunci Enkripsi File", "Masukkan Kunci AES (modern) untuk file ini:", QLineEdit.Password)
        if not (ok and aes_key): return

        try:
            # 1. Enkripsi file secara lokal
            with open(file_path, "rb") as f: data_bytes = f.read()
            temp_crypto = CryptoEngine(aes_key)
            encrypted_payload_bytes = temp_crypto.encrypt(data_bytes)
            
            filename = os.path.basename(file_path)

            # 2. [BARU] Unggah file terenkripsi ke API
            self.add_message_to_display(f"--- Mengunggah {filename}... ---", "error")
            # Kirim sebagai file 'application/octet-stream'
            files = {'file': (f"{filename}.enc", encrypted_payload_bytes, 'application/octet-stream')}
            upload_url = f"{self.api_url}/upload_file/{self.chat_id}"
            response = requests.post(upload_url, files=files, timeout=60) # Timeout lebih lama
            
            if response.status_code != 200 or not response.json().get("success"):
                raise Exception(f"Gagal mengunggah file: {response.json().get('message')}")
                
            file_id = response.json().get("file_id")

            # 3. [BARU] Kirim metadata (TANPA data file)
            metadata = {
                'type': 'file',
                'sender': self.current_user,
                'recipient': self.recipient_username,
                'data': None, # Data tidak lagi dikirim di JSON
                'file_id': file_id, # Kirim file_id sebagai gantinya
                'aes_key_debug': aes_key,
                'filename': filename
            }

            self.message_manager.save_message(self.chat_id, metadata)
            self.add_message_to_display(f"You: [Sent Encrypted File: {filename}]", "sent", metadata)
            
        except Exception as e:
            self.add_message_to_display(f"--- Error File Encryption/Upload: {e} ---", "error")

    # [INSTRUKSI 3: DIUBAH TOTAL]
    def on_chat_item_clicked(self, item):
        metadata = item.data(Qt.UserRole)
        
        if not metadata or metadata['sender'] == self.current_user:
            return
            
        msg_box = QMessageBox(self)
        msg_type = metadata.get('type')
        
        # [BARU] Cek apakah ini pesan file/stegano
        file_id = metadata.get('file_id')
        
        try:
            if msg_type == 'text':
                # --- Alur Teks (Tidak Berubah) ---
                encrypted_data_b64 = metadata['data'].encode('utf-8')
                key, ok = QInputDialog.getText(self, "Dekripsi Teks", "Masukkan Kunci VIGENERE untuk pesan ini:")
                if ok and key:
                    decrypted_bytes = self.session_crypto.decrypt(encrypted_data_b64)
                    classic_encrypted_text = decrypted_bytes.decode('utf-8')
                    decrypted_text = vigenere_decrypt(classic_encrypted_text, key)
                    
                    msg_box.setWindowTitle("Pesan Teks Didekripsi")
                    msg_box.setText(f"Pesan Asli:\n\n{decrypted_text}")
                    msg_box.setInformativeText(f"(Debug: Kunci yg benar '{metadata['vigenere_key_debug']}')")
                    msg_box.exec()

            elif msg_type == 'file' and file_id:
                # --- [ALUR BARU] File Terenkripsi ---
                key, ok = QInputDialog.getText(self, "Dekripsi File", "Masukkan Kunci AES untuk file ini:", QLineEdit.Password)
                if ok and key:
                    
                    # 1. [BARU] Download file terenkripsi dari API
                    self.add_message_to_display(f"--- Mengunduh {metadata['filename']}... ---", "error")
                    download_url = f"{self.api_url}/download_file/{self.chat_id}/{file_id}"
                    response = requests.get(download_url, timeout=60)
                    if response.status_code != 200:
                        raise Exception("Gagal mengunduh file dari server.")
                    encrypted_bytes = response.content
                    self.add_message_to_display(f"--- Unduhan Selesai. Mendekripsi... ---", "error")
                    
                    # 2. Dekripsi file yang diunduh
                    temp_crypto = CryptoEngine(key)
                    decrypted_bytes = temp_crypto.decrypt(encrypted_bytes)
                    
                    # 3. Simpan file hasil dekripsi
                    if not os.path.exists("temp_decrypted"): os.makedirs("temp_decrypted")
                    filename = metadata['filename']
                    decrypted_path = os.path.join("temp_decrypted", f"DECRYPTED_{filename}")
                    with open(decrypted_path, "wb") as f:
                        f.write(decrypted_bytes)
                        
                    msg_box.setWindowTitle("File Didekripsi")
                    msg_box.setText(f"File '{filename}' berhasil didekripsi!")
                    msg_box.setInformativeText(f"Disimpan di folder 'temp_decrypted'.\n(Debug: Kunci yg benar '{metadata['aes_key_debug']}')")
                    msg_box.exec()

            elif msg_type == 'stegano' and file_id:
                # --- [ALUR BARU] Gambar Steganografi ---
                
                # 1. [BARU] Download gambar dari API
                self.add_message_to_display(f"--- Mengunduh gambar {metadata['filename']}... ---", "error")
                download_url = f"{self.api_url}/download_file/{self.chat_id}/{file_id}"
                response = requests.get(download_url, timeout=60)
                if response.status_code != 200:
                    raise Exception("Gagal mengunduh gambar dari server.")
                image_bytes = response.content
                
                # 2. Simpan gambar yang diunduh ke folder temp
                if not os.path.exists("temp_stegano"): os.makedirs("temp_stegano")
                filename = metadata.get('filename', f"received_{metadata['sender']}.png")
                image_path = os.path.join("temp_stegano", filename)
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
                self.add_message_to_display(f"--- Gambar diterima. ---", "error")
                
                # 3. Alur selanjutnya (menampilkan gambar, dekripsi) sama seperti sebelumnya
                msg_box.setWindowTitle("Pesan Gambar Diterima")
                pixmap = QPixmap(image_path).scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                msg_box.setIconPixmap(pixmap)
                
                msg_box.setText("Gambar diterima. Ingin mendekripsi teks tersembunyi di dalamnya?")
                decrypt_button = msg_box.addButton("Dekripsi Teks Tersembunyi", QMessageBox.AcceptRole)
                msg_box.addButton(QMessageBox.Close)
                msg_box.exec()
                
                if msg_box.clickedButton() == decrypt_button:
                    key, ok = QInputDialog.getText(self, "Dekripsi Steganografi", "Masukkan Kunci VIGENERE untuk teks tersembunyi:")
                    if ok and key:
                        revealed_encrypted_text = lsb.reveal(image_path) # Ini akan bekerja sekarang
                        if not revealed_encrypted_text:
                            QMessageBox.warning(self, "Gagal", "Tidak ada pesan tersembunyi yang ditemukan di gambar ini.")
                            return
                            
                        decrypted_message = vigenere_decrypt(revealed_encrypted_text, key)
                        
                        QMessageBox.information(self, "Teks Terungkap", 
                            f"Pesan tersembunyi adalah:\n\n{decrypted_message}\n\n"
                            f"(Debug: Kunci yg benar '{metadata['text_key_debug']}')")

        except ValueError as e:
             QMessageBox.warning(self, "Dekripsi Gagal", f"Tidak dapat mendekripsi: {e}")
        except Exception as e:
             QMessageBox.critical(self, "Error", f"Terjadi error: {e}")

    def add_message_to_display(self, text, message_type, metadata=None):
        # ... (Fungsi ini tidak berubah) ...
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

    def input_style(self): return "QLineEdit { background-color: #1e3a8a; border: 2px solid #6d28d9; border-radius: 8px; padding: 12px 10px; color: white; font-size: 14px; min-height: 25px; } QLineEdit:focus { border: 2px solid #818cf8; }"
    def button_style(self, base, hover, pressed): return f"QPushButton {{ background-color: {base}; color: white; border: none; border-radius: 8px; padding: 10px; font-weight: bold; }} QPushButton:hover {{ background-color: {hover}; }} QPushButton:pressed {{ background-color: {pressed}; }}"