import logging
import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.dependencies import require_api_key
from app.models.image import ImageAnalysisResponse, OCRMetadata
from app.processors.image_processor import ImageProcessor, OCREngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Image"], dependencies=[Depends(require_api_key)])

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/bmp",
    "image/tiff",
}


@router.post("/image", response_model=ImageAnalysisResponse)
async def analyze_image(
    image: UploadFile = File(...),
    engine: str | None = Form(None),
    preprocess: bool = Form(True),
    validate_words: bool = Form(True),
):
    """Process an uploaded image with OCR (stub implementation)."""
    if image.content_type and image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )

    ocr_engine = None
    if engine:
        try:
            ocr_engine = OCREngine(engine.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid OCR engine. Available: {[e.value for e in OCREngine]}",
            )

    suffix = os.path.splitext(image.filename or "img")[1] or ".png"
    content = await image.read()
    return await run_in_threadpool(
        _process_image_content,
        content,
        suffix,
        ocr_engine,
        preprocess,
        validate_words,
    )


def _process_image_content(
    content: bytes,
    suffix: str,
    ocr_engine: OCREngine | None,
    preprocess: bool,
    validate_words: bool,
) -> ImageAnalysisResponse:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        temp_path = tmp.name

    try:
        processor = ImageProcessor(
            preferred_engine=ocr_engine,
            google_credentials_path=settings.GOOGLE_CLOUD_CREDENTIALS_PATH or None,
        )
        result = processor.process_image(
            image_path=temp_path,
            engine=ocr_engine,
            preprocess=preprocess,
            validate_words=validate_words,
        )
        summary = processor.get_processing_summary(result)

        engine_label = ocr_engine.value if ocr_engine else result.engine
        return ImageAnalysisResponse(
            title=f"Image Text - {engine_label.upper()} OCR",
            words=[[w.text, 1] for w in result.words if w.text.strip()],
            sentences=[result.text] if result.text.strip() else [],
            total_words=len([w for w in result.words if w.text.strip()]),
            total_unique_words=len({w.text.lower() for w in result.words if w.text.strip()}),
            total_sentences=1 if result.text.strip() else 0,
            ocr_metadata=OCRMetadata(
                language=result.language,
                confidence=result.confidence,
                engine=result.engine,
                processing_time=result.processing_time,
                accuracy_percentage=summary["accuracy_percentage"],
                valid_words=summary["valid_words"],
                invalid_words=summary["invalid_words"],
            ),
        )
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            logger.warning("Could not delete temporary file: %s", temp_path)


@router.get("/image/health")
async def image_health():
    """Health check for image analysis services (stub)."""
    return {
        "success": True,
        "data": {
            "available_engines": [e.value for e in OCREngine],
            "tesseract_available": True,
            "google_vision_available": True,
            "basic_functionality": True,
        },
    }
