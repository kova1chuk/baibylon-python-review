# API Documentation for Frontend Code Generation

## Overview

The API is fully documented with OpenAPI/Swagger specifications, making it ready for automatic frontend code generation using tools like:

- **OpenAPI Generator** (https://openapi-generator.tech/)
- **Swagger Codegen** (https://swagger.io/tools/swagger-codegen/)
- **TypeScript Axios** generators
- **React Query** code generators

## Accessing the Documentation

### Interactive Documentation

- **Swagger UI**: `http://localhost:8080/swagger/`
- **ReDoc**: `http://localhost:8080/redoc/`

### OpenAPI Schema

- **JSON Schema**: `http://localhost:8080/swagger.json`
- **YAML Schema**: `http://localhost:8080/swagger.yaml`

## API Endpoints

### Text Analysis

- **POST** `/api/text` - Analyze plain text input
  - Request: `TextAnalysisRequestSerializer`
  - Response: `TextAnalysisResponseSerializer`

### EPUB Analysis

- **POST** `/api/epub` - Upload and analyze EPUB file
  - Request: Multipart form with `file` field
  - Response: `TextAnalysisResponseSerializer`

### Subtitle Analysis

- **POST** `/api/subtitle` - Upload and analyze subtitle file
  - Request: Multipart form with `file` field
  - Response: `TextAnalysisResponseSerializer`

### Health Check

- **GET** `/api/health` - Check API health status

## Type Definitions

All request and response types are defined in `wf_parser/serializers.py`:

### Request Types

- `TextAnalysisRequestSerializer` - Text analysis request
- `EPubUploadSerializer` - EPUB file upload
- `SubtitleUploadSerializer` - Subtitle file upload
- `ImageAnalysisRequestSerializer` - Image analysis request

### Response Types

- `TextAnalysisResponseSerializer` - Standard text analysis response
- `ImageAnalysisResponseSerializer` - Image analysis response
- `WordDetailSerializer` - Individual word details

## Response Schema

All text analysis endpoints (`/api/text`, `/api/epub`, `/api/subtitle`) return the **same standardized response** using the `TextAnalysisResponse` type:

```typescript
interface TextAnalysisResponse {
  title: string;
  words: [string, number][]; // [word, count] pairs - Note: Schema shows string[][] but runtime returns numbers
  sentences: string[];
  total_words: number;
  total_unique_words: number;
  total_sentences: number;
  file_size?: number | null; // Optional, for file uploads
  filename?: string | null; // Optional, for file uploads
}
```

**Important Note on `words` field**: The OpenAPI schema may show `words: string[][]` due to DRF serializer limitations, but the actual API response returns `[string, number][]` where the second element is always a number (the frequency count). When generating TypeScript types, you may need to manually adjust the type to `[string, number][]` or use a type assertion.

## Error Responses

All endpoints return standardized error responses:

```typescript
interface ErrorResponse {
  error: string;
}
```

Status codes:

- `400` - Bad Request (validation errors)
- `500` - Internal Server Error

## Code Generation Examples

### Using OpenAPI Generator (TypeScript)

```bash
# Generate TypeScript client
npx @openapitools/openapi-generator-cli generate \
  -i http://localhost:8080/swagger.json \
  -g typescript-axios \
  -o ./src/api/generated
```

### Using Swagger Codegen

```bash
# Generate TypeScript client
swagger-codegen generate \
  -i http://localhost:8080/swagger.json \
  -l typescript-axios \
  -o ./src/api/generated
```

## Features

✅ **Fully Typed**: All endpoints have proper request/response type definitions
✅ **OpenAPI 3.0**: Compatible with all modern code generators
✅ **Swagger UI**: Interactive API documentation
✅ **ReDoc**: Beautiful API documentation
✅ **Schema Validation**: Request/response validation using DRF serializers
✅ **Error Handling**: Standardized error responses with proper types

## Notes

- All endpoints support CORS for `localhost:3000`
- The API uses JSON for text endpoints and multipart/form-data for file uploads
- All text analysis endpoints return the same response structure for consistency
