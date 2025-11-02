import os
import sys
from hashlib import pbkdf2_hmac
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64
import hashlib
import json
import requests  # <-- Sangat penting
import threading
from stegano import lsb
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

# --- FUNGSI HELPER PATH (.EXE) ---
# (Tetap 100% di KLIEN)
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

# --- FUNGSI HASH PASSWORD ---
# (SANGAT PENTING: Tetap 100% di KLIEN)
def hash_password(password):
    salt = os.urandom(16)
    hashed_password = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex(), hashed_password.hex()

def verify_password(stored_salt_hex, stored_hash_hex, password_to_check):
    try:
        stored_salt = bytes.fromhex(stored_salt_hex)
        stored_hash = bytes.fromhex(stored_hash_hex)
        check_hash = hashlib.pbkdf2_hmac('sha256', password_to_check.encode('utf-8'), stored_salt, 100000)
        return check_hash == stored_hash
    except (ValueError, TypeError):
        return False

# --- [ LOGIKA API KLIEN ] ---
API_BASE_URL = "https://morsz.azeroth.site/" # <-- Alamat HTTPS Anda

# --- MANAJEMEN USER (DIUBAH TOTAL) ---
class UserManager:
    def __init__(self):
        self.api_url = API_BASE_URL
        print("UserManager (API Mode) diinisialisasi.")

    def register_user(self, username, password):
        # 1. Enkripsi/hash password di LOKAL (AMAN)
        salt_hex, hash_hex = hash_password(password)
        
        # 2. Kirim HASH (bukan password) ke API
        payload = {
            "username": username,
            "salt_hex": salt_hex,
            "hash_hex": hash_hex
        }
        try:
            response = requests.post(f"{self.api_url}/register", json=payload, timeout=10)
            if response.status_code == 200:
                return True, response.json().get("message", "Akun berhasil dibuat!")
            else:
                return False, response.json().get("message", "Username sudah ada.")
        except requests.exceptions.RequestException as e:
            return False, f"Koneksi ke server gagal: {e}"

    def verify_user(self, username, password):
        # 1. Minta salt dan hash dari server
        try:
            response = requests.post(f"{self.api_url}/login", json={"username": username}, timeout=10)
            if response.status_code != 200:
                return False 

            data = response.json()
            stored_salt_hex = data['salt_hex']
            stored_hash_hex = data['hash_hex']

            # 2. Verifikasi password di LOKAL (AMAN)
            return verify_password(stored_salt_hex, stored_hash_hex, password)
        except requests.exceptions.RequestException as e:
            print(f"Verifikasi gagal: Tidak bisa terhubung ke server. {e}")
            return False
        except Exception as e:
            print(f"Error verifikasi: {e}")
            return False
            
    # --- [ INSTRUKSI 1: FUNGSI BARU AMBIL KONTAK ] ---
    def get_contacts(self, username):
        """Mengambil daftar kontak dari server untuk dashboard."""
        try:
            response = requests.get(f"{self.api_url}/get_chats/{username}", timeout=10)
            if response.status_code == 200 and response.json().get("success"):
                return True, response.json().get("contacts", [])
            else:
                print(f"Gagal mengambil kontak: {response.json().get('message')}")
                return False, []
        except requests.exceptions.RequestException as e:
            print(f"Koneksi error ambil kontak: {e}")
            return False, []

# --- MANAJEMEN PESAN (DIUBAH TOTAL) ---
class MessageManager:
    def __init__(self):
        self.api_url = API_BASE_URL
        print("MessageManager (API Mode) diinisialisasi.")

    def get_chat_id(self, user1, user2):
        users = sorted([user1, user2])
        return f"{users[0]}_{users[1]}"

    def load_messages(self, chat_id):
        try:
            response = requests.get(f"{self.api_url}/load_messages/{chat_id}", timeout=10)
            if response.status_code == 200:
                return response.json() 
            else:
                return []
        except requests.exceptions.RequestException:
            print("Gagal memuat pesan dari server.")
            return [] 

    def save_message(self, chat_id, message_data):
        message_data['chat_id'] = chat_id
        
        # [DIUBAH] Jangan kirim data file besar di JSON
        if message_data.get('type') in ['stegano', 'file']:
             message_data['data'] = None
        
        try:
            # Mengirim pesan dalam thread agar UI tidak 'freeze'
            def send_in_thread():
                try:
                    requests.post(f"{self.api_url}/save_message", json=message_data, timeout=10)
                    print("Pesan (metadata) berhasil dikirim ke server.")
                except requests.exceptions.RequestException as e:
                    print(f"Gagal mengirim pesan: {e}")
            
            threading.Thread(target=send_in_thread, daemon=True).start()
            
        except Exception as e:
            print(f"Error memulai thread kirim pesan: {e}")

