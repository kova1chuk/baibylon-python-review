import json
import logging

from django.core.management.base import BaseCommand

from wf_parser.services.supabase_client import get_supabase_client
from wf_parser.services.word_enricher import enrich_word, enrich_all_words, _build_update_payload

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Enrich en_words with wordfreq + WordNet data'

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=100,
                            help='Number of rows per batch (default: 100)')
        parser.add_argument('--force', action='store_true',
                            help='Re-enrich words that already have enrichment data')
        parser.add_argument('--word', type=str, default=None,
                            help='Enrich a single word (prints result, updates DB)')

    def handle(self, *args, **options):
        supabase = get_supabase_client()

        if options['word']:
            self._enrich_single(supabase, options['word'])
        else:
            self._enrich_all(supabase, options['batch_size'], not options['force'])

    def _enrich_single(self, supabase, word_text: str):
        data = enrich_word(word_text)
        self.stdout.write(json.dumps(data, indent=2))

        # Try to update DB row if it exists
        rows = supabase.table('en_words').select('id, definition, synonymous, antonyms') \
            .eq('text', word_text).limit(1).execute()

        if rows.data:
            row = rows.data[0]
            update_payload = _build_update_payload(data, row)

            supabase.table('en_words').update(update_payload).eq('id', row['id']).execute()

            supabase.table('learning_item_metadata').update({
                'priority': data['suggested_priority'],
                'level': data['estimated_level'],
            }).eq('item_type', 'word').eq('item_id', row['id']).execute()

            self.stdout.write(self.style.SUCCESS(
                f'Updated en_words row id={row["id"]} for "{word_text}"'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'Word "{word_text}" not found in en_words — printed enrichment only'
            ))

    def _enrich_all(self, supabase, batch_size: int, skip_enriched: bool):
        self.stdout.write(f'Starting batch enrichment (batch_size={batch_size}, '
                          f'skip_enriched={skip_enriched})')
        result = enrich_all_words(supabase, batch_size=batch_size, skip_enriched=skip_enriched)
        self.stdout.write(self.style.SUCCESS(
            f'Done — enriched={result["enriched"]}, errors={result["errors"]}'
        ))
