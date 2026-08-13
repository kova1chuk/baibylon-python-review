import logging

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import require_api_key
from app.models.enrichment import (
    EnrichWordRequest,
    EnrichWordResponse,
    WordNlpData,
    WordPhoneticsData,
)
from app.services.word_enricher import enrich_word, fetch_phonetics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Enrichment"], dependencies=[Depends(require_api_key)])


@router.post("/enrich-word", response_model=EnrichWordResponse)
async def enrich_word_endpoint(body: EnrichWordRequest):
    """Return word enrichment data without persisting it."""
    try:
        data = enrich_word(body.text)
    except Exception:
        logger.exception("enrich_word failed for text=%s", body.text)
        raise HTTPException(status_code=500, detail="Enrichment failed")

    return EnrichWordResponse(success=True, data=data, db_updated=False)


@router.get("/word/{word_text}/nlp", response_model=WordNlpData)
async def get_word_nlp(word_text: str):
    """Return NLP data for a word (enrichment without DB write)."""
    try:
        return enrich_word(word_text)
    except Exception:
        logger.exception("enrich_word failed for text=%s", word_text)
        raise HTTPException(status_code=500, detail="Enrichment failed")


@router.get("/word/{word_text}/phonetics", response_model=WordPhoneticsData)
async def get_word_phonetics(word_text: str):
    """Return phonetic text and audio without persisting them."""
    return WordPhoneticsData(**fetch_phonetics(word_text))
