import pytest
from pydantic import ValidationError

from app.models.enrichment import LexicalEvidenceRequest
from app.services.lexical_evidence import lexical_evidence


@pytest.mark.parametrize("surface,lemmas", [
    ("cities", {"city"}), ("went", {"go"}), ("children", {"child"}),
    ("axes", {"ax", "axe", "axis"}), ("better", {"good", "well"}),
    ("series", set()),
])
def test_morphology_retains_all_candidates_for_dictionary_confirmation(surface, lemmas):
    result = lexical_evidence(surface, "en")
    assert set(result["lemma_candidates"]) == lemmas
    assert result["zipf_frequency"] > 0


@pytest.mark.parametrize("sentence,word,is_entity", [
    ("Apple released a new product.", "Apple", True),
    ("I ate an apple.", "apple", False),
    ("I travelled to Turkey.", "Turkey", True),
    ("I ate a turkey.", "turkey", False),
])
def test_context_is_evidence_not_capitalization_alone(sentence, word, is_entity):
    start = sentence.index(word)
    request = LexicalEvidenceRequest(text=word, context={"text": sentence, "start": start, "end": start + len(word)})
    assert bool(lexical_evidence(word, "en", request.context)["named_entity"]) is is_entity


def test_unicode_selection_and_apostrophe_normalization():
    sentence = "🙂 I don’t know."
    start = sentence.index("don’t")
    request = LexicalEvidenceRequest(text="don't", context={"text": sentence, "start": start, "end": start + 5})
    assert lexical_evidence(request.text, "en", request.context)["named_entity"] is None
    with pytest.raises(ValidationError):
        LexicalEvidenceRequest(text="don't", context={"text": sentence, "start": start + 1, "end": start + 5})


def test_unsupported_language_does_not_misrepresent_english_evidence():
    assert lexical_evidence("word", "zz") == {
        "lemma_candidates": [], "zipf_frequency": None, "named_entity": None,
    }


def test_endpoint_authentication_and_retriable_resource_failure():
    from unittest.mock import patch

    from fastapi.testclient import TestClient
    from app.config import settings
    from app.main import app

    with patch.object(settings, "ANALYZER_API_KEY", "test-key"):
        client = TestClient(app)
        assert client.post("/api/lexical-evidence", json={"text": "cities"}).status_code == 401
        response = client.post("/api/lexical-evidence", json={"text": "cities"}, headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        assert response.json()["lemma_candidates"] == ["city"]
        with patch("app.routers.enrichment.lexical_evidence", side_effect=LookupError("missing model")):
            response = client.post("/api/lexical-evidence", json={"text": "cities"}, headers={"X-API-Key": "test-key"})
            assert response.status_code == 503
            assert "missing model" not in response.text
