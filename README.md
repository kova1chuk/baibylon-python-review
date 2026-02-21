# Vocairo Text Analyzer

A FastAPI service for text analysis (EPUB, subtitles, plain text), word enrichment (WordNet + wordfreq), context-aware translation (DeepL), and OCR stubs.

## Features

- Analyse plain text, EPUB files, and subtitle files (SRT, VTT, TXT)
- Word enrichment with WordNet senses, frequency data, CEFR level estimation
- Context-aware translation via DeepL
- Supabase integration for persisting enriched word data
- Auto-generated OpenAPI docs (Swagger UI & ReDoc)

## Prerequisites

- Python 3.12+
- [Supabase](https://supabase.com/) project with service role key
- [DeepL API](https://www.deepl.com/pro-api) key (for translation)
- (Optional) Google Cloud credentials for OCR features
- (Optional) [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed locally for image processing

## Local Development

### 1. Clone the repository

```bash
git clone <repository-url>
cd vocairo_text_analyzer
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # macOS / Linux
# or on Windows:
# venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download NLTK data

The server downloads NLTK data automatically on startup, but you can pre-download it manually:

```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('wordnet'); nltk.download('omw-1.4')"
```

### 5. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your keys (see [Environment Variables](#environment-variables) below).

### 6. Run the server

```bash
uvicorn app.main:app --reload --port 8080
```

The server starts at `http://localhost:8080`.

### 7. Verify

```bash
curl http://localhost:8080/health
```

Expected response: `{"status": "ok"}`

## Docker

### Build the image

```bash
docker build -t vocairo-text-analyzer .
```

### Run the container

Pass environment variables directly:

```bash
docker run -d \
  --name vocairo-analyzer \
  -p 8080:8080 \
  -e SUPABASE_URL=https://your-project.supabase.co \
  -e SUPABASE_SERVICE_ROLE_KEY=your-service-role-key \
  -e DEEPL_API_KEY=your-deepl-key \
  -e CORS_ORIGINS=http://localhost:3000 \
  vocairo-text-analyzer
```

Or use an env file:

```bash
docker run -d \
  --name vocairo-analyzer \
  -p 8080:8080 \
  --env-file .env \
  vocairo-text-analyzer
```

### Verify the container

```bash
curl http://localhost:8080/health
```

### Stop and remove

```bash
docker stop vocairo-analyzer
docker rm vocairo-analyzer
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPABASE_URL` | Yes | — | Your Supabase project URL (`https://<ref>.supabase.co`) |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | — | Supabase service role key (has full DB access, keep secret) |
| `DEEPL_API_KEY` | Yes | — | DeepL API authentication key |
| `GOOGLE_CLOUD_CREDENTIALS_PATH` | No | — | Path to Google Cloud service account JSON (for OCR) |
| `CORS_ORIGINS` | No | `http://localhost:3000,http://127.0.0.1:3000,http://localhost:3006` | Comma-separated list of allowed CORS origins |
| `DEBUG` | No | `false` | Enable debug mode |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service info and version |
| GET | `/health` | Health check |
| POST | `/api/text` | Analyse plain text |
| POST | `/api/epub` | Upload & analyse EPUB |
| POST | `/api/subtitle` | Upload & analyse subtitle file |
| POST | `/api/enrich-word` | Enrich word with NLP data & persist to Supabase |
| GET | `/api/word/{word}/nlp` | Get NLP data for a word |
| POST | `/api/translate` | Translate text (DeepL, context-aware) |
| POST | `/api/image` | Image OCR (stub) |
| GET | `/api/image/health` | OCR health check (stub) |

### API Documentation

When the server is running, interactive docs are available at:

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

## Project Structure

```
vocairo_text_analyzer/
├── app/
│   ├── main.py              # FastAPI app, CORS, lifespan
│   ├── config.py            # Pydantic Settings (env vars)
│   ├── dependencies.py      # Shared deps (Supabase client)
│   ├── models/              # Pydantic request/response schemas
│   ├── routers/             # FastAPI routers
│   │   ├── health.py        #   /health
│   │   ├── text.py          #   /api/text, /api/epub, /api/subtitle
│   │   ├── enrichment.py    #   /api/enrich-word, /api/word/{word}/nlp
│   │   ├── translation.py   #   /api/translate
│   │   └── image.py         #   /api/image (stub)
│   ├── services/            # Business logic & NLP utils
│   └── processors/          # File processing (EPUB, subtitles)
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```
