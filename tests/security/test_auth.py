"""
Authentication & Authorisation Security Tests  —  FlavorSnap Issue #226

Covers:
  - JWT algorithm confusion (alg=none attack)
  - JWT signature tampering
  - Expired token rejection
  - Brute-force / rate-limiting resistance
  - Privilege escalation (IDOR on user-scoped resources)
  - Missing / malformed Authorization header
"""
from __future__ import annotations

import base64
import json
import time

import pytest

from tests.security.conftest import (
    make_expired_jwt_claims,
    make_none_alg_jwt,
    make_tampered_jwt,
)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _forge_jwt(header: dict, payload: dict, signature: str = "") -> str:
    h = _b64url(json.dumps(header).encode())
    p = _b64url(json.dumps(payload).encode())
    return f"{h}.{p}.{signature}"


# ---------------------------------------------------------------------------
# JWT — algorithm confusion (alg=none)
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestJWTAlgorithmConfusion:
    """alg=none tokens must be unconditionally rejected (RFC 8725 §2.1)."""

    def test_none_alg_token_returns_401(self, test_client: object) -> None:
        evil_token = make_none_alg_jwt(
            {"sub": "attacker", "role": "admin", "iat": int(time.time())}
        )
        response = test_client.get(  # type: ignore[attr-defined]
            "/api/profile",
            headers={"Authorization": f"Bearer {evil_token}"},
        )
        assert response.status_code == 401, (
            "alg=none JWT must be rejected — algorithm confusion vulnerability detected"
        )

    def test_none_alg_does_not_grant_admin(self, test_client: object) -> None:
        evil_token = make_none_alg_jwt(
            {"sub": "attacker", "role": "admin", "iat": int(time.time())}
        )
        response = test_client.get(  # type: ignore[attr-defined]
            "/api/admin",
            headers={"Authorization": f"Bearer {evil_token}"},
        )
        assert response.status_code in (401, 403, 404), (
            "alg=none token must not grant admin privileges"
        )

    def test_hs256_token_signed_with_public_key_rejected(self, test_client: object) -> None:
        forged = _forge_jwt(
            {"alg": "HS256", "typ": "JWT"},
            {"sub": "attacker", "role": "admin"},
            signature="forged_sig",
        )
        response = test_client.get(  # type: ignore[attr-defined]
            "/api/profile",
            headers={"Authorization": f"Bearer {forged}"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# JWT — signature tampering
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestJWTSignatureTampering:
    """Any modification to a valid token's signature must invalidate it."""

    def test_tampered_signature_returns_401(self, auth_token: str, test_client: object) -> None:
        tampered = make_tampered_jwt(auth_token)
        response = test_client.get(  # type: ignore[attr-defined]
            "/api/profile",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert response.status_code == 401, (
            "Tampered JWT signature was accepted — HMAC/RSA verification not enforced"
        )

    def test_empty_signature_returns_401(self, auth_token: str, test_client: object) -> None:
        parts = auth_token.split(".")
        no_sig_token = f"{parts[0]}.{parts[1]}."
        response = test_client.get(  # type: ignore[attr-defined]
            "/api/profile",
            headers={"Authorization": f"Bearer {no_sig_token}"},
        )
        assert response.status_code == 401

    def test_modified_payload_returns_401(self, auth_token: str, test_client: object) -> None:
        parts = auth_token.split(".")
        padding = "=" * (4 - len(parts[1]) % 4)
        original_payload = json.loads(base64.urlsafe_b64decode(parts[1] + padding))
        original_payload["role"] = "admin"
        new_payload = _b64url(json.dumps(original_payload).encode())
        evil_token = f"{parts[0]}.{new_payload}.{parts[2]}"
        response = test_client.get(  # type: ignore[attr-defined]
            "/api/profile",
            headers={"Authorization": f"Bearer {evil_token}"},
        )
        assert response.status_code == 401, (
            "Modified JWT payload with original signature was accepted"
        )


# ---------------------------------------------------------------------------
# JWT — expiry
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestJWTExpiry:
    """Expired tokens must never grant access."""

    def test_expired_token_returns_401(self, test_client: object) -> None:
        expired_claims = make_expired_jwt_claims()
        expired_token = make_none_alg_jwt(expired_claims)
        response = test_client.get(  # type: ignore[attr-defined]
            "/api/profile",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401, "Expired JWT must be rejected"

    def test_token_without_exp_claim_returns_401(self, test_client: object) -> None:
        no_exp_token = _forge_jwt(
            {"alg": "HS256", "typ": "JWT"},
            {"sub": "user123"},
        )
        response = test_client.get(  # type: ignore[attr-defined]
            "/api/profile",
            headers={"Authorization": f"Bearer {no_exp_token}"},
        )
        assert response.status_code == 401, (
            "JWT without exp claim should be rejected to prevent indefinite access"
        )


# ---------------------------------------------------------------------------
# Missing / malformed Authorization header
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestMissingAuthorizationHeader:
    """Protected endpoints must reject requests with no or malformed auth."""

    @pytest.mark.parametrize("headers", [
        {},
        {"Authorization": ""},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer "},
        {"Authorization": "Basic dXNlcjpwYXNz"},
        {"Authorization": "Token abc123"},
        {"X-Auth-Token": "some-token"},
    ])
    def test_protected_endpoint_rejects_bad_auth(
        self, headers: dict, test_client: object
    ) -> None:
        response = test_client.get("/api/profile", headers=headers)  # type: ignore[attr-defined]
        assert response.status_code in (401, 403), (
            f"Protected endpoint accepted request with bad auth header: {headers}"
        )


# ---------------------------------------------------------------------------
# Brute-force / rate limiting
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestBruteForceProtection:
    """Login endpoint must rate-limit repeated failed attempts."""

    THRESHOLD = 10
    ENDPOINT = "/api/auth/login"
    BAD_CREDS = {"username": "admin@flavorsnap.io", "password": "wrong_password"}

    def test_repeated_login_failures_trigger_rate_limit(self, test_client: object) -> None:
        status_codes: list[int] = []
        for _ in range(self.THRESHOLD + 5):
            resp = test_client.post(self.ENDPOINT, json=self.BAD_CREDS)  # type: ignore[attr-defined]
            status_codes.append(resp.status_code)
        assert 429 in status_codes, (
            f"No 429 returned after {self.THRESHOLD + 5} failed login attempts — "
            "brute-force protection may be absent"
        )

    def test_valid_login_still_works_after_different_ip(self, test_client: object) -> None:
        resp = test_client.post(  # type: ignore[attr-defined]
            self.ENDPOINT,
            json={"username": "valid_user@flavorsnap.io", "password": "correct_password"},
            headers={"X-Forwarded-For": "10.0.0.99"},
        )
        assert resp.status_code != 429, (
            "Rate-limit may be global rather than per-IP — legitimate users locked out"
        )


# ---------------------------------------------------------------------------
# Privilege escalation / IDOR
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestPrivilegeEscalation:
    """A regular user must not access another user's resources by changing an ID."""

    def test_user_cannot_access_other_users_profile(
        self, auth_token: str, test_client: object
    ) -> None:
        response = test_client.get(  # type: ignore[attr-defined]
            "/api/users/9999999/profile",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code in (403, 404), (
            "User can access another user's profile by guessing the ID — IDOR vulnerability"
        )

    def test_regular_user_cannot_reach_admin_endpoints(
        self, auth_token: str, test_client: object
    ) -> None:
        for endpoint in ["/api/admin/users", "/api/admin/models", "/api/admin/config"]:
            response = test_client.get(  # type: ignore[attr-defined]
                endpoint,
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            assert response.status_code in (403, 404), (
                f"Regular user JWT grants access to admin endpoint: {endpoint}"
            )
