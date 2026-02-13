# Updated: 2025-08-30 23:16 - Force rebuild to fix import issues
from django.urls import path
from wf_parser.views.health import HealthCheckView
from wf_parser.views.epub.epub_view import EpubAnalysisView
from wf_parser.views.test import TestView
from wf_parser.views.text.text_view import TextAnalysisView
from wf_parser.views.subtitle.subtitle_view import SubtitleAnalysisView
from wf_parser.views.image import ImageAnalysisView, ImageAnalysisHealthView
from wf_parser.views.batch_image import BatchImageAnalysisView, BatchImageAnalysisStatusView, BatchImageAnalysisResultsView
from wf_parser.views.enrich import EnrichWordView

urlpatterns = [
    path('epub', EpubAnalysisView.as_view(), name='upload_epub'),
    path('health', HealthCheckView.as_view(), name='health_check'),
    path('test', TestView.as_view(), name='test'),
    path('text', TextAnalysisView.as_view(), name='analyze_text'),
    path('subtitle', SubtitleAnalysisView.as_view(), name='analyze_subtitle'),
    path('image', ImageAnalysisView.as_view(), name='analyze_image'),
    path('image/health', ImageAnalysisHealthView.as_view(),
         name='image_health_check'),
    path('enrich-word', EnrichWordView.as_view(), name='enrich_word'),
    # Temporarily disabled to fix Swagger issues
    # path('image/batch', BatchImageAnalysisView.as_view(),
    #      name='batch_analyze_images'),
    # path('image/batch/status',
    #      name='batch_status'),
    # path('image/batch/results',
    #      name='batch_results'),
]
