import os
import json
import requests # Perlu requests untuk fetch group list
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame,
    QSpacerItem, QSizePolicy, QListWidget
)
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt, QSize, QTimer
from utils import get_resource_path

class DashboardPage(QWidget):
    
    # --- Palet Warna (Sama) ---
    COLOR_BACKGROUND = "#1A1B2E"
    COLOR_PANE_LEFT = "#272540"
    COLOR_PANE_RIGHT = "#1A1B2E"
    COLOR_CARD_BG = "#272540" 
    COLOR_CARD = "#3E3C6E"
    COLOR_TEXT = "#F0F0F5"
    COLOR_TEXT_SUBTLE = "#A9A8C0"
    COLOR_GOLD = "#D4AF37"
    COLOR_GOLD_HOVER = "#F0C44F"
    COLOR_GOLD_PRESSED = "#B8860B"
    COLOR_RED = "#ed4956"
    COLOR_RED_HOVER = "#ff7d6e"
    COLOR_RED_PRESSED = "#e63946"
    # -------------------

    def __init__(self, logout_callback, switch_to_chat, switch_to_group, user_manager):
        super().__init__()
        self.logout_callback = logout_callback
        self.switch_to_chat = switch_to_chat
        self.switch_to_group = switch_to_group 
        self.user_manager = user_manager
        self.current_user = None
        self.api_url = "https://morsz.azeroth.site/"
        
        self.init_ui()
        
        self.contact_poll_timer = QTimer(self)
        self.contact_poll_timer.setInterval(5000)
        self.contact_poll_timer.timeout.connect(self.load_data)

    def init_ui(self):
        self.resize(1200, 800)
        self.setStyleSheet(f"background-color: {self.COLOR_BACKGROUND};")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        left_pane = self.create_left_pane()
        right_pane = self.create_right_pane()
        
        main_layout.addWidget(left_pane)
        main_layout.addWidget(right_pane)
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 3)

    def create_left_pane(self):
        left_pane = QFrame()
        left_pane.setStyleSheet(f"background-color: {self.COLOR_PANE_LEFT}; border-right: 2px solid {self.COLOR_GOLD};")
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(20, 30, 20, 20); left_layout.setSpacing(15)

        title_card = QFrame(); title_card.setStyleSheet(self.card_style())
        title_layout = QVBoxLayout(title_card); title_layout.setContentsMargins(10, 15, 10, 15)
        title = QLabel("Obrolan")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {self.COLOR_GOLD}; background: transparent; border: none;")
        title.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title)
        
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Cari teman atau grup...")
        search_bar.setStyleSheet(self.input_style())
        search_bar.setFixedHeight(45)
        left_layout.addWidget(search_bar)

        self.contact_list = QListWidget()
        self.contact_list.setStyleSheet(self.list_style())
        self.contact_list.itemClicked.connect(self.on_item_clicked) 
        
        left_layout.addWidget(self.contact_list)
        return left_pane

    def create_right_pane(self):
        right_pane = QFrame()
        right_pane.setStyleSheet(f"background-color: {self.COLOR_PANE_RIGHT};")
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(50, 40, 50, 50); right_layout.setSpacing(25)

        header_card = QFrame(); header_card.setStyleSheet(self.card_style())
        header_card_layout = QVBoxLayout(header_card); header_card_layout.setContentsMargins(25, 25, 25, 25)
        header_layout = self.create_header()
        header_card_layout.addLayout(header_layout)

        new_chat_card = QFrame(); new_chat_card.setStyleSheet(self.card_style())
        new_chat_layout_internal = QVBoxLayout(new_chat_card)
        new_chat_layout_internal.setContentsMargins(30, 30, 30, 30); new_chat_layout_internal.setSpacing(15)
        
        info = QLabel("Mulai Obrolan / Buat Grup")
        info.setFont(QFont("Segoe UI", 18, QFont.Bold))
        info.setStyleSheet(f"color: {self.COLOR_GOLD}; background: transparent; border: none;")
        
        info_sub = QLabel("Ketik username teman ATAU nama grup baru:")
        info_sub.setFont(QFont("Segoe UI", 11))
        info_sub.setStyleSheet(f"color: {self.COLOR_TEXT_SUBTLE}; background: transparent; border: none;")

        ctrl_layout = QHBoxLayout(); ctrl_layout.setSpacing(10)
        self.recipient_input = QLineEdit(); self.recipient_input.setPlaceholderText("Username / Nama Grup...")
        self.recipient_input.setStyleSheet(self.input_style()); self.recipient_input.setFixedHeight(45)

        self.start_chat_btn = QPushButton("Chat Personal")
        self.start_chat_btn.setFixedSize(120, 45)
        self.start_chat_btn.setStyleSheet(self.button_style(self.COLOR_GOLD, self.COLOR_GOLD_HOVER, self.COLOR_GOLD_PRESSED, 22, self.COLOR_PANE_LEFT))
        self.start_chat_btn.clicked.connect(self.handle_start_chat)
        
        # [MODIFIED] Tombol hanya untuk BUAT grup
        self.create_group_btn = QPushButton("Buat Grup Baru")
        self.create_group_btn.setFixedSize(140, 45)
        self.create_group_btn.setStyleSheet(self.button_style(self.COLOR_CARD, self.COLOR_GOLD_HOVER, self.COLOR_PANE_LEFT, 22, self.COLOR_TEXT))
        self.create_group_btn.clicked.connect(self.handle_create_group)

        ctrl_layout.addWidget(self.recipient_input)
        ctrl_layout.addWidget(self.start_chat_btn)
        ctrl_layout.addWidget(self.create_group_btn)
        
        new_chat_layout_internal.addWidget(info); new_chat_layout_internal.addWidget(info_sub); new_chat_layout_internal.addLayout(ctrl_layout)

        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setFixedSize(120, 40)
        self.logout_btn.setStyleSheet(self.button_style(self.COLOR_RED, self.COLOR_RED_HOVER, self.COLOR_RED_PRESSED, 10))
        self.logout_btn.clicked.connect(self.handle_logout)

        right_layout.addWidget(header_card)
        right_layout.addWidget(new_chat_card)
        right_layout.addStretch()
        right_layout.addWidget(self.logout_btn, 0, Qt.AlignmentFlag.AlignRight)
        return right_pane

    def create_header(self):
        header = QHBoxLayout(); header.setSpacing(15)
        profile_pic = QLabel(); profile_pic.setFixedSize(80, 80)
        pixmap = QPixmap(get_resource_path(os.path.join("assets", "profile.png")))
        if not pixmap.isNull():
             profile_pic.setPixmap(pixmap.scaled(74, 74, Qt.KeepAspectRatio, Qt.SmoothTransformation))
             profile_pic.setAlignment(Qt.AlignCenter)
        profile_pic.setStyleSheet(f"background-color: {self.COLOR_CARD}; border: 3px solid {self.COLOR_GOLD}; border-radius: 40px;")
        
        name_info = QVBoxLayout(); name_info.setSpacing(2)
        self.title_label = QLabel("Hi, ..."); self.title_label.setFont(QFont("Segoe UI", 28, QFont.Bold))
        self.title_label.setStyleSheet(f"color: {self.COLOR_TEXT}; background: transparent; border: none;")
        self.subtitle_label = QLabel("Selamat datang kembali."); self.subtitle_label.setFont(QFont("Segoe UI", 12))
        self.subtitle_label.setStyleSheet(f"color: {self.COLOR_TEXT_SUBTLE}; background: transparent; border: none;")
        
        name_info.addWidget(self.title_label); name_info.addWidget(self.subtitle_label); name_info.addStretch()
        header.addWidget(profile_pic); header.addLayout(name_info); header.addStretch()
        return header

    # --- Logika Data & Event (DIPERBAIKI) ---
    def set_welcome_message(self, username):
        self.title_label.setText(f"Hi, {username}!")
        self.current_user = username
        self.load_data()
        if not self.contact_poll_timer.isActive(): self.contact_poll_timer.start()

    def load_data(self):
        """
        Mengambil Data Grup dari SERVER (bukan file lokal).
        Jika kita di-invite, grup akan muncul otomatis di sini.
        """
        self.contact_list.clear()
        added_entries = set()
        has_data = False

        # 1. Fetch My Groups from API (Server Side Invitation Check)
        try:
            url = f"{self.api_url}/my_groups/{self.current_user}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                groups_data = resp.json().get('groups', [])
                for g in groups_data:
                    g_name = g['group_name']
                    display = f"Group : {g_name}"
                    self.contact_list.addItem(display)
                    added_entries.add(g_name)
                    has_data = True
        except Exception as e:
            print(f"Gagal load group: {e}")

        # 2. Load Kontak Personal
        success, contacts = self.user_manager.get_contacts(self.current_user)
        if success and contacts:
            for c in contacts:
                # Pastikan tidak menampilkan ID group sebagai user
                if not c.startswith("GROUP_") and c not in added_entries:
                    self.contact_list.addItem(c)
                    added_entries.add(c)
                    has_data = True
        
        if not has_data:
            self.contact_list.addItem("Belum ada obrolan...")

    def handle_logout(self):
        if self.contact_poll_timer.isActive(): self.contact_poll_timer.stop()
        self.logout_callback()

    def on_item_clicked(self, item):
        text = item.text()
        if text in ["Belum ada obrolan...", "Memuat kontak..."]: return
        if self.contact_poll_timer.isActive(): self.contact_poll_timer.stop()
        
        if text.startswith("Group : "):
            real_group_name = text.replace("Group : ", "").strip()
            shared_password = f"key_rahasia_group_{real_group_name}"
            self.switch_to_group(real_group_name, shared_password)
        else:
            recipient = text
            users = sorted([self.current_user, recipient])
            shared_password = f"key_rahasia_{users[0]}_{users[1]}"
            self.switch_to_chat(recipient, shared_password)

    def handle_start_chat(self):
        recipient = self.recipient_input.text().strip()
        if not recipient: return
        if recipient == self.current_user:
             QMessageBox.warning(self, "Error", "Tidak bisa chat diri sendiri."); return
        
        if self.contact_poll_timer.isActive(): self.contact_poll_timer.stop()
        
        users = sorted([self.current_user, recipient])
        pass_key = f"key_rahasia_{users[0]}_{users[1]}"
        self.switch_to_chat(recipient, pass_key)
        self.recipient_input.clear()

    # [BARU] Logika Buat Grup via API
    def handle_create_group(self):
        group_name = self.recipient_input.text().strip()
        if not group_name: 
            QMessageBox.warning(self, "Error", "Isi nama grup baru."); return
        
        try:
            payload = {"group_name": group_name, "creator": self.current_user}
            resp = requests.post(f"{self.api_url}/create_group", json=payload, timeout=10)
            
            if resp.status_code == 200:
                QMessageBox.information(self, "Sukses", f"Grup {group_name} dibuat!")
                # Refresh agar muncul di list
                self.load_data()
                
                # Masuk ke grup
                if self.contact_poll_timer.isActive(): self.contact_poll_timer.stop()
                shared_password = f"key_rahasia_group_{group_name}"
                self.switch_to_group(group_name, shared_password)
                self.recipient_input.clear()
            else:
                msg = resp.json().get("message", "Gagal membuat grup.")
                QMessageBox.warning(self, "Gagal", msg)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Koneksi error: {e}")

    # Styles
    def card_style(self):
        return f"QFrame {{ background-color: {self.COLOR_CARD_BG}; border: 2px solid {self.COLOR_GOLD}; border-radius: 16px; }}"
    def input_style(self):
        return f"QLineEdit {{ background-color: {self.COLOR_CARD}; border: 2px solid {self.COLOR_GOLD}; border-radius: 22px; padding: 10px 20px; color: {self.COLOR_TEXT}; font-size: 14px; }}"
    def list_style(self):
        return f"QListWidget {{ background: transparent; border: none; color: {self.COLOR_TEXT}; font-size: 16px; padding: 5px; }} QListWidget::item {{ padding: 15px 10px; border-radius: 8px; }} QListWidget::item:hover {{ background-color: {self.COLOR_CARD}; }} QListWidget::item:selected {{ background-color: {self.COLOR_GOLD}; color: {self.COLOR_PANE_LEFT}; font-weight: bold; }}"
    def button_style(self, base, hover, pressed, radius=12, text_color=None):
        tc = text_color if text_color else self.COLOR_TEXT
        return f"QPushButton {{ background-color: {base}; color: {tc}; border: none; border-radius: {radius}px; padding: 8px 16px; font-weight: bold; }} QPushButton:hover {{ background-color: {hover}; }} QPushButton:pressed {{ background-color: {pressed}; }}"