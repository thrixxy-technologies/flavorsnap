from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from src.api.main import create_app
from src.api.models import AppSettings, PredictionScore


class FakeClassifier:
    def __init__(self) -> None:
        self.ready = False
        self.class_names = ["Akara", "Bread", "Egusi", "Moi Moi"]

    def load(self) -> None:
        self.ready = True

    def classify(self, image_bytes: bytes, options) -> list[PredictionScore]:
        if image_bytes == b"bad-image":
            raise ValueError("Uploaded file is not a valid image.")
        if image_bytes == b"boom":
            raise RuntimeError("Classifier crashed.")

        return [
            PredictionScore(label="Moi Moi", confidence=0.91),
            PredictionScore(label="Akara", confidence=0.06),
            PredictionScore(label="Bread", confidence=0.03),
        ][: options.top_k]


@pytest.fixture
def settings() -> AppSettings:
    return AppSettings.model_validate(
        {
            "api": {
                "max_upload_size_mb": 1,
                "rate_limit": {
                    "requests": 10,
                    "window_seconds": 60,
                    "exempt_paths": ["/docs", "/redoc", "/openapi.json", "/health"],
                },
            }
        }
    )


@pytest.fixture
def client(settings: AppSettings) -> TestClient:
    app = create_app(settings=settings, classifier=FakeClassifier())
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.integration
def test_classify_happy_path_returns_ranked_predictions(client: TestClient) -> None:
    response = client.post(
        "/api/v1/classify",
        files={"image": ("meal.png", b"fake-image-bytes", "image/png")},
        data={"top_k": "2", "resize": "256", "center_crop": "true", "normalize": "true"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["prediction"] == "Moi Moi"
    assert payload["confidence"] == 0.91
    assert len(payload["predictions"]) == 2
    assert payload["predictions"][0]["label"] == "Moi Moi"
    assert payload["processing_time_ms"] >= 0
    assert payload["preprocessing"] == {
        "resize": 256,
        "center_crop": True,
        "normalize": True,
        "top_k": 2,
    }
    assert payload["filename"] == "meal.png"
    assert response.headers["X-Request-ID"]


@pytest.mark.integration
def test_classify_rejects_empty_upload(client: TestClient) -> None:
    response = client.post(
        "/api/v1/classify",
        files={"image": ("empty.png", b"", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty."


@pytest.mark.integration
def test_classify_rejects_unsupported_media_type(client: TestClient) -> None:
    response = client.post(
        "/api/v1/classify",
        files={"image": ("meal.gif", b"gif-bytes", "image/gif")},
    )

    assert response.status_code == 415
    assert "Unsupported media type" in response.json()["detail"]


@pytest.mark.integration
def test_classify_returns_400_for_invalid_image(client: TestClient) -> None:
    response = client.post(
        "/api/v1/classify",
        files={"image": ("bad.png", b"bad-image", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is not a valid image."


@pytest.mark.integration
def test_rate_limit_returns_429() -> None:
    class RateLimitClassifier(FakeClassifier):
        def classify(self, image_bytes: bytes, options) -> list[PredictionScore]:
            return [PredictionScore(label="Akara", confidence=0.88)]

    settings = AppSettings.model_validate(
        {
            "api": {
                "rate_limit": {
                    "requests": 2,
                    "window_seconds": 60,
                    "exempt_paths": ["/docs", "/redoc", "/openapi.json", "/health"],
                }
            }
        }
    )

    app = create_app(settings=settings, classifier=RateLimitClassifier())
    with TestClient(app) as client:
        first = client.post("/api/v1/classify", files={"image": ("meal.png", b"image-1", "image/png")})
        second = client.post(
            "/api/v1/classify", files={"image": ("meal.png", b"image-2", "image/png")}
        )
        third = client.post("/api/v1/classify", files={"image": ("meal.png", b"image-3", "image/png")})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["detail"] == "Rate limit exceeded. Try again later."
    assert int(third.headers["Retry-After"]) >= 1

