import sys
import threading
import tkinter as tk
from tkinter import messagebox
from PySide6.QtWidgets import QApplication, QStackedWidget, QMessageBox
from PySide6.QtGui import QPalette, QColor

# ====== Import Halaman (UI Pages) ======
from loginpage import LoginPage
from registerpage import RegisterPage
from dashboard import DashboardPage
from chat import ChatPage
from groupchat import GroupChatPage # [BARU] Import GroupChat

# ====== Import Logika (Utils) ======
from utils import UserManager, MessageManager

# ====== Import Autentikasi USB ======
from usb_auth import get_all_valid_keys, check_usb_key, monitor_usb_drive, LOCAL_CONFIG_FILE

class MainWindow(QStackedWidget):
    def __init__(self):
        super().__init__()

        # Manajer akun dan pesan
        self.user_manager = UserManager()
        self.message_manager = MessageManager()
        self.current_user = None

        # Halaman-halaman utama
        self.login_page = LoginPage(self.show_dashboard, self.show_register, self.user_manager)
        self.register_page = RegisterPage(self.show_login, self.user_manager)
        
        # [UPDATE] Menambahkan callback show_group_chat ke Dashboard
        self.dashboard_page = DashboardPage(
            logout_callback=self.show_login, 
            switch_to_chat=self.show_chat, 
            switch_to_group=self.show_group_chat,
            user_manager=self.user_manager
        )
        self.chat_page = None
        self.group_chat_page = None # [BARU] Variabel untuk halaman grup

        # Tambahkan ke QStackedWidget
        self.addWidget(self.login_page)
        self.addWidget(self.register_page)
        self.addWidget(self.dashboard_page)

        self.setWindowTitle("Land Down Under !!!!")
        self.show_login()

    # ==== Navigasi Antar Halaman ====
    def show_login(self):
        self.current_user = None
        self.setCurrentWidget(self.login_page)
        self.setFixedSize(1200, 800)

    def show_register(self):
        self.setCurrentWidget(self.register_page)
        self.setFixedSize(1200, 800)

    def show_dashboard(self, username=""):
        if username:
            self.current_user = username

        if not self.current_user:
            self.show_login()
            return

        self.dashboard_page.set_welcome_message(self.current_user)
        self.setCurrentWidget(self.dashboard_page)
        self.setFixedSize(1200, 800)

    def show_chat(self, recipient_username, shared_password):
        if not self.current_user:
            QMessageBox.critical(self, "Error", "Tidak ada user yang login.")
            self.show_login()
            return

        if self.current_user == recipient_username:
            QMessageBox.warning(self, "Error", "Anda tidak bisa chat dengan diri sendiri.")
            return

        if self.chat_page:
            self.removeWidget(self.chat_page)
            self.chat_page.deleteLater()

        self.chat_page = ChatPage(
            current_user=self.current_user,
            recipient_username=recipient_username,
            shared_password=shared_password,
            message_manager=self.message_manager,
            back_callback=self.show_dashboard
        )

        self.addWidget(self.chat_page)
        self.setCurrentWidget(self.chat_page)
        self.setFixedSize(1200, 800)

    # [BARU] Fungsi Navigasi ke Group Chat
    def show_group_chat(self, group_name, shared_password):
        if not self.current_user:
            self.show_login(); return

        if self.group_chat_page:
            self.removeWidget(self.group_chat_page)
            self.group_chat_page.deleteLater()

        self.group_chat_page = GroupChatPage(
            current_user=self.current_user,
            group_name=group_name,
            shared_password=shared_password,
            message_manager=self.message_manager,
            back_callback=self.show_dashboard
        )
        
        self.addWidget(self.group_chat_page)
        self.setCurrentWidget(self.group_chat_page)
        self.setFixedSize(1200, 800)


if __name__ == "__main__":
    root_usb = tk.Tk()
    root_usb.withdraw()

    valid_keys = get_all_valid_keys()

    if not valid_keys: 
        messagebox.showerror(
            "Setup Error",
            f"File '{LOCAL_CONFIG_FILE}' tidak ditemukan atau tidak ada USB yang terdaftar.\n"
            "Jalankan setup_usb.py terlebih dahulu untuk mendaftarkan USB key."
        )
        sys.exit()

    while True:
        if check_usb_key(valid_keys):
            print("✅ USB Authentication successful.")
            break
        else:
            should_retry = messagebox.askretrycancel(
                "USB Key Not Found",
                "Masukkan SALAH SATU USB key yang terdaftar lalu klik Retry."
            )
            if not should_retry:
                print("❌ Dibatalkan oleh pengguna.")
                sys.exit()

    root_usb.destroy()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#0f172a"))
    palette.setColor(QPalette.WindowText, QColor("#e0e7ff"))
    palette.setColor(QPalette.Base, QColor("#1e3a8a"))
    palette.setColor(QPalette.AlternateBase, QColor("#1e3a8a"))
    palette.setColor(QPalette.ToolTipBase, QColor("#0f172a"))
    palette.setColor(QPalette.ToolTipText, QColor("#e0e7ff"))
    palette.setColor(QPalette.Text, QColor("#e0e7ff"))
    palette.setColor(QPalette.Button, QColor("#1e3a8a"))
    palette.setColor(QPalette.ButtonText, QColor("#e0e7ff"))
    palette.setColor(QPalette.Highlight, QColor("#4338ca"))
    palette.setColor(QPalette.HighlightedText, QColor("white"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()

    monitor_thread = threading.Thread(
        target=monitor_usb_drive,
        args=(app, valid_keys), 
        daemon=True
    )
    monitor_thread.start()

    sys.exit(app.exec())