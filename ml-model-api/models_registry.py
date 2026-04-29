import json
import os
import random
from datetime import datetime

REGISTRY_PATH = "ml-model-api/registry/registry.json"


class ModelRegistry:
    def __init__(self):
        os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)

        if not os.path.exists(REGISTRY_PATH):
            with open(REGISTRY_PATH, "w") as f:
                json.dump({"models": {}, "active": None, "ab_test": None}, f)

        self._load()

    def _load(self):
        with open(REGISTRY_PATH, "r") as f:
            self.registry = json.load(f)

    def _save(self):
        with open(REGISTRY_PATH, "w") as f:
            json.dump(self.registry, f, indent=4)

    # -----------------------------
    # 📌 Register Model
    # -----------------------------
    def register_model(self, name, version, path):
        if name not in self.registry["models"]:
            self.registry["models"][name] = {}

        self.registry["models"][name][version] = {
            "path": path,
            "created_at": str(datetime.utcnow()),
        }

        self._save()

    # -----------------------------
    # 🚀 Set Active Version
    # -----------------------------
    def set_active(self, name, version):
        if name not in self.registry["models"] or \
           version not in self.registry["models"][name]:
            raise ValueError("Model version not found")

        self.registry["active"] = {"name": name, "version": version}
        self._save()

    # -----------------------------
    # 🔁 Rollback
    # -----------------------------
    def rollback(self, name, version):
        print(f"🔁 Rolling back to {name}:{version}")
        self.set_active(name, version)

    # -----------------------------
    # 🧪 Enable A/B Testing
    # -----------------------------
    def enable_ab_test(self, name, version_a, version_b, ratio=0.5):
        self.registry["ab_test"] = {
            "name": name,
            "version_a": version_a,
            "version_b": version_b,
            "ratio": ratio,
        }
        self._save()

    # -----------------------------
    # 🎯 Get Model for Prediction
    # -----------------------------
    def get_model(self):
        # A/B testing logic
        ab = self.registry.get("ab_test")

        if ab:
            chosen_version = (
                ab["version_a"]
                if random.random() < ab["ratio"]
                else ab["version_b"]
            )
            return self._get_model_path(ab["name"], chosen_version)

        # Default active model
        active = self.registry["active"]
        if not active:
            raise ValueError("No active model set")

        return self._get_model_path(active["name"], active["version"])

    # -----------------------------
    # 🔍 Helper
    # -----------------------------
    def _get_model_path(self, name, version):
        return self.registry["models"][name][version]["path"]