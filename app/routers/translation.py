import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.dependencies import require_api_key
from app.models.translation import (
    TranslateBatchRequest,
    TranslateBatchResponse,
    TranslateRequest,
    TranslateResponse,
    ValidateTranslationRequest,
    ValidateTranslationResponse,
)
from app.services.translation_service import get_translator, translation_ref

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Translation"], dependencies=[Depends(require_api_key)])


@router.post("/translate", response_model=TranslateResponse)
async def translate(body: TranslateRequest):
    translator = get_translator()

    try:
        return await asyncio.wait_for(
            run_in_threadpool(
                translator.translate_word,
                body.text,
                body.source_lang,
                body.target_lang,
                body.context,
            ),
            timeout=settings.TRANSLATION_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.warning(
            "Translation timed out %s",
            translation_ref(body.text, body.source_lang, body.target_lang, body.context),
        )
        raise HTTPException(status_code=504, detail="Translation timed out")
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Translation service unavailable")
    except Exception as exc:
        logger.error(
            "Translation failed %s error_type=%s",
            translation_ref(body.text, body.source_lang, body.target_lang, body.context),
            type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail="Translation failed")


@router.post("/translate/batch", response_model=TranslateBatchResponse)
async def translate_batch(body: TranslateBatchRequest):
    translator = get_translator()

    try:
        results = await asyncio.wait_for(
            run_in_threadpool(
                translator.translate_batch,
                body.texts,
                body.source_lang,
                body.target_lang,
            ),
            timeout=settings.TRANSLATION_BATCH_TIMEOUT_SECONDS,
        )
        return TranslateBatchResponse(results=results)
    except TimeoutError:
        logger.warning(
            "Translation batch timed out count=%d total_chars=%d source=%s target=%s",
            len(body.texts),
            sum(len(text) for text in body.texts),
            body.source_lang.lower(),
            body.target_lang.lower(),
        )
        raise HTTPException(status_code=504, detail="Translation batch timed out")
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Translation service unavailable")
    except Exception as exc:
        logger.error(
            "Translation batch failed count=%d total_chars=%d source=%s target=%s error_type=%s",
            len(body.texts),
            sum(len(text) for text in body.texts),
            body.source_lang.lower(),
            body.target_lang.lower(),
            type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail="Translation batch failed")


@router.post("/translation/validate", response_model=ValidateTranslationResponse)
async def validate_translation(body: ValidateTranslationRequest):
    translator = get_translator()

    try:
        return await asyncio.wait_for(
            run_in_threadpool(
                translator.validate_translation,
                body.source,
                body.target,
                body.native_lang,
            ),
            timeout=settings.TRANSLATION_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.warning(
            "Translation validation timed out %s candidate_len=%d",
            translation_ref(body.source, "en", body.native_lang),
            len(body.target),
        )
        raise HTTPException(status_code=504, detail="Translation validation timed out")
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Translation service unavailable")
    except Exception as exc:
        logger.error(
            "Translation validation failed %s candidate_len=%d error_type=%s",
            translation_ref(body.source, "en", body.native_lang),
            len(body.target),
            type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail="Translation validation failed")
