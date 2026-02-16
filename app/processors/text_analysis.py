"""Shared text-analysis logic extracted from BaseAnalysisView."""

import logging
from typing import Any, Optional

from app.models.text import TextAnalysisResponse
from app.services.nlp_utils import extract_words, count_word_frequency, tokenize_sentences

logger = logging.getLogger(__name__)


def analyze_text(
    text: str,
    endpoint_type: str = "text",
    custom_title: Optional[str] = None,
    file_info: Optional[Any] = None,
    filename: Optional[str] = None,
) -> TextAnalysisResponse:
    """Analyse text and return a structured response."""
    logger.info("Starting text analysis for %s", endpoint_type)

    words = extract_words(text)
    total_words = len(words)

    word_frequency = count_word_frequency(words)

    word_list = sorted(
        word_frequency.items(),
        key=lambda x: (-x[1], x[0]),
    )

    sentences = tokenize_sentences(text)
    total_sentences = len(sentences)

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
        words=[[w, c] for w, c in word_list],
        sentences=sentences,
        total_words=total_words,
        total_unique_words=len(word_frequency),
        total_sentences=total_sentences,
    )

    # Add file info if available
    if file_info:
        if hasattr(file_info, "file_size"):
            response.file_size = file_info.file_size
        if hasattr(file_info, "filename"):
            response.filename = file_info.filename

    logger.info("Analysis completed: %d words, %d sentences", total_words, total_sentences)
    return response
