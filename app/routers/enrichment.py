import logging

from fastapi import APIRouter, HTTPException

from app.models.enrichment import EnrichWordRequest, EnrichWordResponse, WordNlpData
from app.services.word_enricher import enrich_word, build_update_payload
from app.dependencies import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Enrichment"])


@router.post("/enrich-word", response_model=EnrichWordResponse)
async def enrich_word_endpoint(body: EnrichWordRequest):
    """Enrich a word with frequency and NLP data, and persist to Supabase."""
    try:
        data = enrich_word(body.text)
    except Exception:
        logger.exception("enrich_word failed for text=%s", body.text)
        raise HTTPException(status_code=500, detail="Enrichment failed")

    db_updated = False
    try:
        supabase = get_supabase()

        if body.word_id:
            rows = (
                supabase.table("en_words")
                .select("id, definition, synonymous, antonyms")
                .eq("id", body.word_id)
                .limit(1)
                .execute()
            )
        else:
            rows = (
                supabase.table("en_words")
                .select("id, definition, synonymous, antonyms")
                .eq("text", body.text)
                .limit(1)
                .execute()
            )

        if rows.data:
            row = rows.data[0]
            update_payload = build_update_payload(data, row)
            supabase.table("en_words").update(update_payload).eq("id", row["id"]).execute()
            supabase.table("learning_item_metadata").update({
                "priority": data.suggested_priority,
                "level": data.estimated_level,
            }).eq("item_type", "word").eq("item_id", row["id"]).execute()
            db_updated = True
    except ValueError:
        pass  # Supabase not configured
    except Exception:
        logger.exception("DB update failed for text=%s", body.text)

    return EnrichWordResponse(success=True, data=data, db_updated=db_updated)


@router.get("/word/{word_text}/nlp", response_model=WordNlpData)
async def get_word_nlp(word_text: str):
    """Return NLP data for a word (enrichment without DB write)."""
    try:
        return enrich_word(word_text)
    except Exception:
        logger.exception("enrich_word failed for text=%s", word_text)
        raise HTTPException(status_code=500, detail="Enrichment failed")
