import json
from encryption_handler import EncryptionHandler

class SecureStorage:
    """
    Encrypted persistent storage layer.
    """

    def __init__(self):
        self.encryption = EncryptionHandler()
        self.storage = {}  # simulate DB

    def save(self, key_id: str, record_id: str, data: dict):
        raw = json.dumps(data)
        encrypted = self.encryption.encrypt(raw, key_id)

        self.storage[record_id] = {
            "data": encrypted,
            "key_id": key_id
        }

    def load(self, record_id: str):
        record = self.storage.get(record_id)

        if not record:
            raise Exception("Record not found")

        decrypted = self.encryption.decrypt(
            record["data"],
            record["key_id"]
        )

        return json.loads(decrypted)

    def list_records(self):
        return list(self.storage.keys())