"""
Tests for /docs and /openapi.json gating behind DISABLE_DOCS (T-04).

Strict TDD: tests written BEFORE production code.
"""
import pytest


class TestDocsGate:
    """Tests for docs gating behavior."""

    @pytest.fixture(autouse=True)
    def enable_auth(self, monkeypatch):
        """Auth ON; the legacy key acts as the opt-in machine credential (ID-11).

        DISABLE_AUTH is set to "" (never deleted) so a stray load_dotenv()
        cannot re-inject DISABLE_AUTH=1 from a developer .env after the app
        import — dotenv never overrides a present variable.
        """
        monkeypatch.setenv("DISABLE_AUTH", "")
        monkeypatch.setenv("PEAK_ADMIN_KEY_ENABLED", "1")

    def test_docs_bypassed_by_default(self, client, api_key):
        """GIVEN no DISABLE_DOCS WHEN accessing /docs THEN bypassed (no 401)."""
        response = client.get("/docs")
        # Should not return 401 (bypassed by default)
        assert response.status_code != 401

    def test_openapi_bypassed_by_default(self, client, api_key):
        """GIVEN no DISABLE_DOCS WHEN accessing /openapi.json THEN bypassed."""
        response = client.get("/openapi.json")
        assert response.status_code != 401

    def test_redoc_bypassed_by_default(self, client, api_key):
        """GIVEN no DISABLE_DOCS WHEN accessing /redoc THEN bypassed."""
        response = client.get("/redoc")
        assert response.status_code != 401

    def test_docs_blocked_when_disable_docs_set(self, client, monkeypatch):
        """GIVEN DISABLE_DOCS=1 WHEN accessing /docs without key THEN 401."""
        monkeypatch.setenv("DISABLE_DOCS", "1")
        response = client.get("/docs")
        assert response.status_code == 401

    def test_openapi_blocked_when_disable_docs_set(self, client, monkeypatch):
        """GIVEN DISABLE_DOCS=1 WHEN accessing /openapi.json without key THEN 401."""
        monkeypatch.setenv("DISABLE_DOCS", "1")
        response = client.get("/openapi.json")
        assert response.status_code == 401

    def test_docs_allowed_with_key_when_disabled(self, client, monkeypatch, auth_headers):
        """GIVEN DISABLE_DOCS=1 WHEN accessing /docs with valid key THEN passes."""
        monkeypatch.setenv("DISABLE_DOCS", "1")
        response = client.get("/docs", headers=auth_headers)
        assert response.status_code != 401

    def test_health_not_affected_by_disable_docs(self, client, monkeypatch):
        """GIVEN DISABLE_DOCS=1 WHEN accessing /api/health THEN still bypassed."""
        monkeypatch.setenv("DISABLE_DOCS", "1")
        response = client.get("/api/health")
        assert response.status_code == 200
