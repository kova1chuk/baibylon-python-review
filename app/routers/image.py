from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.dependencies import require_api_key

router = APIRouter(prefix="/api", tags=["Image"], dependencies=[Depends(require_api_key)])

OCR_UNAVAILABLE_DETAIL = "OCR is not available in this deployment"


@router.post(
    "/image",
    status_code=503,
    responses={503: {"description": OCR_UNAVAILABLE_DETAIL}},
)
async def analyze_image(
    image: UploadFile = File(...),
    engine: str | None = Form(None),
    preprocess: bool = Form(True),
    validate_words: bool = Form(True),
):
    """Reject image analysis until a real OCR adapter is configured."""
    raise HTTPException(status_code=503, detail=OCR_UNAVAILABLE_DETAIL)


@router.get(
    "/image/health",
    status_code=503,
    responses={503: {"description": OCR_UNAVAILABLE_DETAIL}},
)
async def image_health():
    """Report the actual OCR capability instead of advertising stub engines."""
    raise HTTPException(
        status_code=503,
        detail={
            "message": OCR_UNAVAILABLE_DETAIL,
            "available_engines": [],
            "tesseract_available": False,
            "google_vision_available": False,
            "basic_functionality": False,
        },
    )
