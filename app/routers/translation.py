import logging

from fastapi import APIRouter, Depends, HTTPException

from app.models.translation import TranslateRequest, TranslateResponse
from app.services.translation_service import get_translator
from app.dependencies import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Translation"], dependencies=[Depends(require_api_key)])


@router.post("/translate", response_model=TranslateResponse)
async def translate(body: TranslateRequest):
    translator = get_translator()

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
