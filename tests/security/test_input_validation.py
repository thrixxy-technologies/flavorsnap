"""
Input Validation Security Tests  —  FlavorSnap Issue #226

Covers:
  - SQL injection
  - XSS payloads
  - Path traversal
  - Command injection
  - Oversized payload rejection
  - Content-type mismatch
  - Mass assignment
"""
from __future__ import annotations

import pytest

from tests.security.conftest import (
    COMMAND_INJECTION_PAYLOADS,
    OVERSIZED_PAYLOAD,
    PATH_TRAVERSAL_PAYLOADS,
    SQL_INJECTION_PAYLOADS,
    XSS_PAYLOADS,
)


# ---------------------------------------------------------------------------
# SQL Injection
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestSQLInjection:
    """SQL injection payloads must never cause 500 errors or leak DB details."""

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_search_endpoint_rejects_sqli(
        self, payload: str, auth_token: str, test_client: object
    ) -> None:
        response = test_client.get(  # type: ignore[attr-defined]
            "/api/foods/search",
            params={"q": payload},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code != 500, (
            f"SQL injection payload caused 500 — possible unsanitised query.\nPayload: {payload!r}"
        )
        body = response.text.lower()
        for kw in ["syntax error", "unclosed quotation", "pg_query", "sqlstate"]:
            assert kw not in body, (
                f"SQL error detail exposed in response (keyword: {kw!r}).\nPayload: {payload!r}"
            )

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_feedback_label_field_rejects_sqli(
        self, payload: str, auth_token: str, test_client: object
    ) -> None:
        response = test_client.post(  # type: ignore[attr-defined]
            "/api/classifications/feedback",
            json={"label": payload, "image_id": 1},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code != 500, (
            f"SQL injection in POST body caused 500.\nPayload: {payload!r}"
        )

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_registration_fields_reject_sqli(
        self, payload: str, test_client: object
    ) -> None:
        response = test_client.post(  # type: ignore[attr-defined]
            "/api/auth/register",
            json={"username": payload, "email": "test@test.com", "password": "ValidPass123!"},
        )
        assert response.status_code not in (200, 500), (
            f"SQLi in username field returned unexpected status.\nPayload: {payload!r}"
        )


# ---------------------------------------------------------------------------
# XSS
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestXSSPrevention:
    """XSS payloads must never be reflected verbatim in responses."""

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_search_does_not_reflect_xss(
        self, payload: str, auth_token: str, test_client: object
    ) -> None:
        response = test_client.get(  # type: ignore[attr-defined]
            "/api/foods/search",
            params={"q": payload},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        for pattern in ["<script>", "onerror=", "onload=", "javascript:"]:
            assert pattern.lower() not in response.text.lower(), (
                f"XSS payload reflected in response (pattern: {pattern!r}).\nPayload: {payload!r}"
            )

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_feedback_comment_strips_xss(
        self, payload: str, auth_token: str, test_client: object
    ) -> None:
        response = test_client.post(  # type: ignore[attr-defined]
            "/api/classifications/feedback",
            json={"label": "Akara", "comment": payload, "image_id": 1},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        if response.status_code == 200:
            assert "<script>" not in response.text, (
                f"XSS stored and reflected without sanitisation.\nPayload: {payload!r}"
            )

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_template_injection_not_evaluated(
        self, payload: str, auth_token: str, test_client: object
    ) -> None:
        response = test_client.get(  # type: ignore[attr-defined]
            "/api/foods/search",
            params={"q": payload},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        if "{{7*7}}" in payload or "${7*7}" in payload:
            assert "49" not in response.text, (
                "Template injection {{7*7}} was evaluated — SSTI detected"
            )


# ---------------------------------------------------------------------------
# Path Traversal
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestPathTraversal:
    """Path traversal payloads must never access files outside the upload directory."""

    @pytest.mark.parametrize("payload", PATH_TRAVERSAL_PAYLOADS)
    def test_uploads_endpoint_rejects_traversal(
        self, payload: str, auth_token: str, test_client: object
    ) -> None:
        response = test_client.get(  # type: ignore[attr-defined]
            f"/api/uploads/{payload}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code in (400, 403, 404), (
            f"Path traversal not rejected (status {response.status_code}).\nPayload: {payload!r}"
        )
        if response.status_code == 200:
            assert "root:" not in response.text, (
                f"Path traversal succeeded — /etc/passwd content returned.\nPayload: {payload!r}"
            )

    @pytest.mark.parametrize("payload", PATH_TRAVERSAL_PAYLOADS)
    def test_static_endpoint_rejects_traversal(
        self, payload: str, test_client: object
    ) -> None:
        response = test_client.get(f"/static/{payload}")  # type: ignore[attr-defined]
        assert response.status_code in (400, 403, 404), (
            f"Static file endpoint did not reject traversal.\nPayload: {payload!r}"
        )


# ---------------------------------------------------------------------------
# Command Injection
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestCommandInjection:
    """Command injection payloads must never cause 500 or execute system commands."""

    @pytest.mark.parametrize("payload", COMMAND_INJECTION_PAYLOADS)
    def test_search_rejects_command_injection(
        self, payload: str, auth_token: str, test_client: object
    ) -> None:
        response = test_client.get(  # type: ignore[attr-defined]
            "/api/foods/search",
            params={"q": payload},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code != 500, (
            f"Command injection caused 500.\nPayload: {payload!r}"
        )
        for pattern in ["root:", "uid=", "bin/bash", "volume serial"]:
            assert pattern.lower() not in response.text.lower(), (
                f"System output pattern {pattern!r} found in response.\nPayload: {payload!r}"
            )

    @pytest.mark.parametrize("payload", COMMAND_INJECTION_PAYLOADS)
    def test_label_field_rejects_command_injection(
        self, payload: str, auth_token: str, test_client: object
    ) -> None:
        response = test_client.post(  # type: ignore[attr-defined]
            "/api/classifications/feedback",
            json={"label": payload, "image_id": 1},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code != 500, (
            f"Command injection in label field caused 500.\nPayload: {payload!r}"
        )


# ---------------------------------------------------------------------------
# Oversized payloads
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestOversizedPayloads:
    """Payloads exceeding size limits must be rejected to prevent DoS."""

    def test_oversized_json_body_rejected(
        self, auth_token: str, test_client: object
    ) -> None:
        response = test_client.post(  # type: ignore[attr-defined]
            "/api/classifications/feedback",
            json={"label": OVERSIZED_PAYLOAD, "image_id": 1},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code in (400, 413, 422), (
            f"Oversized JSON body accepted (status {response.status_code})"
        )

    def test_oversized_query_param_rejected(
        self, auth_token: str, test_client: object
    ) -> None:
        response = test_client.get(  # type: ignore[attr-defined]
            "/api/foods/search",
            params={"q": "A" * 10_000},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code in (400, 413, 414, 422), (
            "Oversized query parameter not rejected"
        )


# ---------------------------------------------------------------------------
# Content-type & mass assignment
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestContentTypeAndMassAssignment:
    """JSON endpoints must reject wrong content-types and ignore extra fields."""

    def test_json_endpoint_rejects_xml_body(
        self, auth_token: str, test_client: object
    ) -> None:
        response = test_client.post(  # type: ignore[attr-defined]
            "/api/classifications/feedback",
            content=b"<label>Akara</label>",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/xml",
            },
        )
        assert response.status_code in (400, 415, 422), (
            "JSON endpoint accepted application/xml body"
        )

    def test_json_endpoint_rejects_plain_text(
        self, auth_token: str, test_client: object
    ) -> None:
        response = test_client.post(  # type: ignore[attr-defined]
            "/api/classifications/feedback",
            content=b"label=Akara&image_id=1",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "text/plain",
            },
        )
        assert response.status_code in (400, 415, 422)

    def test_extra_fields_not_used_for_privilege_escalation(
        self, auth_token: str, test_client: object
    ) -> None:
        response = test_client.post(  # type: ignore[attr-defined]
            "/api/classifications/feedback",
            json={
                "label": "Akara",
                "image_id": 1,
                "role": "admin",
                "is_superuser": True,
                "user_id": 1,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code in (200, 201, 400, 422), (
            "Unexpected status on mass-assignment probe"
        )
        if response.status_code in (200, 201):
            assert response.json().get("role") != "admin", (
                "Mass assignment succeeded — role: admin was accepted"
            )
