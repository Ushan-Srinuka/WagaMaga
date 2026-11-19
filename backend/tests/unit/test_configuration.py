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


@pytest.mark.parametrize(
    "value",
    ["not-an-email", "https://example.com", "help@example.com\r\nBcc:other@example.com", 123],
)
def test_support_contact_rejects_non_email_and_header_injection(isolated_settings, value):
    with pytest.raises(ValidationError, match="valid public support email"):
        Settings(_env_file=None, support_contact_email=value)


@pytest.mark.parametrize("value", [None, ""])
def test_support_contact_can_be_unconfigured(isolated_settings, value):
    assert Settings(_env_file=None, support_contact_email=value).support_contact_email is None


def test_support_contact_normalizes_a_public_address_without_delivery_lookup(isolated_settings):
    assert (
        Settings(_env_file=None, support_contact_email=" help@EXAMPLE.com ").support_contact_email
        == "help@example.com"
    )
