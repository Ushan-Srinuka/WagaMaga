import pytest
from pydantic import ValidationError

from app.core.config import FarmerAdvisoryQualityReview
from app.modules.knowledge.pilot import release_configured


def test_production_release_rechecks_the_attested_model_and_corpus(isolated_settings):
    settings = isolated_settings.model_copy(update={"app_env": "production"})
    settings.farmer_advisory_enabled = True
    document = "a" * 64
    settings.gemini_approved_pdf_checksums = {document}
    settings.rag_embedding_pdf_checksums = {document}
    assert not release_configured(settings)
    fields = {
        "report_sha256": "b" * 64,
        "reviewer": "Fictional reviewer for test",
        "model": settings.gemini_model,
        "pdf_checksums": {document},
        "question_count": 32,
        "recall_at_5": 0.8,
        "supported_claim_rate": 0.9,
        "unsupported_actionable_treatments": 0,
    }
    for invalid in (
        {"question_count": 29},
        {"recall_at_5": 0.79},
        {"supported_claim_rate": 0.89},
        {"unsupported_actionable_treatments": 1},
    ):
        with pytest.raises(ValidationError):
            FarmerAdvisoryQualityReview.model_validate(fields | invalid)
    settings.farmer_advisory_quality_review = FarmerAdvisoryQualityReview.model_validate(fields)
    assert release_configured(settings)
    settings.rag_embedding_pdf_checksums.add("c" * 64)
    assert not release_configured(settings)
    settings.rag_embedding_pdf_checksums.remove("c" * 64)
    settings.gemini_model = "gemini-test-changed"
    assert not release_configured(settings)
