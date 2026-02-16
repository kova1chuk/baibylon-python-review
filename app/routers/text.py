import logging

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.models.text import TextAnalysisRequest, TextAnalysisResponse
from app.processors.text_processor import TextProcessor
from app.processors.epub_processor import EpubProcessor
from app.processors.subtitle_processor import SubtitleProcessor
from app.processors.text_analysis import analyze_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Text Analysis"])


@router.post("/text", response_model=TextAnalysisResponse)
async def analyze_plain_text(body: TextAnalysisRequest):
    """Analyse plain text input for word and sentence statistics."""
    processor = TextProcessor()
    success, error_message, text_info = processor.process_text_input(body.text)

    if not success:
        raise HTTPException(status_code=400, detail=error_message)

    return analyze_text(
        text_info.cleaned_text,
        endpoint_type="text",
        custom_title=body.title or None,
    )


@router.post("/epub", response_model=TextAnalysisResponse)
async def analyze_epub(file: UploadFile = File(...)):
    """Upload an EPUB file for parsing and text analysis."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()
    processor = EpubProcessor()
    result = processor.process_file(content, file.filename)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return analyze_text(
        result.extracted_text,
        endpoint_type="epub",
        file_info=result.file_info,
        filename=file.filename,
    )


@router.post("/subtitle", response_model=TextAnalysisResponse)
async def analyze_subtitle(file: UploadFile = File(...)):
    """Upload a subtitle file (SRT, VTT, TXT) for text analysis."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()
    processor = SubtitleProcessor()
    result = processor.process_file(content, file.filename)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return analyze_text(
        result.extracted_text,
        endpoint_type="subtitle",
        file_info=result.file_info,
        filename=file.filename,
    )
