"""
Word validator: checks whether a token is a real English word.

Uses WordNet (dictionary lookup) and wordfreq (corpus frequency) together.
A word is accepted if WordNet has synsets for it OR wordfreq reports
a Zipf frequency >= MIN_ZIPF. Everything else is dropped as noise.
"""

import logging

import nltk
from nltk.corpus import wordnet as wn
from wordfreq import zipf_frequency

logger = logging.getLogger(__name__)

MIN_ZIPF = 2.0  # minimum Zipf frequency to accept without WordNet match

_nltk_ready = False


def _ensure_nltk():
    global _nltk_ready
    if _nltk_ready:
        return
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)
    _nltk_ready = True


def is_valid_english_word(word: str) -> bool:
    """Return True if *word* is a known English word."""
    _ensure_nltk()

    word = word.lower().strip()

    if not word or len(word) < 2:
        logger.debug("REJECT %-20s  reason=too_short", repr(word))
        return False

    in_wordnet = bool(wn.synsets(word))
    zipf = zipf_frequency(word, 'en')

    if in_wordnet:
        logger.debug("ACCEPT %-20s  wordnet=yes  zipf=%.2f", word, zipf)
        return True

    if zipf >= MIN_ZIPF:
        logger.debug("ACCEPT %-20s  wordnet=no   zipf=%.2f  (freq pass)", word, zipf)
        return True

    logger.debug("REJECT %-20s  wordnet=no   zipf=%.2f", word, zipf)
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
