from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from wf_parser.lib.base_analysis_view import BaseAnalysisView
from wf_parser.serializers import TextAnalysisRequestSerializer, TextAnalysisResponseSerializer
from .text_processor import TextProcessor


class TextAnalysisView(BaseAnalysisView):
    """
    Analyze simple text input for word and sentence statistics
    """
    parser_classes = [JSONParser]

    def get_processor(self):
        """Get the text processor instance."""
        return TextProcessor()

    def extract_text_from_request(self, request):
        """Extract text content and optional title from the request."""
        if 'text' not in request.data:
            raise ValueError('No text provided')

        text = request.data['text']
        title = request.data.get('title', '')  # Optional title parameter

        # Validate text input
        processor = self.get_processor()
        success, error_message, text_info = processor.process_text_input(text)

        if not success:
            raise ValueError(error_message)

        return text_info.cleaned_text, title

    def get_swagger_schema(self):
        """Get the Swagger schema for text analysis."""
        return {
            'operation_description': """
            Analyze simple text input for word and sentence statistics.
            
            This endpoint accepts plain text and returns:
            - List of sentences from the text
            - Unique words with usage counts
            - Statistics (total counts)
            - Extracted title (custom title or first sentence)
            
            The text is processed to:
            - Convert to lowercase
            - Filter for alphabetic words only
            - Remove extra whitespace
            
            You can optionally provide a custom title. If not provided, the first sentence will be used as the title.
            """,
            'operation_title': "Text Analysis API",
            'operation_summary': "Analyze simple text",
            'request_body': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                required=['text'],
                properties={
                    'text': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="The text to analyze"
                    ),
                    'title': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description="Optional title for the text (if not provided, first sentence will be used)"
                    )
                }
            ),
            'responses': self.get_standard_swagger_responses(),
            'tags': ['Text Analysis'],
            'operation_id': 'analyze_text'
        }

    @swagger_auto_schema(
        operation_description="""
        Analyze simple text input for word and sentence statistics.
        
        This endpoint accepts plain text and returns:
        - List of sentences from the text
        - Unique words with usage counts
        - Statistics (total counts)
        - Extracted title (custom title or first sentence)
        
        The text is processed to:
        - Convert to lowercase
        - Filter for alphabetic words only
        - Remove extra whitespace
        
        You can optionally provide a custom title. If not provided, the first sentence will be used as the title.
        """,
        operation_title="Text Analysis API",
        operation_summary="Analyze simple text",
        request_body=TextAnalysisRequestSerializer,
        responses={
            200: openapi.Response(
                description="Analysis completed successfully",
                schema=TextAnalysisResponseSerializer
            ),
            400: openapi.Response(
                description="Bad request - invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            500: openapi.Response(
                description="Internal server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        },
        tags=['Text Analysis'],
        operation_id='analyze_text'
    )
    def post(self, request):
        try:
            self.logger.info("Starting text analysis")

            # Extract text from request
            text, title = self.extract_text_from_request(request)
            self.logger.info(
                f"Successfully processed text input of {len(text)} characters")

            # Analyze text and return response
            return self.analyze_text(text, endpoint_type="text", custom_title=title)

        except ValueError as e:
            # Validation error
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Unexpected error
            return self.handle_unexpected_error(e, "text analysis")
