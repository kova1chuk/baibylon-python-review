import logging
from hashlib import sha256

import nltk
import requests
from wordfreq import available_languages, zipf_frequency, top_n_list

from app.models.enrichment import WordNlpData, WordSense

logger = logging.getLogger(__name__)

_nltk_ready = False


def _ensure_nltk() -> None:
    global _nltk_ready
    if _nltk_ready:
        return
    nltk.download("wordnet", quiet=True)
    nltk.download("omw-1.4", quiet=True)
    _nltk_ready = True


_top_sets: dict[int, set[str]] = {}


def _get_top_set(n: int) -> set[str]:
    if n not in _top_sets:
        _top_sets[n] = set(top_n_list("en", n))
    return _top_sets[n]


def _zipf_to_level(zipf: float) -> str:
    if zipf >= 6:
        return "A1"
    if zipf >= 5:
        return "A2"
    if zipf >= 4:
        return "B1"
    if zipf >= 3:
        return "B2"
    if zipf >= 2:
        return "C1"
    return "C2"


def _zipf_to_priority(zipf: float) -> int:
    return min(100, max(1, int(zipf * 15)))


_POS_MAP: dict[str, str] = {
    "n": "n",
    "v": "v",
    "a": "a",
    "s": "a",
    "r": "r",
}


def fetch_phonetics(word: str) -> dict:
    """Fetch phonetic text + audio URL from Free Dictionary API."""
    try:
        resp = requests.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}",
            timeout=10,
        )
        if resp.status_code != 200:
            return {}

        data = resp.json()
        if not data or not isinstance(data, list):
            return {}

        entry = data[0]
        phonetic_text = entry.get("phonetic", "")
        phonetic_audio_link = ""

        for p in entry.get("phonetics", []):
            if not phonetic_text and p.get("text"):
                phonetic_text = p["text"]
            if not phonetic_audio_link and p.get("audio"):
                phonetic_audio_link = p["audio"]

        result = {}
        if phonetic_text:
            result["phonetic_text"] = phonetic_text
        if phonetic_audio_link:
            result["phonetic_audio_link"] = phonetic_audio_link
        return result
    except Exception as exc:
        logger.warning(
            "fetch_phonetics failed ref=%s text_len=%d error_type=%s",
            sha256(word.encode("utf-8")).hexdigest()[:12],
            len(word),
            type(exc).__name__,
        )
        return {}


def enrich_word(text: str) -> WordNlpData:
    """Build a full enrichment payload for a single English word."""
    _ensure_nltk()
    from nltk.corpus import wordnet as wn

    word = text.strip().lower()

    # wordfreq
    zipf = zipf_frequency(word, "en")
    is_top_1k = word in _get_top_set(1_000)
    is_top_5k = word in _get_top_set(5_000)
    is_top_10k = word in _get_top_set(10_000)
    is_top_50k = word in _get_top_set(50_000)

    # WordNet
    synsets = wn.synsets(word)

    pos_synsets: dict[str, list] = {}
    for ss in synsets:
        pos = _POS_MAP.get(ss.pos(), ss.pos())
        if pos not in pos_synsets:
            pos_synsets[pos] = []
        if len(pos_synsets[pos]) < 3:
            pos_synsets[pos].append(ss)

    senses: list[WordSense] = []
    all_synonyms: set[str] = set()
    all_antonyms: set[str] = set()
    all_hypernyms: set[str] = set()
    all_derived: set[str] = set()
    all_verb_frames: set[str] = set()
    all_examples: list[str] = []

    for pos, ss_list in pos_synsets.items():
        for ss in ss_list:
            sense_synonyms: list[str] = []
            for lemma in ss.lemmas():
                name = lemma.name().replace("_", " ")
                if name.lower() != word:
                    all_synonyms.add(name)
                    sense_synonyms.append(name)
                for ant in lemma.antonyms():
                    all_antonyms.add(ant.name().replace("_", " "))
                for df in lemma.derivationally_related_forms():
                    all_derived.add(df.name().replace("_", " "))

            for hyp in ss.hypernyms():
                for lemma in hyp.lemmas():
                    name = lemma.name().replace("_", " ")
                    if len(all_hypernyms) < 5:
                        all_hypernyms.add(name)

            if hasattr(ss, "frame_ids"):
                for fid in ss.frame_ids():
                    try:
                        all_verb_frames.add(ss.frame_text(fid))
                    except Exception:
                        pass

            sense_examples = ss.examples()
            all_examples.extend(sense_examples)

            senses.append(WordSense(
                pos=pos,
                definition=ss.definition(),
                examples=sense_examples,
                synonyms=sense_synonyms,
            ))

    derived_list = sorted(all_derived)[:10]

    best_def = ""
    if synsets:
        best_ss = max(
            synsets,
            key=lambda ss: max(
                (l.count() for l in ss.lemmas() if l.name().lower() == word),
                default=0,
            ),
        )
        best_def = best_ss.definition()
    primary_definition = best_def

    return WordNlpData(
        zipf_frequency=round(zipf, 2),
        is_top_1k=is_top_1k,
        is_top_5k=is_top_5k,
        is_top_10k=is_top_10k,
        is_top_50k=is_top_50k,
        pos_available=list(pos_synsets.keys()),
        senses=senses,
        synonyms=sorted(all_synonyms),
        antonyms=sorted(all_antonyms),
        hypernyms=sorted(all_hypernyms),
        derived_forms=derived_list,
        verb_frames=sorted(all_verb_frames),
        examples=all_examples,
        estimated_level=_zipf_to_level(zipf),
        suggested_priority=_zipf_to_priority(zipf),
        primary_definition=primary_definition,
    )


def batch_zipf_frequency(words: list[str], lang: str) -> tuple[bool, list[float | None]]:
    """Look up wordfreq Zipf frequency for many words in one call.

    Unlike `enrich_word`, this skips WordNet/synset work entirely — a
    words.zipf_frequency backfill only needs the number, not a full
    enrichment payload, and doing this in-process avoids per-word NLTK
    overhead. Returns (False, [None, ...]) for a language wordfreq has no
    data for, so the caller can leave those rows NULL instead of writing a
    fabricated value.
    """
    if lang not in available_languages():
        return False, [None for _ in words]
    return True, [round(zipf_frequency(w.strip().lower(), lang), 2) for w in words]
