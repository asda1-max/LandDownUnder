from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox
)
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtCore import Qt

class LoginPage(QWidget):
    def __init__(self, switch_to_dashboard, switch_to_register, user_manager):
        super().__init__()
        self.switch_to_dashboard = switch_to_dashboard
        self.switch_to_register = switch_to_register
        self.user_manager = user_manager
        
        # --- PERUBAHAN ---
        # Diperlukan agar QWidget utama mau menerima warna background dari stylesheet
        self.setAutoFillBackground(True) 
        
        self.init_ui()
        self.apply_styles() # Panggil fungsi styling
        
    def init_ui(self):
        # (Fungsi ini SAMA PERSIS seperti sebelumnya, tidak ada logika yang diubah)
        self.resize(420, 320)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(35, 35, 35, 35)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Welcome Back 💙")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.returnPressed.connect(self.handle_login) 

        login_btn = QPushButton("Login")
        login_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        login_btn.clicked.connect(self.handle_login)
        login_btn.setObjectName("loginButton") 

        register_btn = QPushButton("Don't have an account? Register") 
        register_btn.setFont(QFont("Segoe UI", 10))
        register_btn.clicked.connect(self.switch_to_register)
        register_btn.setObjectName("registerButton") 

        layout.addWidget(title)
        layout.addWidget(self.user_input)
        layout.addWidget(self.pass_input)
        layout.addWidget(login_btn)
        layout.addWidget(register_btn)

    def apply_styles(self):
        """
        Menerapkan styling QSS (Qt Style Sheets) tema BIRU TUA.
        Ini HANYA mengubah tampilan (PySide6), BUKAN logika.
        """
        # Palet Warna (Biru Tua / Dark Blue)
        BG_DARK_BLUE = "#2C3E50"      # Background utama (Biru Sangat Tua)
        BG_MEDIUM_BLUE = "#34495E"    # Background input (Sedikit lebih terang)
        TEXT_LIGHT = "#ECF0F1"        # Teks utama (Putih pudar)
        BORDER_LIGHT = "#4A6572"      # Border input
        PRIMARY_BLUE = "#3498DB"      # Tombol login (Biru Cerah)
        PRIMARY_HOVER = "#2980B9"     # Hover tombol login
        PRIMARY_PRESSED = "#2471A3"   # Press tombol login
        SECONDARY_LINK = "#5DADE2"    # Tombol register (Link biru muda)
        SECONDARY_HOVER = "#85C1E9"   # Hover link
        
        # Menggunakan f-string untuk memasukkan variabel warna ke QSS
        self.setStyleSheet(f"""
            /* Gunakan nama class 'LoginPage' sebagai selector utama
               agar 'background-color' diterapkan
            */
            LoginPage {{
                background-color: {BG_DARK_BLUE};
            }}
            
            QLabel {{
                color: {TEXT_LIGHT};
                background-color: transparent; /* Pastikan label transparan */
            }}
            
            QLineEdit {{
                font-family: "Segoe UI";
                font-size: 11pt;
                padding: 10px;
                background-color: {BG_MEDIUM_BLUE};
                color: {TEXT_LIGHT};
                border: 1px solid {BORDER_LIGHT};
                border-radius: 5px;
            }}
            QLineEdit:focus {{
                border: 1px solid {SECONDARY_LINK}; /* Aksen biru muda saat di-klik */
            }}
            
            /* Style untuk tombol Login Utama */
            QPushButton#loginButton {{
                background-color: {PRIMARY_BLUE};
                color: white; /* Teks putih solid untuk kontras terbaik */
                padding: 10px;
                border: none;
                border-radius: 5px;
                min-height: 25px;
            }}
            QPushButton#loginButton:hover {{
                background-color: {PRIMARY_HOVER};
            }}
            QPushButton#loginButton:pressed {{
                background-color: {PRIMARY_PRESSED};
            }}
            
            /* Style untuk tombol Register (secondary) */
            QPushButton#registerButton {{
                background-color: transparent;
                color: {SECONDARY_LINK};
                font-size: 9pt;
                border: none;
                text-decoration: underline;
                padding: 5px;
            }}
            QPushButton#registerButton:hover {{
                color: {SECONDARY_HOVER};
            }}
        """)

    def handle_login(self):
        # --- LOGIKA INI TIDAK DIUBAH SAMA SEKALI ---
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