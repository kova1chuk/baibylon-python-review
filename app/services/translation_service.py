import logging
from concurrent.futures import Future, ThreadPoolExecutor
from hashlib import sha256
from threading import Lock
from time import perf_counter
from typing import Optional
from unicodedata import normalize

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
        self._inflight: dict[str, Future[TranslateResponse]] = {}
        self._inflight_lock = Lock()
        if settings.DEEPL_API_KEY:
            try:
                import deepl
                self._deepl = deepl.Translator(settings.DEEPL_API_KEY)
                logger.info("DeepL translator initialised")
            except Exception as exc:
                logger.warning(
                    "Failed to initialise DeepL translator error_type=%s",
                    type(exc).__name__,
                )

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
            logger.warning(
                "DeepL translation failed %s error_type=%s",
                translation_ref(text, source_lang, target_lang, context),
                type(exc).__name__,
            )
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
            logger.warning(
                "Google fallback translation failed %s error_type=%s",
                translation_ref(text, source_lang, target_lang),
                type(exc).__name__,
            )
            return None

    def translate_word(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
    ) -> TranslateResponse:
        key = translation_key(text, source_lang, target_lang, context)
        with self._inflight_lock:
            flight = self._inflight.get(key)
            owns_flight = flight is None
            if flight is None:
                flight = Future()
                self._inflight[key] = flight

        if not owns_flight:
            return flight.result()

        try:
            result = self._translate_word_uncached(text, source_lang, target_lang, context)
            flight.set_result(result)
            return result
        except BaseException as exc:
            flight.set_exception(exc)
            raise
        finally:
            with self._inflight_lock:
                if self._inflight.get(key) is flight:
                    self._inflight.pop(key, None)

    def _translate_word_uncached(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
    ) -> TranslateResponse:
        provider_started = perf_counter()
        translated = self._translate_deepl(text, source_lang, target_lang, context)
        _log_provider_timing(
            "deepl",
            translated is not None,
            provider_started,
            text,
            source_lang,
            target_lang,
            context,
        )

        if not translated:
            provider_started = perf_counter()
            translated = self._translate_google(text, source_lang, target_lang)
            _log_provider_timing(
                "google",
                translated is not None,
                provider_started,
                text,
                source_lang,
                target_lang,
                context,
            )

        if not translated:
            raise RuntimeError(
                f"All translation backends failed ({translation_ref(text, source_lang, target_lang, context)})"
            )

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
        unique_texts = list(dict.fromkeys(text.strip() for text in texts))
        if self._deepl:
            try:
                results = self._deepl.translate_text(
                    unique_texts,
                    source_lang=source_lang,
                    target_lang=target_lang,
                )
                translated_by_text = {
                    text: TranslateResponse(
                        translated_text=r.text,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        context_used=False,
                    )
                    for text, r in zip(unique_texts, results)
                }
                return [translated_by_text[text.strip()] for text in texts]
            except Exception as exc:
                logger.warning(
                    "DeepL batch failed count=%d total_chars=%d error_type=%s",
                    len(unique_texts),
                    sum(len(text) for text in unique_texts),
                    type(exc).__name__,
                )

        workers = max(1, min(settings.TRANSLATION_BATCH_CONCURRENCY, len(unique_texts)))
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="translation-batch") as pool:
            translated = list(
                pool.map(
                    lambda text: self.translate_word(text, source_lang, target_lang),
                    unique_texts,
                )
            )
        translated_by_text = dict(zip(unique_texts, translated))
        return [translated_by_text[text.strip()] for text in texts]


def translation_key(
    text: str,
    source_lang: str,
    target_lang: str,
    context: Optional[str] = None,
) -> str:
    normalized_text = normalize("NFC", " ".join(text.split()).strip())
    normalized_context = normalize("NFC", " ".join((context or "").split()).strip())
    canonical = "\n".join(
        [source_lang.strip().lower(), target_lang.strip().lower(), normalized_text, normalized_context]
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def translation_ref(
    text: str,
    source_lang: str,
    target_lang: str,
    context: Optional[str] = None,
) -> str:
    return (
        f"ref={translation_key(text, source_lang, target_lang, context)[:12]} "
        f"source={source_lang.strip().lower()} target={target_lang.strip().lower()} "
        f"text_len={len(text)} context_len={len(context or '')}"
    )


def _log_provider_timing(
    provider: str,
    success: bool,
    started_at: float,
    text: str,
    source_lang: str,
    target_lang: str,
    context: Optional[str] = None,
) -> None:
    logger.debug(
        "translation_provider_completed provider=%s success=%s duration_ms=%d %s",
        provider,
        success,
        round((perf_counter() - started_at) * 1000),
        translation_ref(text, source_lang, target_lang, context),
    )


_translator: TranslationService | None = None


def get_translator() -> TranslationService:
    global _translator
    if _translator is None:
        _translator = TranslationService()
    return _translator
