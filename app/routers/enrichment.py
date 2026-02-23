import logging

from fastapi import APIRouter, HTTPException

from app.models.enrichment import EnrichWordRequest, EnrichWordResponse, WordNlpData
from app.services.word_enricher import enrich_word, build_update_payload, fetch_phonetics
from app.services.translation_service import get_translator
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
                .select("id")
                .eq("id", body.word_id)
                .limit(1)
                .execute()
            )
        else:
            rows = (
                supabase.table("en_words")
                .select("id")
                .eq("text", body.text)
                .limit(1)
                .execute()
            )

        if rows.data:
            row = rows.data[0]
            update_payload = build_update_payload(data)
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


@router.post("/batch-enrich-dictionary")
async def batch_enrich_dictionary():
    """Batch enrich all dictionary words: translations, phonetics, NLP data."""
    supabase = get_supabase()
    translator = get_translator()

    # 1. Collect all unique word_ids from en_dictionary_words
    word_ids: set[str] = set()
    offset = 0
    page_size = 1000
    while True:
        rows = (
            supabase.table("en_dictionary_words")
            .select("word_id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        for r in rows.data:
            if r["word_id"]:
                word_ids.add(r["word_id"])
        if len(rows.data) < page_size:
            break
        offset += page_size

    word_id_list = sorted(word_ids)
    total = len(word_id_list)
    translated = 0
    audio_filled = 0
    nlp_filled = 0
    errors = 0

    # 2. Process in batches
    batch_size = 50
    for i in range(0, total, batch_size):
        batch_ids = word_id_list[i : i + batch_size]
        words = (
            supabase.table("en_words")
            .select("id, text, phonetic_audio_link, phonetic_text, zipf_frequency")
            .in_("id", batch_ids)
            .execute()
        )

        for word in words.data:
            word_id = word["id"]
            text = word["text"]
            if not text:
                continue

            # Translation: always re-translate
            try:
                tr = translator.translate_word(text, "EN", "UK")
                supabase.table("en_to_uk_word_details").upsert({
                    "word_id": word_id,
                    "translations_text": tr.translated_text,
                }).execute()
                translated += 1
            except Exception:
                logger.exception("Translation failed for word=%s", text)
                errors += 1

            # Audio / Phonetic text: only if missing
            needs_audio = not word.get("phonetic_audio_link")
            needs_phonetic = not word.get("phonetic_text")
            if needs_audio or needs_phonetic:
                phonetics = fetch_phonetics(text)
                update: dict = {}
                if needs_audio and phonetics.get("phonetic_audio_link"):
                    update["phonetic_audio_link"] = phonetics["phonetic_audio_link"]
                if needs_phonetic and phonetics.get("phonetic_text"):
                    update["phonetic_text"] = phonetics["phonetic_text"]
                if update:
                    supabase.table("en_words").update(update).eq("id", word_id).execute()
                    audio_filled += 1 if "phonetic_audio_link" in update else 0

            # NLP: only if missing
            if word.get("zipf_frequency") is None:
                try:
                    nlp = enrich_word(text)
                    payload = build_update_payload(nlp)
                    supabase.table("en_words").update(payload).eq("id", word_id).execute()
                    supabase.table("learning_item_metadata").update({
                        "priority": nlp.suggested_priority,
                        "level": nlp.estimated_level,
                    }).eq("item_type", "word").eq("item_id", word_id).execute()
                    nlp_filled += 1
                except Exception:
                    logger.exception("NLP enrichment failed for word=%s", text)
                    errors += 1

            logger.info("Enriched dictionary word: %s", text)

    return {
        "total": total,
        "translated": translated,
        "audio_filled": audio_filled,
        "nlp_filled": nlp_filled,
        "errors": errors,
    }
