"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

# Swagger schema view
schema_view = get_schema_view(
    openapi.Info(
        title="Word Flow Text Analyzer API",
        default_version='v1',
        description="API for parsing EPUB files and extracting text analysis data",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@wordflow.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


class RootAPIView(APIView):
    """
    Root API endpoint that provides basic information about the API
    """
    
    @swagger_auto_schema(
        operation_description="Get API information and available endpoints",
        operation_summary="API Root",
        responses={
            200: openapi.Response(
                description="API information",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'name': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="API name"
                        ),
                        'version': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="API version"
                        ),
                        'description': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="API description"
                        ),
                        'endpoints': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description="Available API endpoints",
                            additional_properties=openapi.Schema(type=openapi.TYPE_STRING)
                        ),
                        'documentation': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Link to API documentation"
                        )
                    }
                ),
                examples={
                    "application/json": {
                        "name": "Word Flow Text Analyzer API",
                        "version": "v1.0.0",
                        "description": "API for parsing EPUB files and extracting text analysis data",
                        "endpoints": {
                            "health": "/api/health/",
                            "text": "/api/text/",
                            "subtitle": "/api/subtitle/",
                            "swagger": "/swagger/"
                        },
                        "documentation": "/swagger/"
                    }
                }
            )
        },
        tags=['API Info'],
        operation_id='api_root'
    )
    def get(self, request):
        return Response({
            'name': 'Word Flow Text Analyzer API',
            'version': 'v1.0.0',
            'description': 'API for parsing EPUB files and extracting text analysis data',
            'endpoints': {
                'health': '/api/health/',
                'upload': '/api/upload/',
                'text': '/api/text/',
                'subtitle': '/api/subtitle/',
                'swagger': '/swagger/',
                'redoc': '/redoc/',
                'admin': '/admin/'
            },
            'documentation': '/swagger/'
        })


def redirect_to_swagger(request):
    """Redirect root URL to Swagger documentation"""
    return redirect('/swagger/')


urlpatterns = [
    # Root URL - redirect to Swagger or provide API info
    path('', RootAPIView.as_view(), name='api_root'),

    path('admin/', admin.site.urls),
    # API root endpoint (without trailing slash)
    path('api', RootAPIView.as_view(), name='api_root_no_slash'),
    # API endpoints
    path('api/', include('wf_parser.urls')),

    # Swagger URLs
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger',
         cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc',
         cache_timeout=0), name='schema-redoc'),
]
