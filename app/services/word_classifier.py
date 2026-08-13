"""
Split tokens of a text into learnable vocabulary, proper nouns and unknown noise.

Capitalisation is the signal: a form that is written with a capital letter while
sitting in the middle of a sentence is almost always a name. That signal only
exists here, before the word list is lowercased and handed to consumers.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from app.config import settings
from app.services.word_validator import english_zipf, is_in_wordnet, is_valid_english_word

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z]+")

_SENTENCE_START_CHARS = frozenset("\"'“”‘’«»(){}[]<>—–-*_#|:;/\\.!?…&")

_DETERMINERS = frozenset(
    "a an the this that these those his her its their our your my no every each some any".split()
)

_FUNCTION_WORDS = frozenset(
    """
    a about above after again against all am an and any are as at be because been before being
    below between both but by can cannot could did do does doing down during each few for from
    further had has have having he her here hers herself him himself his how i if in into is it
    its itself just me more most my myself no nor not now of off on once only or other ought our
    ours ourselves out over own same she should so some such than that the their theirs them
    themselves then there these they this those through to too under until up very was we were
    what when where which while who whom why will with would you your yours yourself yourselves
    """.split()
)


@dataclass
class WordStats:
    total: int = 0
    capitalized: int = 0
    lowercase: int = 0

    @property
    def evidence(self) -> int:
        """Occurrences that carry a usable capitalisation signal."""
        return self.capitalized + self.lowercase


@dataclass
class ClassifiedWords:
    accepted: dict[str, int] = field(default_factory=dict)
    proper_nouns: dict[str, int] = field(default_factory=dict)
    unknown: dict[str, int] = field(default_factory=dict)
    total_tokens: int = 0


def _previous_significant_char(text: str, index: int) -> str:
    position = index - 1
    while position >= 0 and text[position].isspace():
        position -= 1
    return text[position] if position >= 0 else ""


def _is_digit_adjacent(text: str, match: re.Match) -> bool:
    """Ordinal tails such as the "th" of "16th" are not words."""
    before = text[match.start() - 1] if match.start() > 0 else ""
    after = text[match.end()] if match.end() < len(text) else ""
    return before.isdigit() or after.isdigit()


def _is_titlecased_line(tokens: list[str]) -> bool:
    considered = [t for t in tokens if len(t) >= settings.WORD_FILTER_MIN_WORD_LENGTH]
    if len(considered) < 3:
        return False
    capitalized = sum(1 for t in considered if t[0].isupper())
    return capitalized / len(considered) >= settings.WORD_FILTER_TITLECASE_SENTENCE_RATIO


def collect_word_stats(sentences: list[str]) -> tuple[dict[str, WordStats], int]:
    """Count occurrences and mid-sentence capitalisation for every normalised form."""
    stats: dict[str, WordStats] = {}
    total_tokens = 0
    min_length = settings.WORD_FILTER_MIN_WORD_LENGTH

    for sentence in sentences:
        matches = list(_TOKEN_RE.finditer(sentence))
        headline = _is_titlecased_line([m.group(0) for m in matches])

        for position, match in enumerate(matches):
            token = match.group(0)
            if len(token) < min_length or _is_digit_adjacent(sentence, match):
                continue

            normalised = token.lower()
            entry = stats.get(normalised)
            if entry is None:
                entry = stats[normalised] = WordStats()
            entry.total += 1
            total_tokens += 1

            if headline or token.isupper():
                continue

            previous = _previous_significant_char(sentence, match.start())
            if position == 0 or not previous or previous in _SENTENCE_START_CHARS:
                continue

            if not token[0].isupper():
                entry.lowercase += 1
                continue

            # "the Professor" is a title, not a name; a determiner makes the capital uninformative.
            if previous.isalpha() and matches[position - 1].group(0).lower() in _DETERMINERS:
                continue

            entry.capitalized += 1

    return stats, total_tokens


def _looks_like_proper_noun(word: str, stats: WordStats) -> bool:
    if word in _FUNCTION_WORDS:
        return False
    if english_zipf(word) >= settings.WORD_FILTER_PROPER_NOUN_MAX_ZIPF:
        return False

    min_occurrences = settings.WORD_FILTER_PROPER_NOUN_MIN_OCCURRENCES

    if (
        stats.evidence >= min_occurrences
        and stats.capitalized / stats.evidence >= settings.WORD_FILTER_PROPER_NOUN_RATIO
    ):
        return True

    # Names that only ever open sentences leave no mid-sentence evidence at all.
    return stats.lowercase == 0 and stats.total >= min_occurrences and not is_in_wordnet(word)


def classify_words(stats: dict[str, WordStats], total_tokens: int = 0) -> ClassifiedWords:
    result = ClassifiedWords(total_tokens=total_tokens)

    for word, entry in stats.items():
        if _looks_like_proper_noun(word, entry):
            result.proper_nouns[word] = entry.total
        elif is_valid_english_word(word):
            result.accepted[word] = entry.total
        else:
            result.unknown[word] = entry.total

    logger.info(
        "Word classification: %d accepted, %d proper nouns, %d unknown (of %d unique)",
        len(result.accepted),
        len(result.proper_nouns),
        len(result.unknown),
        len(stats),
    )
    return result


def classify_sentences(sentences: list[str]) -> ClassifiedWords:
    stats, total_tokens = collect_word_stats(sentences)
    return classify_words(stats, total_tokens)
