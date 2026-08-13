from pydantic import BaseModel, Field

from app.config import settings


class TextAnalysisRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=10,
        max_length=settings.MAX_EXTRACTED_TEXT_CHARS,
        description="Text to analyse",
    )
    title: str | None = Field(None, description="Optional custom title")


class ExcludedWords(BaseModel):
    proper_nouns: list[list] = Field(default_factory=list)  # [[word, count], ...]
    unknown: list[list] = Field(default_factory=list)


class TextAnalysisResponse(BaseModel):
    title: str
    words: list[list]  # [[word, count], ...]
    sentences: list[str]
    total_words: int
    total_unique_words: int
    total_sentences: int
    file_size: int | None = None
    filename: str | None = None
    excluded_words: ExcludedWords | None = None
    excluded_proper_noun_count: int | None = None
    excluded_unknown_count: int | None = None
    total_words_before_filter: int | None = None
    total_unique_words_before_filter: int | None = None
