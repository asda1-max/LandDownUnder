from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame,
    QSpacerItem, QSizePolicy
)
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt

class DashboardPage(QWidget):
    def __init__(self, logout_callback, switch_to_chat):
        super().__init__()
        self.logout_callback = logout_callback
        self.switch_to_chat = switch_to_chat
        self.init_ui()
        
    def init_ui(self):
        self.resize(1200, 800)
        self.setStyleSheet("QWidget { background-color: #0f172a; } QLabel { color: #e0e7ff; }")
        layout = QVBoxLayout(self); layout.setContentsMargins(80, 40, 80, 40); layout.setSpacing(30)
        header = QHBoxLayout(); profile_pic = QLabel()
        pixmap = QPixmap("assets/profile.png") 
        if pixmap.isNull(): profile_pic.setStyleSheet("border-radius: 40px; background-color: #334155;")
        else: profile_pic.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)); profile_pic.setStyleSheet("border-radius: 40px;")
        profile_pic.setFixedSize(80, 80); name_info = QVBoxLayout()
        
        self.title_label = QLabel("Welcome 💙"); self.title_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        subtitle = QLabel("Selamat datang di ruang kerja eleganmu 🌤️"); subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet("color: #94a3b8;")
        name_info.addWidget(self.title_label); name_info.addWidget(subtitle)
        
        header.addWidget(profile_pic); header.addLayout(name_info); header.addStretch()
        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet(self.button_style("#ed4956", "#ff7d6e", "#e63946", radius=10))
        logout_btn.setFixedWidth(120); logout_btn.clicked.connect(self.logout_callback)
        header.addWidget(logout_btn, alignment=Qt.AlignmentFlag.AlignRight)
        card = QFrame(); card.setStyleSheet("QFrame { background-color: #1e293b; border-radius: 20px; border: 1px solid #4c1d95; }")
        card_layout = QVBoxLayout(card); card_layout.setContentsMargins(40, 40, 40, 40); card_layout.setSpacing(20)
        info = QLabel("Mulai obrolan baru 💬"); info.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.recipient_input = QLineEdit(); self.recipient_input.setPlaceholderText("👤 Username tujuan")
        self.recipient_input.setStyleSheet(self.input_style())
        self.password_input = QLineEdit(); self.password_input.setPlaceholderText("🔐 Kunci Sandi SESI UTAMA (AES)")
        self.password_input.setEchoMode(QLineEdit.Password); self.password_input.setStyleSheet(self.input_style())
        self.start_chat_btn = QPushButton("Mulai Chat"); self.start_chat_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.start_chat_btn.setStyleSheet(self.button_style("#6d28d9", "#818cf8", "#4c1d95", radius=12))
        self.start_chat_btn.setFixedHeight(40); self.start_chat_btn.clicked.connect(self.handle_start_chat)
        card_layout.addWidget(info); card_layout.addWidget(self.recipient_input); card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.start_chat_btn); card_layout.addSpacerItem(QSpacerItem(10, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))
        layout.addLayout(header); layout.addWidget(card)
        
    def set_welcome_message(self, username):
        self.title_label.setText(f"{username} 💙")

    def input_style(self): return "QLineEdit { background-color: #1e3a8a; border: 2px solid #6d28d9; border-radius: 8px; padding: 8px 10px; color: white; font-size: 14px; } QLineEdit:focus { border: 2px solid #818cf8; }"
    def button_style(self, base, hover, pressed, radius=8): return f"QPushButton {{ background-color: {base}; color: white; border: none; border-radius: {radius}px; padding: 8px 16px; font-weight: bold; }} QPushButton:hover {{ background-color: {hover}; }} QPushButton:pressed {{ background-color: {pressed}; }}"
    
    def handle_start_chat(self):
        recipient = self.recipient_input.text(); password = self.password_input.text()
        if not recipient or not password: 
            QMessageBox.warning(self, "Error", "Isi username tujuan dan Kunci Sandi Sesi Utama.")
            return
        self.switch_to_chat(recipient, password)
        self.recipient_input.clear(); self.password_input.clear()