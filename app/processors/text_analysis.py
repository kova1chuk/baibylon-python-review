"""Shared text-analysis logic extracted from BaseAnalysisView."""

import logging
from typing import Any, Optional

from app.config import settings
from app.models.text import ExcludedWords, TextAnalysisResponse
from app.services.nlp_utils import extract_words, count_word_frequency, tokenize_sentences
from app.services.word_classifier import ClassifiedWords, classify_sentences

logger = logging.getLogger(__name__)


def _as_pairs(frequency: dict[str, int]) -> list[list]:
    return [[w, c] for w, c in sorted(frequency.items(), key=lambda x: (-x[1], x[0]))]


def analyze_text(
    text: str,
    endpoint_type: str = "text",
    custom_title: Optional[str] = None,
    file_info: Optional[Any] = None,
    filename: Optional[str] = None,
) -> TextAnalysisResponse:
    """Analyse text and return a structured response."""
    logger.info("Starting text analysis for %s", endpoint_type)

    sentences = tokenize_sentences(text)
    total_sentences = len(sentences)

    classified: ClassifiedWords | None = None
    if settings.WORD_FILTER_ENABLED:
        classified = classify_sentences(sentences)
        word_frequency = classified.accepted
        total_words = sum(word_frequency.values())
    else:
        words = extract_words(text)
        word_frequency = count_word_frequency(words)
        total_words = len(words)

    # Determine title
    if custom_title:
        title = custom_title
    elif file_info and hasattr(file_info, "title") and file_info.title:
        title = file_info.title
    elif filename:
        title = filename.rsplit(".", 1)[0] if "." in filename else filename
    elif sentences:
        title = sentences[0][:100]
        if len(sentences[0]) > 100:
            title += "..."
    else:
        title = f"{endpoint_type.capitalize()} Text"

    response = TextAnalysisResponse(
        title=title,
        words=_as_pairs(word_frequency),
        sentences=sentences,
        total_words=total_words,
        total_unique_words=len(word_frequency),
        total_sentences=total_sentences,
    )

    if classified is not None:
        response.excluded_words = ExcludedWords(
            proper_nouns=_as_pairs(classified.proper_nouns),
            unknown=_as_pairs(classified.unknown),
        )
        response.excluded_proper_noun_count = len(classified.proper_nouns)
        response.excluded_unknown_count = len(classified.unknown)
        response.total_words_before_filter = classified.total_tokens
        response.total_unique_words_before_filter = (
            len(classified.accepted) + len(classified.proper_nouns) + len(classified.unknown)
        )

    # Add file info if available
    if file_info:
        if hasattr(file_info, "file_size"):
            response.file_size = file_info.file_size
        if hasattr(file_info, "filename"):
            response.filename = file_info.filename

    logger.info("Analysis completed: %d words, %d sentences", total_words, total_sentences)
    return response
