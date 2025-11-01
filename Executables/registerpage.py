from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox
)
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtCore import Qt

class RegisterPage(QWidget):
    def __init__(self, switch_to_login, user_manager):
        super().__init__()
        self.switch_to_login = switch_to_login
        self.user_manager = user_manager
        
        # Diperlukan agar QWidget mau menerima warna background
        self.setAutoFillBackground(True) 
        
        self.init_ui()
        self.apply_styles() # Menerapkan style
        
    def init_ui(self):
        # Layout dasar
        self.resize(480, 420) # Sedikit lebih tinggi untuk field tambahan
        layout = QVBoxLayout(self)
        
        # --- Perubahan PySide6 (Layout) ---
        layout.setSpacing(15) # Diubah agar ada jarak
        layout.setContentsMargins(35, 35, 35, 35) # Ditambah padding
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Judul
        title = QLabel("Create New Account 💜")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter) # Ditambah rata tengah

        # Input username
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")

        # Input password
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)

        # Konfirmasi password
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm Password")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        
        # --- Tambahan UX: Tekan Enter di field terakhir untuk register ---
        self.confirm_input.returnPressed.connect(self.handle_register)

        # Tombol buat akun
        create_btn = QPushButton("Create Account")
        create_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        create_btn.clicked.connect(self.handle_register)
        create_btn.setObjectName("createButton") # ID untuk stylesheet

        # Tombol kembali
        back_btn = QPushButton("Back to Login")
        back_btn.setFont(QFont("Segoe UI", 10))
        back_btn.clicked.connect(self.switch_to_login)
        back_btn.setObjectName("backButton") # ID untuk stylesheet

        # Tambahkan ke layout (Urutan sama persis)
        layout.addWidget(title)
        layout.addWidget(self.user_input)
        layout.addWidget(self.pass_input)
        layout.addWidget(self.confirm_input)
        layout.addWidget(create_btn)
        layout.addWidget(back_btn)

    def apply_styles(self):
        """
        Menerapkan styling QSS (Qt Style Sheets) tema BIRU TUA.
        (Tema ini SAMA PERSIS dengan LoginPage sebelumnya)
        """
        # Palet Warna (Biru Tua / Dark Blue)
        BG_DARK_BLUE = "#2C3E50"
        BG_MEDIUM_BLUE = "#34495E"
        TEXT_LIGHT = "#ECF0F1"
        BORDER_LIGHT = "#4A6572"
        PRIMARY_BLUE = "#3498DB"      # Tombol utama (Create)
        PRIMARY_HOVER = "#2980B9"
        PRIMARY_PRESSED = "#2471A3"
        SECONDARY_LINK = "#5DADE2"    # Tombol sekunder (Back)
        SECONDARY_HOVER = "#85C1E9"
        
        self.setStyleSheet(f"""
            RegisterPage {{
                background-color: {BG_DARK_BLUE};
            }}
            
            QLabel {{
                color: {TEXT_LIGHT};
                background-color: transparent;
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
                border: 1px solid {SECONDARY_LINK};
            }}
            
            /* Style untuk tombol Create Account (Primary) */
            QPushButton#createButton {{
                background-color: {PRIMARY_BLUE};
                color: white;
                padding: 10px;
                border: none;
                border-radius: 5px;
                min-height: 25px;
            }}
            QPushButton#createButton:hover {{
                background-color: {PRIMARY_HOVER};
            }}
            QPushButton#createButton:pressed {{
                background-color: {PRIMARY_PRESSED};
            }}
            
            /* Style untuk tombol Back to Login (Secondary) */
            QPushButton#backButton {{
                background-color: transparent;
                color: {SECONDARY_LINK};
                font-size: 9pt;
                border: none;
                text-decoration: underline;
                padding: 5px;
            }}
            QPushButton#backButton:hover {{
                color: {SECONDARY_HOVER};
            }}
        """)

    def handle_register(self):
        # --- LOGIKA BACKEND INI TIDAK DIUBAH SAMA SEKALI ---
        user = self.user_input.text()
        p1 = self.pass_input.text()
        p2 = self.confirm_input.text()
        
        # --- Tambahan kecil (logika frontend) untuk UX ---
        if not user or not p1 or not p2:
            QMessageBox.warning(self, "Error", "Semua field harus diisi.")
            return
        
        if p1 != p2: 
            QMessageBox.warning(self, "Error", "Password tidak sama.")
            # Bersihkan field password untuk input ulang
            self.pass_input.clear()
            self.confirm_input.clear()
            return

        # --- Panggilan ke backend (SAMA PERSIS) ---
        success, message = self.user_manager.register_user(user, p1)
        
        if success:
            QMessageBox.information(self, "Success", f"{message} 💙")
            # Bersihkan semua field sebelum pindah
            self.user_input.clear()
            self.pass_input.clear()
            self.confirm_input.clear()
            self.switch_to_login()
        else:
            QMessageBox.warning(self, "Error", message)
            # Hanya bersihkan password jika error (misal: username sudah ada)
            self.pass_input.clear()
            self.confirm_input.clear()