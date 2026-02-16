from pydantic import BaseModel, Field


class TextAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Text to analyse")
    title: str | None = Field(None, description="Optional custom title")


class TextAnalysisResponse(BaseModel):
    title: str
    words: list[list]  # [[word, count], ...]
    sentences: list[str]
    total_words: int
    total_unique_words: int
    total_sentences: int
    file_size: int | None = None
    filename: str | None = None
