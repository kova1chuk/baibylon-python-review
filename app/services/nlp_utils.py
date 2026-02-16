import logging
import re

import nltk
from nltk.tokenize import sent_tokenize

from app.services.word_validator import filter_valid_words

logger = logging.getLogger(__name__)


def ensure_nltk_data() -> None:
    """Download required NLTK data packages."""
    for pkg in ("punkt", "punkt_tab", "wordnet", "omw-1.4"):
        try:
            nltk.download(pkg, quiet=True)
        except Exception as e:
            logger.warning("Could not download NLTK package %s: %s", pkg, e)
    logger.info("NLTK data ready")


def tokenize_sentences(text: str) -> list[str]:
    """Tokenize text into sentences with a regex fallback."""
    try:
        sentences = sent_tokenize(text)
    except Exception as exc:
        logger.warning("NLTK sentence tokenization failed: %s", exc)
        sentences = re.split(r"[.!?]+", text)

    return [s.strip() for s in sentences if s.strip()]


def extract_words(text: str) -> list[str]:
    """Extract valid English words from text."""
    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    return filter_valid_words(words)


def count_word_frequency(words: list[str]) -> dict[str, int]:
    """Count frequency of each word."""
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    return freq
