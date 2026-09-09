"""Extract vocabulary candidates; NestJS owns final dictionary admission."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config import settings
from app.services.lexical_evidence import named_entities
from app.services.nltk_resources import ensure_nltk_data
from app.services.word_validator import is_in_wordnet, is_valid_english_word

# Retain entire mixed tokens so an ordinal cannot turn into a learnable "th".
_TOKEN_RE = re.compile(r"\w+(?:['’ʼ-]\w+)*")


@dataclass
class ClassifiedWords:
    accepted: dict[str, int] = field(default_factory=dict)
    proper_nouns: dict[str, int] = field(default_factory=dict)
    unknown: dict[str, int] = field(default_factory=dict)
    total_tokens: int = 0


def classify_sentences(sentences: list[str]) -> ClassifiedWords:
    ensure_nltk_data()
    result = ClassifiedWords()
    for sentence in sentences:
        entities = named_entities(sentence)
        for match in _TOKEN_RE.finditer(sentence):
            token = match.group(0)
            if len(token) < settings.WORD_FILTER_MIN_WORD_LENGTH:
                continue
            word = token.lower().replace("’", "'").replace("ʼ", "'")
            result.total_tokens += 1
            entity = any(start < match.end() and end > match.start() for start, end, _ in entities)
            # NER can mislabel ordinary words at the start of a sentence. Keep
            # common/name ambiguities for NestJS, which has dictionary + context.
            if entity and not is_in_wordnet(word):
                bucket = result.proper_nouns
            elif is_valid_english_word(word):
                bucket = result.accepted
            else:
                bucket = result.unknown
            bucket[word] = bucket.get(word, 0) + 1
    return result
