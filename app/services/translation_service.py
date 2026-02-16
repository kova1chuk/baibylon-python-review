import logging
from typing import Optional

from app.config import settings
from app.models.translation import TranslateResponse

logger = logging.getLogger(__name__)


class DeepLTranslator:
    """Wrapper around deepl.Translator with graceful fallback."""

    def __init__(self) -> None:
        self._translator = None
        if settings.DEEPL_API_KEY:
            try:
                import deepl
                self._translator = deepl.Translator(settings.DEEPL_API_KEY)
            except Exception as exc:
                logger.warning("Failed to initialise DeepL translator: %s", exc)

    @property
    def available(self) -> bool:
        return self._translator is not None

    def translate_word(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
    ) -> TranslateResponse:
        if not self.available:
            raise RuntimeError("DeepL API key not configured")

        kwargs: dict = {
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
        if context:
            kwargs["context"] = context

        result = self._translator.translate_text(**kwargs)

        return TranslateResponse(
            translated_text=result.text,
            source_lang=source_lang,
            target_lang=target_lang,
            context_used=context is not None,
        )

    def translate_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
    ) -> list[TranslateResponse]:
        if not self.available:
            raise RuntimeError("DeepL API key not configured")

        results = self._translator.translate_text(
            texts,
            source_lang=source_lang,
            target_lang=target_lang,
        )

        return [
            TranslateResponse(
                translated_text=r.text,
                source_lang=source_lang,
                target_lang=target_lang,
                context_used=False,
            )
            for r in results
        ]


_translator: DeepLTranslator | None = None


def get_translator() -> DeepLTranslator:
    global _translator
    if _translator is None:
        _translator = DeepLTranslator()
    return _translator
