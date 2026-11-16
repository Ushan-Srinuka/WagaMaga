import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--require-database",
        action="store_true",
        default=False,
        help="Fail instead of skip if integration DB configuration is missing",
    )


@pytest.fixture
def isolated_settings(monkeypatch):
    for name in (
        "DATABASE_URL",
        "MIGRATION_DATABASE_URL",
        "TEST_DATABASE_URL",
        "TEST_MIGRATION_DATABASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    from app.core.config import Settings

    return Settings(_env_file=None, app_env="test")
