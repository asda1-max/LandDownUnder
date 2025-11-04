from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox
)
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtCore import Qt

class RegisterPage(QWidget):

    # --- [BARU] Palet Warna dari Dashboard ---
    COLOR_BACKGROUND = "#1A1B2E"
    COLOR_PANE_LEFT = "#272540" # Dipakai untuk text color di tombol gold
    COLOR_CARD_BG = "#272540"
    COLOR_CARD = "#3E3C6E"     # Background input
    COLOR_TEXT = "#F0F0F5"
    COLOR_TEXT_SUBTLE = "#A9A8C0"
    COLOR_GOLD = "#D4AF37"
    COLOR_GOLD_HOVER = "#F0C44F"
    COLOR_GOLD_PRESSED = "#B8860B"
    # -----------------------------------------------

    def __init__(self, switch_to_login, user_manager):
        super().__init__()
        self.switch_to_login = switch_to_login
        self.user_manager = user_manager
        
        self.setAutoFillBackground(True) 
        
        self.init_ui()
        self.apply_styles() # Menerapkan style baru
        
    def init_ui(self):
        # [REVISI] Ukuran disesuaikan
        self.resize(480, 480) 
        layout = QVBoxLayout(self)
        
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Create New Account 💜")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("titleLabel") # [BARU] ID untuk styling

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        self.user_input.setFixedHeight(45) # [BARU] Samakan tinggi

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setFixedHeight(45) # [BARU] Samakan tinggi

        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm Password")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.returnPressed.connect(self.handle_register)
        self.confirm_input.setFixedHeight(45) # [BARU] Samakan tinggi

        create_btn = QPushButton("Create Account")
        create_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        create_btn.clicked.connect(self.handle_register)
        create_btn.setObjectName("createButton") 
        create_btn.setFixedHeight(45) # [BARU] Samakan tinggi

        back_btn = QPushButton("Back to Login")
        back_btn.setFont(QFont("Segoe UI", 10))
        back_btn.clicked.connect(self.switch_to_login)
        back_btn.setObjectName("backButton") 

        layout.addWidget(title)
        layout.addSpacing(15)
        layout.addWidget(self.user_input)
        layout.addWidget(self.pass_input)
        layout.addWidget(self.confirm_input)
        layout.addSpacing(10)
        layout.addWidget(create_btn)
        layout.addWidget(back_btn)

    def apply_styles(self):
        """
        [REVISI TOTAL]
        Menerapkan styling QSS tema Dashboard (Indigo + Emas).
        """
        self.setStyleSheet(f"""
            RegisterPage {{
                background-color: {self.COLOR_BACKGROUND};
            }}
            
            QLabel {{
                color: {self.COLOR_TEXT};
                background-color: transparent;
            }}

            QLabel#titleLabel {{
                color: {self.COLOR_GOLD};
            }}
            
            QLineEdit {{
                font-family: "Segoe UI";
                font-size: 14px;
                padding: 10px 20px;
                background-color: {self.COLOR_CARD};
                color: {self.COLOR_TEXT};
                border: 2px solid {self.COLOR_GOLD};
                border-radius: 22px; /* Radius besar */
            }}
            QLineEdit:focus {{
                border: 2px solid {self.COLOR_GOLD_HOVER};
            }}
            
            /* Style untuk tombol Create Account (Emas) */
            QPushButton#createButton {{
                background-color: {self.COLOR_GOLD};
                color: {self.COLOR_PANE_LEFT}; /* Teks gelap */
                padding: 10px;
                border: none;
                border-radius: 22px; /* Radius besar */
                font-weight: bold;
            }}
            QPushButton#createButton:hover {{
                background-color: {self.COLOR_GOLD_HOVER};
            }}
            QPushButton#createButton:pressed {{
                background-color: {self.COLOR_GOLD_PRESSED};
            }}
            
            /* Style untuk tombol Back (Link) */
            QPushButton#backButton {{
                background-color: transparent;
                color: {self.COLOR_TEXT_SUBTLE};
                font-size: 9pt;
                border: none;
                text-decoration: underline;
                padding: 5px;
            }}
            QPushButton#backButton:hover {{
                color: {self.COLOR_TEXT};
            }}
        """)

    def handle_register(self):
        # --- LOGIKA TIDAK DIUBAH ---
        user = self.user_input.text()
        p1 = self.pass_input.text()
        p2 = self.confirm_input.text()
        
        if not user or not p1 or not p2:
            QMessageBox.warning(self, "Error", "Semua field harus diisi.")
            return
        
        if p1 != p2: 
            QMessageBox.warning(self, "Error", "Password tidak sama.")
            self.pass_input.clear()
            self.confirm_input.clear()
            return

        success, message = self.user_manager.register_user(user, p1)
        
        if success:
            QMessageBox.information(self, "Success", f"{message} 💙")
            self.user_input.clear()
            self.pass_input.clear()
            self.confirm_input.clear()
            self.switch_to_login()
        else:
            QMessageBox.warning(self, "Error", message)
            self.pass_input.clear()
            self.confirm_input.clear()
