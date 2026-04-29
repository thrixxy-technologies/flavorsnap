from cryptography.fernet import Fernet
from key_manager import KeyManager
from security_config import SecurityConfig
import base64
import hashlib

class EncryptionHandler:
    """
    Handles encryption/decryption of data at rest and in transit.
    """

    def __init__(self):
        self.key_manager = KeyManager()

    def encrypt(self, data: str, key_id: str) -> str:
        key = self.key_manager.get_key(key_id)
        f = Fernet(key)

        encrypted = f.encrypt(data.encode())

        if SecurityConfig.ENABLE_AUDIT_LOGS:
            print(f"[ENCRYPT] key_id={key_id}")

        return base64.b64encode(encrypted).decode()

    def decrypt(self, token: str, key_id: str) -> str:
        key = self.key_manager.get_key(key_id)
        f = Fernet(key)

        decrypted = f.decrypt(base64.b64decode(token.encode()))

        if SecurityConfig.ENABLE_AUDIT_LOGS:
            print(f"[DECRYPT] key_id={key_id}")

        return decrypted.decode()

    def hash_data(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()