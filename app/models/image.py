from pydantic import BaseModel


class OCRMetadata(BaseModel):
    language: str
    confidence: float
    engine: str
    processing_time: float
    accuracy_percentage: float
    valid_words: int
    invalid_words: int


class WordResult(BaseModel):
    text: str
    confidence: float = 0.0
    is_valid: bool = False
    suggestions: list[str] = []


class ImageAnalysisResponse(BaseModel):
    title: str
    words: list[list]
    sentences: list[str]
    total_words: int
    total_unique_words: int
    total_sentences: int
    ocr_metadata: OCRMetadata
