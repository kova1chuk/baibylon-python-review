import logging

import nltk
from wordfreq import zipf_frequency, top_n_list

logger = logging.getLogger(__name__)

# NLTK data download (once)
_nltk_ready = False


def _ensure_nltk():
    global _nltk_ready
    if _nltk_ready:
        return
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)
    _nltk_ready = True


# Pre-compute top-N word sets for fast lookup
_top_sets = {}


def _get_top_set(n: int) -> set:
    if n not in _top_sets:
        _top_sets[n] = set(top_n_list('en', n))
    return _top_sets[n]


# Zipf -> CEFR mapping
def _zipf_to_level(zipf: float) -> str:
    if zipf >= 6:
        return 'A1'
    if zipf >= 5:
        return 'A2'
    if zipf >= 4:
        return 'B1'
    if zipf >= 3:
        return 'B2'
    if zipf >= 2:
        return 'C1'
    return 'C2'


def _zipf_to_priority(zipf: float) -> int:
    return min(100, max(1, int(zipf * 15)))


# WordNet POS tag to short label (string literals to avoid loading wn at import time)
_POS_MAP = {
    'n': 'n',
    'v': 'v',
    'a': 'a',
    's': 'a',  # adjective satellite -> adjective
    'r': 'r',
}


def enrich_word(text: str) -> dict:
    """Build a full enrichment dict for a single English word."""
    _ensure_nltk()
    from nltk.corpus import wordnet as wn

    word = text.strip().lower()

    # --- wordfreq ---
    zipf = zipf_frequency(word, 'en')
    is_top_1k = word in _get_top_set(1000)
    is_top_5k = word in _get_top_set(5000)
    is_top_10k = word in _get_top_set(10000)
    is_top_50k = word in _get_top_set(50000)

    # --- WordNet ---
    synsets = wn.synsets(word)

    # Group synsets by POS, take top 3 per POS
    pos_synsets: dict[str, list] = {}
    for ss in synsets:
        pos = _POS_MAP.get(ss.pos(), ss.pos())
        if pos not in pos_synsets:
            pos_synsets[pos] = []
        if len(pos_synsets[pos]) < 3:
            pos_synsets[pos].append(ss)

    senses = []
    all_synonyms = set()
    all_antonyms = set()
    all_hypernyms = set()
    all_derived = set()
    all_verb_frames = set()
    all_examples = []

    for pos, ss_list in pos_synsets.items():
        for ss in ss_list:
            # Synonyms from lemmas
            sense_synonyms = []
            for lemma in ss.lemmas():
                name = lemma.name().replace('_', ' ')
                if name.lower() != word:
                    all_synonyms.add(name)
                    sense_synonyms.append(name)
                # Antonyms
                for ant in lemma.antonyms():
                    all_antonyms.add(ant.name().replace('_', ' '))
                # Derived forms
                for df in lemma.derivationally_related_forms():
                    all_derived.add(df.name().replace('_', ' '))

            # Hypernyms (max 5 total)
            for hyp in ss.hypernyms():
                for lemma in hyp.lemmas():
                    name = lemma.name().replace('_', ' ')
                    if len(all_hypernyms) < 5:
                        all_hypernyms.add(name)

            # Verb frames
            if hasattr(ss, 'frame_ids'):
                for fid in ss.frame_ids():
                    try:
                        all_verb_frames.add(ss.frame_text(fid))
                    except Exception:
                        pass

            # Examples
            sense_examples = ss.examples()
            all_examples.extend(sense_examples)

            senses.append({
                'pos': pos,
                'definition': ss.definition(),
                'examples': sense_examples,
                'synonyms': sense_synonyms,
            })

    # Limit derived forms
    derived_list = sorted(all_derived)[:10]

    # Primary definition = first sense if available
    primary_definition = senses[0]['definition'] if senses else ''

    return {
        # wordfreq
        'zipf_frequency': round(zipf, 2),
        'is_top_1k': is_top_1k,
        'is_top_5k': is_top_5k,
        'is_top_10k': is_top_10k,
        'is_top_50k': is_top_50k,
        # WordNet
        'pos_available': list(pos_synsets.keys()),
        'senses': senses,
        'synonyms': sorted(all_synonyms),
        'antonyms': sorted(all_antonyms),
        'hypernyms': sorted(all_hypernyms),
        'derived_forms': derived_list,
        'verb_frames': sorted(all_verb_frames),
        'examples': all_examples,
        # Derived
        'estimated_level': _zipf_to_level(zipf),
        'suggested_priority': _zipf_to_priority(zipf),
        'primary_definition': primary_definition,
    }


def _build_update_payload(data: dict, row: dict) -> dict:
    """Build a Supabase update payload from enrichment data, writing each column individually."""
    payload = {
        'zipf_frequency': data['zipf_frequency'],
        'is_top_1k': data['is_top_1k'],
        'is_top_5k': data['is_top_5k'],
        'is_top_10k': data['is_top_10k'],
        'is_top_50k': data['is_top_50k'],
        'pos_available': data['pos_available'],
        'senses': data['senses'],
        'synonyms': data['synonyms'],
        'hypernyms': data['hypernyms'],
        'derived_forms': data['derived_forms'],
        'verb_frames': data['verb_frames'],
        'examples': data['examples'],
        'estimated_level': data['estimated_level'],
        'suggested_priority': data['suggested_priority'],
        'primary_definition': data['primary_definition'],
    }

    # Back-fill legacy columns only if currently empty
    if not row.get('definition') and data['primary_definition']:
        payload['definition'] = data['primary_definition']
    if not row.get('synonymous') and data['synonyms']:
        payload['synonymous'] = ', '.join(data['synonyms'][:10])
    if not row.get('antonyms') and data['antonyms']:
        payload['antonyms'] = ', '.join(data['antonyms'][:10])

    return payload


def enrich_all_words(supabase, batch_size: int = 100, skip_enriched: bool = True):
    """Paginate through en_words and enrich each one."""
    offset = 0
    total_enriched = 0
    total_errors = 0

    while True:
        query = supabase.table('en_words').select(
            'id, text, definition, synonymous, antonyms, zipf_frequency'
        )
        if skip_enriched:
            query = query.is_('zipf_frequency', 'null')
        rows = query.range(offset, offset + batch_size - 1).execute()

        if not rows.data:
            break

        for row in rows.data:
            try:
                data = enrich_word(row['text'])
                update_payload = _build_update_payload(data, row)

                supabase.table('en_words').update(update_payload).eq('id', row['id']).execute()

                # Update learning_item_metadata
                supabase.table('learning_item_metadata').update({
                    'priority': data['suggested_priority'],
                    'level': data['estimated_level'],
                }).eq('item_type', 'word').eq('item_id', row['id']).execute()

                total_enriched += 1
                logger.info("Enriched word: %s (zipf=%.2f, level=%s)",
                            row['text'], data['zipf_frequency'], data['estimated_level'])
            except Exception:
                total_errors += 1
                logger.exception("Failed to enrich word id=%s text=%s", row['id'], row['text'])

        # If we got fewer rows than batch_size, we're done
        if len(rows.data) < batch_size:
            break
        offset += batch_size

    return {'enriched': total_enriched, 'errors': total_errors}
