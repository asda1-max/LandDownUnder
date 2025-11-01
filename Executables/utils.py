import os
import base64
import hashlib
import json
from stegano import lsb
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

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
        print("Error: Format salt/hash tidak valid di JSON.")
        return False

# --- MANAJEMEN USER ---
class UserManager:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Naik satu folder (ke "Aplikas")
        parent_dir = os.path.dirname(current_dir)

        # Gabungkan ke folder "jsonfile"
        json_folder = os.path.join(parent_dir, "data")

        # Pastikan foldernya ada
        os.makedirs(json_folder, exist_ok=True)

        # Path file JSON
        json_path = os.path.join(json_folder, "userdat.json")
        self.filename = json_path
        self.users = self.load_users()

    def load_users(self):
        if not os.path.exists(self.filename):
            return {}
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Gagal membaca {self.filename}. Membuat file baru.")
            return {}

    def save_users(self):
        with open(self.filename, 'w') as f:
            json.dump(self.users, f, indent=2)

    def register_user(self, username, password):
        if username in self.users:
            return False, "Username sudah ada."
        if not username or not password:
            return False, "Username dan password tidak boleh kosong."
            
        salt_hex, hash_hex = hash_password(password)
        self.users[username] = (salt_hex, hash_hex)
        self.save_users()
        print(f"User DB (DEBUG): {self.users}")
        return True, "Akun berhasil dibuat!"

    def verify_user(self, username, password):
        if username not in self.users:
            return False
        
        stored_salt_hex, stored_hash_hex = self.users[username]
        return verify_password(stored_salt_hex, stored_hash_hex, password)

# --- MANAJEMEN PESAN ---
class MessageManager:
    
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Naik satu folder (ke "Aplikas")
        parent_dir = os.path.dirname(current_dir)

        # Gabungkan ke folder "jsonfile"
        json_folder = os.path.join(parent_dir, "data")

        # Pastikan foldernya ada
        os.makedirs(json_folder, exist_ok=True)

        # Path file JSON
        json_path = os.path.join(json_folder, "chat")

        self.chat_dir = json_path
        if not os.path.exists(self.chat_dir):
            os.makedirs(self.chat_dir)

    def get_chat_id(self, user1, user2):
        users = sorted([user1, user2])
        return f"{users[0]}_{users[1]}"

    def _get_chat_filepath(self, chat_id):
        return os.path.join(self.chat_dir, f"{chat_id}.json")

    def load_messages(self, chat_id):
        filepath = self._get_chat_filepath(chat_id)
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Gagal membaca file chat {filepath}.")
            return []

    def save_message(self, chat_id, message_data):
        messages = self.load_messages(chat_id)
        messages.append(message_data)
        filepath = self._get_chat_filepath(chat_id)
        with open(filepath, 'w') as f:
            json.dump(messages, f, indent=2)

# --- FUNGSI SUPER ENKRIPSI (Klasik) ---
def vigenere_encrypt(plain_text, key):
    encrypted_text = ""
    key_index = 0
    key = key.lower()
    if not key: key = "defaultkey"
    for char in plain_text:
        if 'a' <= char <= 'z':
            key_char = key[key_index % len(key)]; key_offset = ord(key_char) - ord('a')
            new_char_code = (ord(char) - ord('a') + key_offset) % 26
            encrypted_text += chr(new_char_code + ord('a')); key_index += 1
        elif 'A' <= char <= 'Z':
            key_char = key[key_index % len(key)]; key_offset = ord(key_char) - ord('a')
            new_char_code = (ord(char) - ord('A') + key_offset) % 26
            encrypted_text += chr(new_char_code + ord('A')); key_index += 1
        else: encrypted_text += char
    return encrypted_text

def vigenere_decrypt(encrypted_text, key):
    decrypted_text = ""
    key_index = 0
    key = key.lower()
    if not key: key = "defaultkey"
    for char in encrypted_text:
        if 'a' <= char <= 'z':
            key_char = key[key_index % len(key)]; key_offset = ord(key_char) - ord('a')
            new_char_code = (ord(char) - ord('a') - key_offset) % 26
            decrypted_text += chr(new_char_code + ord('a')); key_index += 1
        elif 'A' <= char <= 'Z':
            key_char = key[key_index % len(key)]; key_offset = ord(key_char) - ord('a')
            new_char_code = (ord(char) - ord('A') - key_offset) % 26
            decrypted_text += chr(new_char_code + ord('A')); key_index += 1
        else: decrypted_text += char
    return decrypted_text

# --- CRYPTO ENGINE (Modern) ---
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
            print(f"Error dekripsi: {e}")
            raise ValueError("Gagal mendekripsi data: Password salah atau data korup.")