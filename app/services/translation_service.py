import logging
from typing import Optional

from app.config import settings
from app.models.translation import TranslateResponse

logger = logging.getLogger(__name__)

LANG_CODE_MAP = {
    "EN": "en",
    "UK": "uk",
    "DE": "de",
    "FR": "fr",
    "ES": "es",
    "IT": "it",
    "PL": "pl",
    "PT": "pt",
    "NL": "nl",
    "JA": "ja",
    "ZH": "zh-CN",
    "KO": "ko",
    "RU": "ru",
    "CS": "cs",
    "SV": "sv",
}


class TranslationService:
    def __init__(self) -> None:
        self._deepl = None
        if settings.DEEPL_API_KEY:
            try:
                import deepl
                self._deepl = deepl.Translator(settings.DEEPL_API_KEY)
                logger.info("DeepL translator initialised")
            except Exception as exc:
                logger.warning("Failed to initialise DeepL translator: %s", exc)

    @property
    def available(self) -> bool:
        return True

    def _translate_deepl(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
    ) -> str | None:
        if not self._deepl:
            return None
        try:
            kwargs: dict = {
                "text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
            }
            if context:
                kwargs["context"] = context
            result = self._deepl.translate_text(**kwargs)
            return result.text
        except Exception as exc:
            logger.warning("DeepL translation failed for '%s': %s", text, exc)
            return None

    def _translate_google(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> str | None:
        try:
            from deep_translator import GoogleTranslator

            src = LANG_CODE_MAP.get(source_lang.upper(), source_lang.lower())
            tgt = LANG_CODE_MAP.get(target_lang.upper(), target_lang.lower())
            result = GoogleTranslator(source=src, target=tgt).translate(text)
            return result or None
        except Exception as exc:
            logger.warning("Google fallback translation failed for '%s': %s", text, exc)
            return None

    def translate_word(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
    ) -> TranslateResponse:
        translated = self._translate_deepl(text, source_lang, target_lang, context)

        if not translated:
            translated = self._translate_google(text, source_lang, target_lang)

        if not translated:
            raise RuntimeError(f"All translation backends failed for '{text}'")

        return TranslateResponse(
            translated_text=translated,
            source_lang=source_lang,
            target_lang=target_lang,
            context_used=context is not None and self._deepl is not None,
        )

    def translate_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
    ) -> list[TranslateResponse]:
        if self._deepl:
            try:
                results = self._deepl.translate_text(
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
            except Exception as exc:
                logger.warning("DeepL batch failed, falling back to Google: %s", exc)

        return [
            self.translate_word(t, source_lang, target_lang)
            for t in texts
        ]


_translator: TranslationService | None = None


def get_translator() -> TranslationService:
    global _translator
    if _translator is None:
        _translator = TranslationService()
    return _translator
