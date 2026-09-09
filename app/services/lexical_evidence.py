from functools import lru_cache

import nltk
from nltk.corpus import wordnet
from nltk.tokenize import TreebankWordTokenizer
from wordfreq import available_languages, zipf_frequency

from app.services.nltk_resources import ensure_nltk_data


@lru_cache(maxsize=64)
def named_entities(context: str) -> tuple[tuple[int, int, str], ...]:
    spans = list(TreebankWordTokenizer().span_tokenize(context))
    tagged = nltk.pos_tag([context[start:end] for start, end in spans])
    tree = nltk.ne_chunk(tagged)
    entities = []
    index = 0
    for node in tree:
        if isinstance(node, nltk.Tree):
            count = len(node.leaves())
            if any(pos.startswith("NNP") for _, pos in node.leaves()):
                entities.append((spans[index][0], spans[index + count - 1][1], node.label()))
            index += count
        else:
            index += 1
    return tuple(entities)


def lexical_evidence(text: str, language: str, context=None) -> dict:
    ensure_nltk_data()
    normalized = text.replace("’", "'").strip().lower()
    lemmas = set()
    if language == "en":
        for pos in (wordnet.NOUN, wordnet.VERB, wordnet.ADJ, wordnet.ADV):
            # morphy() returns only the first result; retain ambiguity such as axes.
            for lemma in wordnet._morphy(normalized, pos):
                if lemma != normalized:
                    lemmas.add(lemma.replace("_", " "))
    entity = None
    if language == "en" and context is not None:
        entity = next((label for start, end, label in named_entities(context.text)
                       if start < context.end and end > context.start), None)
    return {
        "lemma_candidates": sorted(lemmas),
        "zipf_frequency": round(zipf_frequency(normalized, language), 2)
        if language in available_languages() else None,
        "named_entity": entity,
    }
