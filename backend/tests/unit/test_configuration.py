import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import PROJECT_ROOT, Settings


def test_sqlite_is_rejected(isolated_settings):
    with pytest.raises(ValidationError, match="postgresql\\+psycopg"):
        Settings(_env_file=None, database_url=SecretStr("sqlite:///:memory:"))


@pytest.mark.parametrize("origin", ["*", "https://*.example.com", "https://user:secret@host"])
def test_cors_requires_explicit_origins(isolated_settings, origin):
    with pytest.raises(ValidationError, match="explicit HTTP"):
        Settings(_env_file=None, cors_allowed_origins=[origin])


def test_relative_storage_has_same_location_for_api_and_worker(isolated_settings):
    settings = Settings(_env_file=None, document_storage_path=".data/documents")
    assert settings.document_storage_path == PROJECT_ROOT / ".data" / "documents"
