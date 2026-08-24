import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from starlette.concurrency import run_in_threadpool

from app.dependencies import require_api_key
from app.models.text import TextAnalysisRequest, TextAnalysisResponse
from app.processors.text_processor import TextProcessor
from app.processors.epub_processor import EpubProcessor
from app.processors.subtitle_processor import SubtitleProcessor
from app.processors.text_analysis import analyze_text
from app.upload import read_bounded_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Text Analysis"], dependencies=[Depends(require_api_key)])

@router.post("/text", response_model=TextAnalysisResponse)
def analyze_plain_text(body: TextAnalysisRequest):
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

    content = await read_bounded_upload(file)
    return await run_in_threadpool(_analyze_upload, EpubProcessor(), content, file.filename, "epub")


@router.post("/subtitle", response_model=TextAnalysisResponse)
async def analyze_subtitle(file: UploadFile = File(...)):
    """Upload a subtitle file (SRT, VTT, TXT) for text analysis."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await read_bounded_upload(file)
    return await run_in_threadpool(
        _analyze_upload,
        SubtitleProcessor(),
        content,
        file.filename,
        "subtitle",
    )


def _analyze_upload(processor, content: bytes, filename: str, endpoint_type: str):
    result = processor.process_file(content, filename)
    if not result.success:
        status = 413 if "too large" in result.error_message.lower() else 400
        raise HTTPException(status_code=status, detail=result.error_message)

    return analyze_text(
        result.extracted_text,
        endpoint_type=endpoint_type,
        file_info=result.file_info,
        filename=filename,
    )
