from fastapi.testclient import TestClient

from app.main import create_app


def test_liveness_and_docs_work_without_database(isolated_settings):
    with TestClient(create_app(isolated_settings)) as client:
        assert client.get("/health/live").json()["status"] == "ok"
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["database"] == "not_configured"


def test_unreachable_database_does_not_expose_credentials(isolated_settings):
    from pydantic import SecretStr

    settings = isolated_settings.model_copy(
        update={
            "database_url": SecretStr("postgresql+psycopg://user:private-password@127.0.0.1:1/db")
        }
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/health/live").status_code == 200
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert "private-password" not in response.text
        assert "Traceback" not in response.text


def test_cors_denies_unconfigured_origin(isolated_settings):
    with TestClient(create_app(isolated_settings)) as client:
        denied = client.get("/health/live", headers={"Origin": "https://untrusted.example"})
        allowed = client.get("/health/live", headers={"Origin": "http://localhost:5173"})
        assert "access-control-allow-origin" not in denied.headers
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_production_hides_openapi(isolated_settings):
    settings = isolated_settings.model_copy(update={"app_env": "production"})
    with TestClient(create_app(settings)) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
