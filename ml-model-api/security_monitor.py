import time

class EncryptionMonitor:
    """
    Tracks encryption performance and security events.
    """

    def __init__(self):
        self.logs = []

    def log_event(self, event_type: str, meta: dict):
        self.logs.append({
            "type": event_type,
            "meta": meta,
            "timestamp": time.time()
        })

    def get_metrics(self):
        return {
            "total_events": len(self.logs),
            "encryption_events": len([l for l in self.logs if l["type"] == "encrypt"]),
            "decryption_events": len([l for l in self.logs if l["type"] == "decrypt"]),
        }