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

ADD --checksum=sha256:6025f530624335c67d6547d44757b357b4e79bae030a0383e9887a92c1718f0b https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/taggers/averaged_perceptron_tagger_eng.zip /tmp/averaged_perceptron_tagger_eng.zip
ADD --checksum=sha256:1370234c7770045d0c50f41e08bc627ec92450324a946de14b93cd7d5e362a86 https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/chunkers/maxent_ne_chunker_tab.zip /tmp/maxent_ne_chunker_tab.zip
ADD --checksum=sha256:54ed02917d6771dcc3e8141218960d020947f7f2ccfd9ac9b320979349746015 https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/words.zip /tmp/words.zip
RUN mkdir -p /usr/local/nltk_data/taggers /usr/local/nltk_data/chunkers \
    && python -m zipfile -e /tmp/averaged_perceptron_tagger_eng.zip /usr/local/nltk_data/taggers \
    && python -m zipfile -e /tmp/maxent_ne_chunker_tab.zip /usr/local/nltk_data/chunkers \
    && python -m zipfile -e /tmp/words.zip /usr/local/nltk_data/corpora \
    && rm /tmp/averaged_perceptron_tagger_eng.zip /tmp/maxent_ne_chunker_tab.zip /tmp/words.zip \
    && chmod -R a+rX /usr/local/nltk_data

USER appuser
RUN python -c "from app.services.nltk_resources import ensure_nltk_data; ensure_nltk_data(); from nltk.corpus import wordnet; assert wordnet.synsets('hello'); from app.services.lexical_evidence import named_entities; assert named_entities('Apple released a new product.')"
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
