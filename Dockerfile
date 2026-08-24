FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a AS runner

WORKDIR /app
RUN addgroup --system --gid 1001 appuser && adduser --system --uid 1001 --gid 1001 appuser

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY app/ app/
COPY static/ static/

ADD --checksum=sha256:51c3078994aeaf650bfc8e028be4fb42b4a0d177d41c012b6a983979653660ec https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/tokenizers/punkt.zip /tmp/punkt.zip
ADD --checksum=sha256:e57f64187974277726a3417ca6f181ec5403676c717672eef6a748a7b20e0106 https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/tokenizers/punkt_tab.zip /tmp/punkt_tab.zip
ADD --checksum=sha256:cbda5ea6eef7f36a97a43d4a75f85e07fccbb4f23657d27b4ccbc93e2646ab59 https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/wordnet.zip /tmp/wordnet.zip
ADD --checksum=sha256:3b941e664852f3297b6040236626065796a2aaf7d7f9eec8779a3beaa1096c2d https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/omw-1.4.zip /tmp/omw-1.4.zip
RUN mkdir -p /usr/local/nltk_data/tokenizers /usr/local/nltk_data/corpora \
    && python -m zipfile -e /tmp/punkt.zip /usr/local/nltk_data/tokenizers \
    && python -m zipfile -e /tmp/punkt_tab.zip /usr/local/nltk_data/tokenizers \
    && mv /tmp/wordnet.zip /tmp/omw-1.4.zip /usr/local/nltk_data/corpora/ \
    && rm /tmp/punkt.zip /tmp/punkt_tab.zip \
    && chmod -R a+rX /usr/local/nltk_data
ENV NLTK_DATA=/usr/local/nltk_data

USER appuser
RUN python -c "from app.services.nltk_resources import ensure_nltk_data; ensure_nltk_data(); from nltk.corpus import wordnet; assert wordnet.synsets('hello')"
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

FROM runner AS test

USER root
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt
COPY tests/ tests/
USER appuser

CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]

FROM runner AS production
