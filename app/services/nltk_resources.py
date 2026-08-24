import logging

import nltk

logger = logging.getLogger(__name__)

_REQUIRED_RESOURCES = (
    "tokenizers/punkt",
    "tokenizers/punkt_tab",
    "corpora/wordnet.zip",
    "corpora/omw-1.4.zip",
)
_ready = False


def ensure_nltk_data() -> None:
    """Fail fast when the immutable image is missing an NLP resource."""
    global _ready
    if _ready:
        return

    for resource in _REQUIRED_RESOURCES:
        nltk.data.find(resource)

    _ready = True
    logger.info("NLTK resources verified")
