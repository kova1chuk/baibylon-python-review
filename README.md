# Vocairo Text Analyzer

A FastAPI service for text analysis (EPUB, subtitles, plain text), word enrichment (WordNet + wordfreq), context-aware translation (DeepL), and OCR stubs.

## Features

- Analyse plain text, EPUB files, and subtitle files (SRT, VTT, TXT)
- Word enrichment with WordNet senses, frequency data, CEFR level estimation
- Context-aware translation via DeepL
- Auto-generated OpenAPI docs (Swagger UI & ReDoc)

## Local Development

### Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
```

### Run

```bash
uvicorn app.main:app --reload --port 8080
```

### API Documentation

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/text` | Analyse plain text |
| POST | `/api/epub` | Upload & analyse EPUB |
| POST | `/api/subtitle` | Upload & analyse subtitle file |
| POST | `/api/enrich-word` | Enrich word with NLP data & persist to Supabase |
| GET | `/api/word/{word}/nlp` | Get NLP data for a word |
| POST | `/api/translate` | Translate text (DeepL, context-aware) |
| POST | `/api/image` | Image OCR (stub) |
| GET | `/api/image/health` | OCR health check (stub) |

## Environment Variables

See `.env.example` for the full list.

## Project Structure

```
vocairo_text_analyzer/
├── app/
│   ├── main.py              # FastAPI app, CORS, lifespan
│   ├── config.py            # Pydantic Settings
│   ├── dependencies.py      # Shared deps (Supabase client)
│   ├── models/              # Pydantic request/response schemas
│   ├── routers/             # FastAPI routers (endpoints)
│   ├── services/            # Business logic
│   └── processors/          # File processing
├── requirements.txt
├── .env.example
└── README.md
```
