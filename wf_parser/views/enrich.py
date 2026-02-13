import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from wf_parser.services.supabase_client import get_supabase_client
from wf_parser.services.word_enricher import enrich_word, _build_update_payload

logger = logging.getLogger(__name__)


class EnrichWordView(APIView):
    """Enrich a single word with wordfreq + WordNet data and persist to Supabase."""

    @swagger_auto_schema(
        operation_description="Enrich a word with frequency and NLP data",
        operation_summary="Enrich word",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'word_id': openapi.Schema(type=openapi.TYPE_STRING,
                                          description="UUID of existing en_words row (optional)"),
                'text': openapi.Schema(type=openapi.TYPE_STRING,
                                       description="Word text to enrich"),
            },
            required=['text'],
        ),
        responses={
            200: openapi.Response(description="Enrichment result"),
            400: openapi.Response(description="Missing text field"),
            500: openapi.Response(description="Internal error"),
        },
        tags=['Enrichment'],
        operation_id='enrich_word',
    )
    def post(self, request):
        text = request.data.get('text')
        word_id = request.data.get('word_id')

        if not text:
            return Response({'success': False, 'error': 'text is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            data = enrich_word(text)
        except Exception:
            logger.exception("enrich_word failed for text=%s", text)
            return Response({'success': False, 'error': 'Enrichment failed'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Persist to Supabase if we can locate the row
        try:
            supabase = get_supabase_client()

            if word_id:
                rows = supabase.table('en_words').select('id, definition, synonymous, antonyms') \
                    .eq('id', word_id).limit(1).execute()
            else:
                rows = supabase.table('en_words').select('id, definition, synonymous, antonyms') \
                    .eq('text', text).limit(1).execute()

            if rows.data:
                row = rows.data[0]
                update_payload = _build_update_payload(data, row)

                supabase.table('en_words').update(update_payload).eq('id', row['id']).execute()

                supabase.table('learning_item_metadata').update({
                    'priority': data['suggested_priority'],
                    'level': data['estimated_level'],
                }).eq('item_type', 'word').eq('item_id', row['id']).execute()

                data['db_updated'] = True
            else:
                data['db_updated'] = False
        except ValueError:
            # Supabase not configured — return enrichment without DB update
            data['db_updated'] = False
        except Exception:
            logger.exception("DB update failed for text=%s", text)
            data['db_updated'] = False

        return Response({'success': True, 'data': data})
