import logging

from fastapi import APIRouter, HTTPException

from app.models.translation import TranslateRequest, TranslateResponse
from app.services.translation_service import get_translator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Translation"])


@router.post("/translate", response_model=TranslateResponse)
async def translate(body: TranslateRequest):
    """Translate text with optional context for more accurate word-level translation."""
    translator = get_translator()
    if not translator.available:
        raise HTTPException(status_code=503, detail="DeepL API key not configured")

    try:
        return translator.translate_word(
            text=body.text,
            source_lang=body.source_lang,
            target_lang=body.target_lang,
            context=body.context,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Translation failed for text=%s", body.text)
        raise HTTPException(status_code=500, detail="Translation failed")
