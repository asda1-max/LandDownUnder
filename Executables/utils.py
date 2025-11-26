import os
import sys
from hashlib import pbkdf2_hmac
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from config_manager import get_api_url, save_api_url # Pastikan config_manager ada
import base64
import hashlib
import json
import requests
import threading
from stegano import lsb
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

# --- Impor White-Mist ---
try:
    import crossCross
except ImportError:
    print("PERINGATAN: Modul WhiteMist tidak ditemukan. Fitur enkripsi White-Mist tidak akan berfungsi.")
    crossCross = None 

# --- FUNGSI HELPER PATH ---
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

# =========================================================================
# [LOGIKA API DINAMIS]
# Kita TIDAK mendefinisikan API_BASE_URL sebagai variabel global di sini.
# Kita memanggil get_api_url() di dalam setiap fungsi agar real-time.
# =========================================================================

# --- MANAJEMEN USER ---
class UserManager:
    def __init__(self):
        # Tidak menyimpan self.api_url di init agar tidak statis
        print("UserManager (API Mode - Dynamic) diinisialisasi.")

    def register_user(self, username, password):
        salt_hex, hash_hex = hash_password(password)
        payload = { "username": username, "salt_hex": salt_hex, "hash_hex": hash_hex }
        
        # [PENTING] Ambil URL terbaru saat tombol ditekan
        current_api_url = get_api_url()
        
        try:
            response = requests.post(f"{current_api_url}/register", json=payload, timeout=10)
            if response.status_code == 200:
                return True, response.json().get("message", "Akun berhasil dibuat!")
            else:
                return False, response.json().get("message", "Username sudah ada.")
        except requests.exceptions.RequestException as e:
            return False, f"Koneksi ke server gagal: {e}"

    def verify_user(self, username, password):
        try:
            # [PENTING] Ambil URL terbaru
            current_api_url = get_api_url()
            
            response = requests.post(f"{current_api_url}/login", json={"username": username}, timeout=10)
            if response.status_code != 200: return False 
            data = response.json()
            stored_salt_hex = data['salt_hex']
            stored_hash_hex = data['hash_hex']
            return verify_password(stored_salt_hex, stored_hash_hex, password)
        except requests.exceptions.RequestException as e:
            print(f"Verifikasi gagal: Tidak bisa terhubung ke server {current_api_url}. Error: {e}")
            return False
        except Exception as e:
            print(f"Error verifikasi: {e}")
            return False
            
    def get_contacts(self, username):
        try:
            # [PENTING] Ambil URL terbaru
            current_api_url = get_api_url()
            
            response = requests.get(f"{current_api_url}/get_chats/{username}", timeout=10)
            if response.status_code == 200 and response.json().get("success"):
                return True, response.json().get("contacts", [])
            else:
                print(f"Gagal mengambil kontak dari {current_api_url}: {response.json().get('message')}")
                return False, []
        except requests.exceptions.RequestException as e:
            # Error ini akan ditangkap oleh dashboard.py untuk memicu popup ganti URL
            print(f"Koneksi error ambil kontak: {e}")
            # Kita raise error agar Dashboard tahu koneksi putus
            raise e 

# --- MANAJEMEN PESAN ---
class MessageManager:
    def __init__(self):
        print("MessageManager (API Mode - Dynamic) diinisialisasi.")

    def get_chat_id(self, user1, user2):
        users = sorted([user1, user2])
        return f"{users[0]}_{users[1]}"

    def load_messages(self, chat_id):
        try:
            # [PENTING] Ambil URL terbaru
            current_api_url = get_api_url()
            
            response = requests.get(f"{current_api_url}/load_messages/{chat_id}", timeout=10)
            if response.status_code == 200:
                return response.json() 
            else:
                return []
        except requests.exceptions.RequestException:
            # Bisa di-raise jika ingin notif di chat page, tapi return [] cukup aman
            return [] 

    def save_message(self, chat_id, message_data):
        message_data_copy = message_data.copy()
        message_data_copy['chat_id'] = chat_id
        if message_data_copy.get('type') in ['stegano', 'file']:
             message_data_copy['data'] = None
        if 'db_timestamp' in message_data_copy:
            del message_data_copy['db_timestamp']
            
        try:
            # [PENTING] Ambil URL DI LUAR thread agar thread pakai URL yang valid saat ini
            current_api_url = get_api_url()
            
            def send_in_thread(target_url):
                try:
                    requests.post(f"{target_url}/save_message", json=message_data_copy, timeout=10)
                    print(f"Pesan berhasil dikirim ke {target_url}.")
                except requests.exceptions.RequestException as e:
                    print(f"Gagal mengirim pesan ke {target_url}: {e}")
            
            # Oper URL ke dalam thread
            threading.Thread(target=send_in_thread, args=(current_api_url,), daemon=True).start()
        except Exception as e:
            print(f"Error memulai thread kirim pesan: {e}")

# --- FUNGSI VIGENERE (HELPER) ---
def vigenere_encrypt(plain_text, key):
    if not key: key = "defaultkey"
    payload = {"text": plain_text, "key": key}
    try:
        # [PENTING] Ambil URL terbaru
        current_api_url = get_api_url()
        
        response = requests.post(f"{current_api_url}/encrypt/vigenere", json=payload, timeout=5)
        if response.status_code == 200:
            return response.json().get("result", plain_text)
        else:
            return plain_text 
    except requests.exceptions.RequestException:
        return plain_text 

def vigenere_decrypt(encrypted_text, key):
    if not key: key = "defaultkey"
    payload = {"text": encrypted_text, "key": key}
    try:
        # [PENTING] Ambil URL terbaru
        current_api_url = get_api_url()
        
        response = requests.post(f"{current_api_url}/decrypt/vigenere", json=payload, timeout=5)
        if response.status_code == 200:
            return response.json().get("result", encrypted_text)
        else:
            return encrypted_text
    except requests.exceptions.RequestException:
        return encrypted_text 

# --- CRYPTO ENGINE (Modern - AES) ---
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

# --- FUNGSI HELPER WHITE-MIST ---
def encrypt_whitemist(data_bytes: bytes, key: str, is_text: bool = False) -> str:
    if crossCross is None:
        raise ImportError("Modul WhiteMist tidak ditemukan. Tidak bisa enkripsi.")
    string_to_encrypt = ""
    if is_text:
        string_to_encrypt = data_bytes.decode('utf-8')
    else:
        string_to_encrypt = base64.b64encode(data_bytes).decode('utf-8')
    enkripsi = crossCross.state(key=key, salt="Kriptoasik", sugar="FunKripto")
    encrypted_string = enkripsi.letsEncrypt(string_to_encrypt)
    return encrypted_string

def decrypt_whitemist(encrypted_string: str, key: str, is_text: bool = False) -> bytes:
    if crossCross is None:
        raise ImportError("Modul WhiteMist tidak ditemukan. Tidak bisa dekripsi.")
    dekripsi = crossCross.deState(key=key, salt="Kriptoasik", sugar="FunKripto")
    decrypted_string = dekripsi.letsDecrypt(encrypted_string)
    if is_text:
        return decrypted_string.encode('utf-8')
    else:
        try:
            decrypted_bytes = base64.b64decode(decrypted_string.encode('utf-8'))
            return decrypted_bytes
        except Exception as e:
            print(f"Gagal B64Decode WhiteMist, fallback ke UTF-8: {e}")
            return decrypted_string.encode('utf-8')

# --- KONFIGURASI KUNCI USB ---
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