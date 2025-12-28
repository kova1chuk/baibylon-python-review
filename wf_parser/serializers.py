from rest_framework import serializers
from wf_parser.models import ImageAnalysisResult, ImageAnalysisSession


# ============================================================================
# Text Analysis Request/Response Serializers
# ============================================================================

class TextAnalysisRequestSerializer(serializers.Serializer):
    """Serializer for text analysis requests"""
    text = serializers.CharField(
        required=True,
        help_text="The text to analyze (minimum 10 characters)",
        min_length=10
    )
    title = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional title for the text (if not provided, first sentence will be used)"
    )


class WordFrequencySerializer(serializers.Serializer):
    """Serializer for word frequency data"""
    word = serializers.CharField(help_text="The word")
    count = serializers.IntegerField(help_text="Frequency count of the word")


class TextAnalysisResponseSerializer(serializers.Serializer):
    """Serializer for text analysis responses"""
    title = serializers.CharField(help_text="Title of the analyzed text")
    words = serializers.ListField(
        child=serializers.ListField(
            child=serializers.CharField(),
            min_length=2,
            max_length=2
        ),
        help_text="List of [word, count] pairs sorted by frequency. Format: [[word1, count1], [word2, count2], ...] where count is a number representing frequency. Note: In the actual API response, the count is a number, but the OpenAPI schema represents it as string for compatibility."
    )
    sentences = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of sentences extracted from the text"
    )
    total_words = serializers.IntegerField(help_text="Total number of words")
    total_unique_words = serializers.IntegerField(help_text="Total number of unique words")
    total_sentences = serializers.IntegerField(help_text="Total number of sentences")
    file_size = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="File size in bytes (if applicable)"
    )
    filename = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Original filename (if applicable)"
    )


class EPubUploadSerializer(serializers.Serializer):
    """Serializer for the EPUB file upload."""
    file = serializers.FileField(
        help_text="The .epub file to be processed."
    )

    class Meta:
        fields = ('file',)


class SubtitleUploadSerializer(serializers.Serializer):
    """Serializer for subtitle file uploads (SRT, VTT, TXT)."""
    file = serializers.FileField(
        help_text="The subtitle file to analyze (SRT, VTT, TXT)"
    )

    class Meta:
        fields = ('file',)


class WordDetailSerializer(serializers.Serializer):
    """Serializer for individual word details"""
    text = serializers.CharField()
    confidence = serializers.FloatField()
    bounding_box = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_null=True
    )
    is_valid = serializers.BooleanField(allow_null=True)
    suggestions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True
    )
    language = serializers.CharField(required=False, allow_null=True)


class ImageAnalysisResultSerializer(serializers.ModelSerializer):
    """Serializer for ImageAnalysisResult model"""
    word_details = WordDetailSerializer(many=True, read_only=True)
    success_rate = serializers.ReadOnlyField()

    class Meta:
        model = ImageAnalysisResult
        fields = [
            'id', 'image_name', 'image_size', 'content_type',
            'extracted_text', 'detected_language', 'confidence_score',
            'ocr_engine', 'processing_time', 'total_words', 'valid_words',
            'invalid_words', 'accuracy_percentage', 'word_details',
            'created_at', 'updated_at', 'success_rate'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'success_rate'
        ]


class ImageAnalysisResultSummarySerializer(serializers.ModelSerializer):
    """Simplified serializer for listing results"""
    success_rate = serializers.ReadOnlyField()

    class Meta:
        model = ImageAnalysisResult
        fields = [
            'id', 'image_name', 'detected_language', 'confidence_score',
            'ocr_engine', 'accuracy_percentage', 'total_words',
            'created_at', 'success_rate'
        ]


class ImageAnalysisSessionSerializer(serializers.ModelSerializer):
    """Serializer for ImageAnalysisSession model"""
    session_summary = serializers.SerializerMethodField()

    class Meta:
        model = ImageAnalysisSession
        fields = [
            'id', 'session_id', 'started_at', 'completed_at', 'status',
            'total_images', 'processed_images', 'successful_images',
            'failed_images', 'ocr_engine', 'preprocess_enabled',
            'word_validation_enabled', 'overall_accuracy',
            'average_processing_time', 'session_summary'
        ]
        read_only_fields = [
            'id', 'started_at', 'completed_at', 'overall_accuracy',
            'average_processing_time', 'session_summary'
        ]

    def get_session_summary(self, obj):
        """Get session summary data"""
        return obj.get_session_summary()


class ImageAnalysisRequestSerializer(serializers.Serializer):
    """Serializer for image analysis requests"""
    image = serializers.FileField()
    engine = serializers.ChoiceField(
        choices=[('tesseract', 'Tesseract OCR'), ('google_vision',
                                                  'Google Cloud Vision')],  # Removed Azure and AWS
        default='google_vision',  # Default to Google Vision
        required=False
    )
    preprocess = serializers.BooleanField(default=True, required=False)
    validate_words = serializers.BooleanField(default=True, required=False)
    export_format = serializers.ChoiceField(
        choices=['json', 'txt'],
        default='json',
        required=False
    )


class BatchImageAnalysisRequestSerializer(serializers.Serializer):
    """Serializer for batch image analysis requests"""
    images = serializers.ListField(
        child=serializers.FileField(),
        min_length=1,
        max_length=100
    )
    engine = serializers.ChoiceField(
        choices=[('tesseract', 'Tesseract OCR'), ('google_vision',
                                                  'Google Cloud Vision')],  # Removed Azure and AWS
        default='google_vision',  # Default to Google Vision
        required=False
    )
    preprocess = serializers.BooleanField(default=True, required=False)
    validate_words = serializers.BooleanField(default=True, required=False)
    session_name = serializers.CharField(max_length=255, required=False)


class ImageAnalysisResponseSerializer(serializers.Serializer):
    """Serializer for image analysis responses"""
    success = serializers.BooleanField()
    data = serializers.DictField()
    error = serializers.CharField(required=False, allow_null=True)


class ImageAnalysisHealthSerializer(serializers.Serializer):
    """Serializer for image analysis health check responses"""
    success = serializers.BooleanField()
    data = serializers.DictField()
    error = serializers.CharField(required=False, allow_null=True)
