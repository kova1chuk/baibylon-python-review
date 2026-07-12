# Vocairo Text Analyzer

FastAPI service for plain-text, EPUB, subtitle, word-enrichment, translation,
and OCR analysis. It is consumed by the NestJS backend and runs locally on port
8080.

## Local Development

```bash
cd /Users/oleks/Work/Vocairo/vocairo_text_analyzer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Verify:

```bash
curl http://localhost:8080/health
```

Interactive docs:

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

## Environment

```env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
ANALYZER_API_KEY=
DEEPL_API_KEY=
GOOGLE_CLOUD_CREDENTIALS_PATH=
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3006
DEBUG=false
```

Google credentials are optional and only needed for OCR flows that use Google
Cloud. Keep credentials out of git.

`ANALYZER_API_KEY` is required for every `/api/*` route. Send it in the
`X-API-Key` header; `/health` remains public:

```bash
curl -X POST http://localhost:8080/api/text \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ANALYZER_API_KEY" \
  -d '{"text":"This sentence is long enough to analyze."}'
```

## Docker

```bash
docker build -t vocairo-text-analyzer .
docker run --rm -p 8080:8080 --env-file .env vocairo-text-analyzer
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/text` | Analyze plain text |
| `POST` | `/api/epub` | Analyze EPUB files |
| `POST` | `/api/subtitle` | Analyze subtitle files |
| `POST` | `/api/enrich-word` | Enrich and persist word NLP data |
| `GET` | `/api/word/{word}/nlp` | Fetch NLP data for a word |
| `POST` | `/api/translate` | Translate text |
| `POST` | `/api/image` | OCR image analysis |
| `GET` | `/api/image/health` | OCR health check |

## Structure

```text
app/
  main.py
  config.py
  dependencies.py
  models/
  processors/
  routers/
  services/
```
