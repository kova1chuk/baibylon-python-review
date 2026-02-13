"""
Management command: delete invalid (non-English) words from en_words
and clean up linked rows in all referencing tables.

Delete order (before en_words):
  1. learning_item_metadata  (no FK cascade) → user_learning_states (CASCADE)
  2. en_dictionary_words     (FK CASCADE, but explicit for counting)
  3. en_to_uk_word_details   (FK, no cascade — must delete explicitly)
  4. en_reviews_words        (FK, no cascade — must delete explicitly)
  5. en_words
"""

import logging

from django.core.management.base import BaseCommand

from wf_parser.services.supabase_client import get_supabase_client
from wf_parser.services.word_validator import is_valid_english_word

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'Validate every word in en_words with WordNet + wordfreq. '
        'Delete invalid words and their linked rows from '
        'learning_item_metadata, en_dictionary_words, and user_learning_states.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Only log what would be deleted — do not touch the DB',
        )
        parser.add_argument(
            '--batch-size', type=int, default=500,
            help='Rows to fetch per page (default: 500)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        supabase = get_supabase_client()

        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN — no rows will be deleted ==='))

        offset = 0
        total_scanned = 0
        invalid_ids = []

        # ── 1. Scan en_words and collect invalid IDs ──────────────────────
        self.stdout.write('Scanning en_words …')

        while True:
            rows = (
                supabase.table('en_words')
                .select('id, text')
                .range(offset, offset + batch_size - 1)
                .execute()
            )

            if not rows.data:
                break

            for row in rows.data:
                total_scanned += 1
                word = row['text']
                if not is_valid_english_word(word):
                    invalid_ids.append(row['id'])
                    logger.info('INVALID  id=%s  text=%r', row['id'], word)
                    self.stdout.write(self.style.ERROR(
                        f'  INVALID  {word!r:25}  id={row["id"]}'
                    ))

            if len(rows.data) < batch_size:
                break
            offset += batch_size

        valid_count = total_scanned - len(invalid_ids)
        self.stdout.write(
            f'\nScanned {total_scanned} words: '
            f'{valid_count} valid, {len(invalid_ids)} invalid'
        )

        if not invalid_ids:
            self.stdout.write(self.style.SUCCESS('Nothing to delete.'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'DRY RUN complete — would delete {len(invalid_ids)} words'
            ))
            return

        # ── 2. Delete linked rows, then the words themselves ──────────────
        deleted_metadata = 0
        deleted_dict_words = 0
        deleted_uk_details = 0
        deleted_review_words = 0
        deleted_words = 0

        for word_id in invalid_ids:
            try:
                # 2a. learning_item_metadata (cascades → user_learning_states)
                res = (
                    supabase.table('learning_item_metadata')
                    .delete()
                    .eq('item_type', 'word')
                    .eq('item_id', word_id)
                    .execute()
                )
                n = len(res.data) if res.data else 0
                deleted_metadata += n
                if n:
                    logger.debug('Deleted %d learning_item_metadata for word %s', n, word_id)

                # 2b. en_dictionary_words
                res = (
                    supabase.table('en_dictionary_words')
                    .delete()
                    .eq('word_id', word_id)
                    .execute()
                )
                n = len(res.data) if res.data else 0
                deleted_dict_words += n
                if n:
                    logger.debug('Deleted %d en_dictionary_words for word %s', n, word_id)

                # 2c. en_to_uk_word_details (Ukrainian translations)
                res = (
                    supabase.table('en_to_uk_word_details')
                    .delete()
                    .eq('word_id', word_id)
                    .execute()
                )
                n = len(res.data) if res.data else 0
                deleted_uk_details += n
                if n:
                    logger.debug('Deleted %d en_to_uk_word_details for word %s', n, word_id)

                # 2d. en_reviews_words
                res = (
                    supabase.table('en_reviews_words')
                    .delete()
                    .eq('word_id', word_id)
                    .execute()
                )
                n = len(res.data) if res.data else 0
                deleted_review_words += n
                if n:
                    logger.debug('Deleted %d en_reviews_words for word %s', n, word_id)

                # 2e. en_words
                supabase.table('en_words').delete().eq('id', word_id).execute()
                deleted_words += 1
                logger.info('Deleted en_words id=%s', word_id)

            except Exception:
                logger.exception('Failed to delete word id=%s', word_id)
                self.stdout.write(self.style.ERROR(
                    f'  ERROR deleting id={word_id} — see logs'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'\nDone.\n'
            f'  en_words deleted:              {deleted_words}\n'
            f'  learning_item_metadata deleted: {deleted_metadata}\n'
            f'  en_dictionary_words deleted:    {deleted_dict_words}\n'
            f'  en_to_uk_word_details deleted:  {deleted_uk_details}\n'
            f'  en_reviews_words deleted:       {deleted_review_words}'
        ))
