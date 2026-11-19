"""Disposable browser fixture server. Refuses development/production databases."""

import os
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.main import create_app
from app.modules.identity.models import User
from app.modules.identity.security import passwords
from app.modules.identity.service import write_audit


def main():
    baseline = Settings()
    urls = (baseline.test_database_url, baseline.test_migration_database_url)
    if any(url is None for url in urls):
        raise RuntimeError("Dedicated browser test database URLs are required")
    for url in urls:
        if not (make_url(url.get_secret_value()).database or "").endswith("_test"):
            raise RuntimeError("Refusing browser fixtures outside an _test database")
    run_id = os.environ["E2E_RUN_ID"]
    api_port = int(os.environ.get("E2E_API_PORT", "8000"))
    web_port = int(os.environ.get("E2E_WEB_PORT", "5173"))
    if not all(1024 <= port <= 65535 for port in (api_port, web_port)):
        raise RuntimeError("E2E ports must be between 1024 and 65535")
    web_origin = f"http://127.0.0.1:{web_port}"
    password = os.environ["E2E_PASSWORD"]
    owner = create_engine(urls[1].get_secret_value(), hide_parameters=True)
    with owner.begin() as connection:
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    with Session(owner) as db, db.begin():
        admin = User(
            email=f"browser-admin-{run_id}@example.com",
            display_name="Browser administrator",
            password_hash=passwords.hash(password),
            role="administrator",
        )
        db.add(admin)
        db.flush()
        write_audit(
            db,
            admin.id,
            admin.id,
            "test-fixture",
            None,
            "administrator",
            "Synthetic dedicated browser-test account",
            run_id,
        )
    owner.dispose()
    settings = baseline.model_copy(
        update={
            "app_env": "test",
            "database_url": baseline.test_database_url,
            "auth_signing_key": SecretStr(os.environ["E2E_SIGNING_KEY"]),
            "auth_registration_attempts": 100,
            "auth_login_ip_attempts": 1000,
            "auth_refresh_attempts": 1000,
            "cors_allowed_origins": [web_origin],
            "auth_allowed_origins": [web_origin],
        }
    )
    uvicorn.run(
        create_app(settings), host="127.0.0.1", port=api_port, proxy_headers=False, access_log=False
    )


if __name__ == "__main__":
    main()