# --- [ FUNGSI VIGENERE (DIPINDAH KE API) ] ---
# (Tidak berubah)
def vigenere_encrypt(plain_text, key):
    if not key: key = "defaultkey"
    payload = {"text": plain_text, "key": key}
    
    try:
        response = requests.post(f"{API_BASE_URL}/encrypt/vigenere", json=payload, timeout=5)
        if response.status_code == 200:
            return response.json().get("result", plain_text)
        else:
            print(f"Server error Vigenere Encrypt: {response.status_code}")
            return plain_text # Kembalikan teks asli jika gagal
    except requests.exceptions.RequestException as e:
        print(f"Koneksi error Vigenere Encrypt: {e}")
        return plain_text # Kembalikan teks asli jika gagal

def vigenere_decrypt(encrypted_text, key):
    if not key: key = "defaultkey"
    payload = {"text": encrypted_text, "key": key}
    
    try:
        response = requests.post(f"{API_BASE_URL}/decrypt/vigenere", json=payload, timeout=5)
        if response.status_code == 200:
            return response.json().get("result", encrypted_text)
        else:
            print(f"Server error Vigenere Decrypt: {response.status_code}")
            return encrypted_text # Kembalikan teks asli jika gagal
    except requests.exceptions.RequestException as e:
        print(f"Koneksi error Vigenere Decrypt: {e}")
        return encrypted_text # Kembalikan teks asli jika gagal

# --- CRYPTO ENGINE (Modern) ---
# (Tidak berubah)
class CryptoEngine:
    def __init__(self, password: str):
        self.password = password.encode('utf-8')
    def _derive_key(self, salt: bytes) -> bytes:
        kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1, backend=default_backend())
        return kdf.derive(self.password)
    def encrypt(self, data: bytes) -> bytes:
        salt = os.urandom(16); key = self._derive_key(salt)
        aesgcm = AESGCM(key); nonce = os.urandom(12)
        encrypted_data = aesgcm.encrypt(nonce, data, None)
        return base64.b64encode(salt + nonce + encrypted_data) 
    def decrypt(self, combined_payload_b64: bytes) -> bytes:
        try:
            combined_payload = base64.b64decode(combined_payload_b64)
            salt = combined_payload[:16]; nonce = combined_payload[16:28]
            encrypted_data = combined_payload[28:]
            key = self._derive_key(salt)
            aesgcm = AESGCM(key)
            return aesgcm.decrypt(nonce, encrypted_data, None)
        except Exception as e:
            print(f"CryptoEngine Gagal Dekripsi: {e}")
            raise ValueError("Gagal mendekripsi data: Password salah atau data korup.")

# --- KONFIGURASI KUNCI USB ---
# (Tidak berubah)
HARDCODED_SECRET = "ini-adalah-kunci-rahasia-saya-yang-sangat-panjang-12345"
SALT_SIZE = 16
KEY_SIZE = 32
ITERATIONS = 100000
HASH_ALG = "sha256"

def encrypt_config(plain_text_key, password):
    salt = get_random_bytes(SALT_SIZE)
    key = pbkdf2_hmac(HASH_ALG, password.encode("utf-8"), salt, ITERATIONS, KEY_SIZE)
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(plain_text_key.encode("utf-8"))
    encrypted_data = {
        "salt": salt.hex(), "nonce": cipher.nonce.hex(),
        "tag": tag.hex(), "ciphertext": ciphertext.hex(),
    }
    return json.dumps(encrypted_data).encode("utf-8")

def decrypt_config(encrypted_data_bytes, password):
    try:
        encrypted_data = json.loads(encrypted_data_bytes.decode("utf-8"))
        salt = bytes.fromhex(encrypted_data["salt"])
        nonce = bytes.fromhex(encrypted_data["nonce"])
        tag = bytes.fromhex(encrypted_data["tag"])
        ciphertext = bytes.fromhex(encrypted_data["ciphertext"])
        key = pbkdf2_hmac(HASH_ALG, password.encode("utf-8"), salt, ITERATIONS, KEY_SIZE)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        plain_text_bytes = cipher.decrypt_and_verify(ciphertext, tag)
        return plain_text_bytes.decode("utf-8")
    except Exception as e:
        print(f"Gagal dekripsi config: {e}")
        return None