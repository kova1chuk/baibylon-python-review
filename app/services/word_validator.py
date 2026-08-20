"""
Word validator: checks whether a token is a real English word.

Uses WordNet (dictionary lookup) and wordfreq (corpus frequency) together.
A word is accepted if WordNet has synsets for it OR wordfreq reports
a Zipf frequency >= WORD_FILTER_MIN_ZIPF. Everything else is dropped as noise.
"""

import logging
from hashlib import sha256

import nltk
from nltk.corpus import wordnet as wn
from wordfreq import zipf_frequency

from app.config import settings

logger = logging.getLogger(__name__)

_nltk_ready = False


def _ensure_nltk() -> None:
    global _nltk_ready
    if _nltk_ready:
        return
    nltk.download("wordnet", quiet=True)
    nltk.download("omw-1.4", quiet=True)
    _nltk_ready = True


def is_in_wordnet(word: str) -> bool:
    """Return True if WordNet knows *word*."""
    _ensure_nltk()
    return bool(wn.synsets(word.lower().strip()))


def english_zipf(word: str) -> float:
    """Return the wordfreq Zipf frequency of *word* in English."""
    return zipf_frequency(word.lower().strip(), "en")


def is_valid_english_word(word: str) -> bool:
    """Return True if *word* is a known English word."""
    _ensure_nltk()

    word = word.lower().strip()

    if not word or len(word) < settings.WORD_FILTER_MIN_WORD_LENGTH:
        logger.debug("REJECT %s reason=too_short", _word_ref(word))
        return False

    in_wordnet = bool(wn.synsets(word))
    zipf = zipf_frequency(word, "en")

    if in_wordnet:
        logger.debug("ACCEPT %s wordnet=yes zipf=%.2f", _word_ref(word), zipf)
        return True

    if zipf >= settings.WORD_FILTER_MIN_ZIPF:
        logger.debug("ACCEPT %s wordnet=no zipf=%.2f (freq pass)", _word_ref(word), zipf)
        return True

    logger.debug("REJECT %s wordnet=no zipf=%.2f", _word_ref(word), zipf)
    return False


def filter_valid_words(words: list[str]) -> list[str]:
    """Keep only words that pass the validity check."""
    _ensure_nltk()
    total = len(words)
    valid = [w for w in words if is_valid_english_word(w)]
    dropped = total - len(valid)
    if dropped:
        logger.info("Filtered words: %d/%d kept, %d dropped", len(valid), total, dropped)
    return valid


def _word_ref(word: str) -> str:
    digest = sha256(word.encode("utf-8")).hexdigest()[:12]
    return f"ref={digest} text_len={len(word)}"
