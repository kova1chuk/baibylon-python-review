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
ANALYZER_API_KEY=
DEEPL_API_KEY=
GOOGLE_CLOUD_CREDENTIALS_PATH=
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3006
DEBUG=false
```

Google credentials are optional and only needed for OCR flows that use Google
Cloud. Keep credentials out of git.

## Word Filtering

Text analysis splits every token into three buckets so that names and noise
never reach a learner's dictionary. Only `accepted` words are returned in
`words`; the rest come back in `excluded_words` so consumers can report them.

| Bucket | Rule |
|---|---|
| `accepted` | Known to WordNet, or wordfreq Zipf >= `WORD_FILTER_MIN_ZIPF` |
| `proper_nouns` | Capitalised mid-sentence in >= `WORD_FILTER_PROPER_NOUN_RATIO` of its informative occurrences (min `WORD_FILTER_PROPER_NOUN_MIN_OCCURRENCES`), or never seen lowercase and absent from WordNet |
| `unknown` | Fails the lexical check above |

Sentence-initial words, all-caps tokens, title-cased headings (`WORD_FILTER_TITLECASE_SENTENCE_RATIO`),
determiner-preceded titles ("the Professor"), function words and words above
`WORD_FILTER_PROPER_NOUN_MAX_ZIPF` are never treated as proper nouns.

```env
WORD_FILTER_ENABLED=true
WORD_FILTER_MIN_WORD_LENGTH=2
WORD_FILTER_MIN_ZIPF=2.0
WORD_FILTER_PROPER_NOUN_RATIO=0.8
WORD_FILTER_PROPER_NOUN_MIN_OCCURRENCES=2
WORD_FILTER_PROPER_NOUN_MAX_ZIPF=6.0
WORD_FILTER_TITLECASE_SENTENCE_RATIO=0.7
```

`WORD_FILTER_ENABLED=false` restores the previous behaviour (lexical filter
only, no `excluded_words` in the response).

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
| `POST` | `/api/enrich-word` | Fetch word NLP data (legacy-compatible request shape) |
| `GET` | `/api/word/{word}/nlp` | Fetch NLP data for a word |
| `GET` | `/api/word/{word}/phonetics` | Fetch phonetic text and audio |
| `POST` | `/api/translate` | Translate text |
| `POST` | `/api/image` | OCR image analysis |
| `GET` | `/api/image/health` | OCR health check |

The analyzer is stateless. Database persistence and batch enrichment are owned
by the NestJS API, which calls these analysis endpoints and writes through
Kysely (`POST /admin/words/{id}/reload` and
`POST /admin/words/batch-enrich`).

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
