from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox
)
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtCore import Qt

class LoginPage(QWidget):
    
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

    def __init__(self, switch_to_dashboard, switch_to_register, user_manager):
        super().__init__()
        self.switch_to_dashboard = switch_to_dashboard
        self.switch_to_register = switch_to_register
        self.user_manager = user_manager
        
        self.setAutoFillBackground(True) 
        
        self.init_ui()
        self.apply_styles() # Panggil fungsi styling baru
        
    def init_ui(self):
        # [REVISI] Ukuran disesuaikan untuk padding baru
        self.resize(480, 400) 
        layout = QVBoxLayout(self)
        layout.setSpacing(20) # Beri jarak lebih
        layout.setContentsMargins(40, 40, 40, 40) # Padding lebih besar
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Welcome Back 💙")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("titleLabel") # [BARU] ID untuk styling

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        self.user_input.setFixedHeight(45) # [BARU] Samakan tinggi

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.returnPressed.connect(self.handle_login) 
        self.pass_input.setFixedHeight(45) # [BARU] Samakan tinggi

        login_btn = QPushButton("Login")
        login_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        login_btn.clicked.connect(self.handle_login)
        login_btn.setObjectName("loginButton") 
        login_btn.setFixedHeight(45) # [BARU] Samakan tinggi

        register_btn = QPushButton("Don't have an account? Register") 
        register_btn.setFont(QFont("Segoe UI", 10))
        register_btn.clicked.connect(self.switch_to_register)
        register_btn.setObjectName("registerButton") 

        layout.addWidget(title)
        layout.addSpacing(15) # Spasi tambahan
        layout.addWidget(self.user_input)
        layout.addWidget(self.pass_input)
        layout.addSpacing(10) # Spasi tambahan
        layout.addWidget(login_btn)
        layout.addWidget(register_btn)

    def apply_styles(self):
        """
        [REVISI TOTAL]
        Menerapkan styling QSS tema Dashboard (Indigo + Emas).
        """
        self.setStyleSheet(f"""
            LoginPage {{
                background-color: {self.COLOR_BACKGROUND};
            }}
            
            QLabel {{
                color: {self.COLOR_TEXT};
                background-color: transparent;
            }}
            
            /* [BARU] Judul Emas */
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
                border-radius: 22px; /* Radius besar seperti dashboard */
            }}
            QLineEdit:focus {{
                border: 2px solid {self.COLOR_GOLD_HOVER};
            }}
            
            /* Style untuk tombol Login (Emas) */
            QPushButton#loginButton {{
                background-color: {self.COLOR_GOLD};
                color: {self.COLOR_PANE_LEFT}; /* Teks gelap agar kontras */
                padding: 10px;
                border: none;
                border-radius: 22px; /* Radius besar */
                font-weight: bold;
            }}
            QPushButton#loginButton:hover {{
                background-color: {self.COLOR_GOLD_HOVER};
            }}
            QPushButton#loginButton:pressed {{
                background-color: {self.COLOR_GOLD_PRESSED};
            }}
            
            /* Style untuk tombol Register (Link) */
            QPushButton#registerButton {{
                background-color: transparent;
                color: {self.COLOR_TEXT_SUBTLE};
                font-size: 9pt;
                border: none;
                text-decoration: underline;
                padding: 5px;
            }}
            QPushButton#registerButton:hover {{
                color: {self.COLOR_TEXT};
            }}
        """)

    def handle_login(self):
        # --- LOGIKA TIDAK DIUBAH ---
        username = self.user_input.text()
        password = self.pass_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Login Failed", "Username dan password tidak boleh kosong.")
            return
        
        if self.user_manager.verify_user(username, password):
            self.user_input.clear()
            self.pass_input.clear()
            self.switch_to_dashboard(username)
        else:
            QMessageBox.warning(self, "Login Failed", "Username atau password salah.")
            self.pass_input.clear()
