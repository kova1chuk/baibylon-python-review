from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.parsers import MultiPartParser
from wf_parser.lib.base_analysis_view import BaseAnalysisView
from wf_parser.serializers import TextAnalysisResponseSerializer
from .epub_processor import EpubProcessor


class EpubAnalysisView(BaseAnalysisView):
    parser_classes = [MultiPartParser]

    def get_processor(self):
        """Get the EPUB processor instance."""
        return EpubProcessor()

    def extract_text_from_request(self, request):
        """Extract text content, file info, and filename from the request."""
        if 'file' not in request.FILES:
            raise ValueError('No file provided')

        epub_file = request.FILES['file']
        self.logger.info(
            f"Received file: {epub_file.name}, size: {epub_file.size} bytes")

        # Process EPUB file
        processor = self.get_processor()
        file_content = epub_file.read()
        result = processor.process_file(file_content, epub_file.name)

        if not result.success:
            raise ValueError(result.error_message)

        self.logger.info(
            f"Successfully extracted {len(result.extracted_text)} characters from EPUB file")
        return result.extracted_text, result.file_info, epub_file.name

    def get_swagger_schema(self):
        """Get the Swagger schema for EPUB analysis."""
        # Import here to avoid circular imports
        from wf_parser.serializers import EPubUploadSerializer
        
        return {
            'operation_description': """
            Upload an EPUB file for parsing and text analysis.
            
            This endpoint accepts an EPUB file and returns:
            - Full word list (all words from the book)
            - Unique word list (deduplicated words)
            - List of sentences from the book
            - Statistics (total counts)
            
            The text is processed to:
            - Remove HTML tags and formatting
            - Convert to lowercase
            - Filter for alphabetic words only
            - Remove extra whitespace
            """,
            'operation_summary': "Upload and parse EPUB file",
            'request_body': EPubUploadSerializer,
            'responses': self.get_standard_swagger_responses(),
            'tags': ['Text Analysis'],
            'operation_id': 'upload_epub'
        }

    @swagger_auto_schema(
        operation_description="""
        Upload an EPUB file for parsing and text analysis.
        
        This endpoint accepts an EPUB file and returns:
        - Full word list (all words from the book)
        - Unique word list (deduplicated words)
        - List of sentences from the book
        - Statistics (total counts)
        
        The text is processed to:
        - Remove HTML tags and formatting
        - Convert to lowercase
        - Filter for alphabetic words only
        - Remove extra whitespace
        """,
        operation_summary="Upload and parse EPUB file",
        manual_parameters=[
            openapi.Parameter(
                'file',
                openapi.IN_FORM,
                description="EPUB file to upload and analyze",
                type=openapi.TYPE_FILE,
                required=True
            )
        ],
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
        operation_id='upload_epub'
    )
    def post(self, request):
        try:
            self.logger.info("Starting EPUB upload processing")

            # Extract text from request
            text, file_info, filename = self.extract_text_from_request(request)

            # Analyze text and return response
            return self.analyze_text(text, endpoint_type="epub", file_info=file_info, filename=filename)

        except ValueError as e:
            # Validation error
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Unexpected error
            return self.handle_unexpected_error(e, "EPUB analysis")
