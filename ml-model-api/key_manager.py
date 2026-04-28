import os
import time
import base64
from cryptography.fernet import Fernet
from security_config import SecurityConfig

class KeyManager:
    """
    Handles secure key generation, storage, and rotation.
    """

    def __init__(self):
        self.master_key = SecurityConfig.MASTER_KEY or self._generate_master_key()
        self.key_store = {}
        self.key_created_at = {}

    def _generate_master_key(self):
        return base64.urlsafe_b64encode(os.urandom(32)).decode()

    def create_data_key(self, key_id: str):
        key = Fernet.generate_key()
        self.key_store[key_id] = key
        self.key_created_at[key_id] = time.time()
        return key

    def get_key(self, key_id: str):
        if key_id not in self.key_store:
            raise Exception("Key not found")
        return self.key_store[key_id]

    def rotate_key(self, key_id: str):
        new_key = Fernet.generate_key()
        self.key_store[key_id] = new_key
        self.key_created_at[key_id] = time.time()
        return new_key

    def is_key_expired(self, key_id: str):
        created = self.key_created_at.get(key_id, 0)
        return (time.time() - created) > (SecurityConfig.KEY_ROTATION_DAYS * 86400)