"""Generate ignored local configuration without overwriting existing settings."""

import argparse
import secrets
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=55432)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a non-privileged TCP port between 1024 and 65535")
    root = Path(__file__).resolve().parents[1]
    env_file = root / ".env"
    if env_file.exists():
        print("Existing .env preserved; no credentials changed.")
        return
    bootstrap_password = secrets.token_hex(24)
    app_password = secrets.token_hex(24)
    host = f"127.0.0.1:{args.port}"

    def url(user: str, password: str, database: str) -> str:
        return f"postgresql+psycopg://{user}:{password}@{host}/{database}"

    values = {
        "APP_ENV": "development",
        "CORS_ALLOWED_ORIGINS": '["http://localhost:5173","http://127.0.0.1:5173"]',
        "POSTGRES_USER": "wagamaga_bootstrap",
        "POSTGRES_PASSWORD": bootstrap_password,
        "POSTGRES_PORT": str(args.port),
        "APP_DB_USER": "wagamaga_app",
        "APP_DB_PASSWORD": app_password,
        "APP_DB_NAME": "wagamaga",
        "TEST_DB_NAME": "wagamaga_test",
        "DATABASE_URL": url("wagamaga_app", app_password, "wagamaga"),
        "MIGRATION_DATABASE_URL": url("wagamaga_bootstrap", bootstrap_password, "wagamaga"),
        "TEST_DATABASE_URL": url("wagamaga_app", app_password, "wagamaga_test"),
        "TEST_MIGRATION_DATABASE_URL": url(
            "wagamaga_bootstrap", bootstrap_password, "wagamaga_test"
        ),
        "DOCUMENT_STORAGE_PATH": ".data/documents",
    }
    with env_file.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("# Local development only. Generated credentials; never commit this file.\n")
        stream.writelines(f"{key}={value}\n" for key, value in values.items())
    (root / ".data" / "documents").mkdir(parents=True, exist_ok=True)
    print("Created ignored .env and private local document directory; credentials not printed.")


if __name__ == "__main__":
    main()
