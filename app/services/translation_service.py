import logging
from concurrent.futures import Future, ThreadPoolExecutor
from difflib import SequenceMatcher
from hashlib import sha256
from threading import BoundedSemaphore, Lock
from time import perf_counter
from typing import Optional
from unicodedata import normalize

import requests
from bs4 import BeautifulSoup

from app.config import settings
from app.models.translation import TranslateResponse, ValidateTranslationResponse

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

VALID_TRANSLATION_SCORE = 0.82
DEEPL_API_URL = "https://api.deepl.com/v2/translate"
DEEPL_FREE_API_URL = "https://api-free.deepl.com/v2/translate"
GOOGLE_TRANSLATE_URL = "https://translate.google.com/m"


class TranslationService:
    def __init__(self) -> None:
        self._deepl = bool(settings.DEEPL_API_KEY)
        self._inflight: dict[str, Future[TranslateResponse]] = {}
        self._inflight_lock = Lock()
        self._provider_slots = BoundedSemaphore(max(1, settings.TRANSLATION_PROVIDER_CONCURRENCY))

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
        api_key = settings.DEEPL_API_KEY
        if not self._deepl or not api_key:
            return None
        if not self._provider_slots.acquire(timeout=settings.TRANSLATION_PROVIDER_TIMEOUT_SECONDS):
            logger.warning("DeepL translation skipped because provider capacity is exhausted")
            return None
        try:
            payload: dict[str, str | list[str]] = {
                "text": [text],
                "source_lang": source_lang.upper(),
                "target_lang": target_lang.upper(),
            }
            if context:
                payload["context"] = context
            response = requests.post(
                DEEPL_FREE_API_URL if api_key.endswith(":fx") else DEEPL_API_URL,
                headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
                json=payload,
                timeout=_provider_timeout(),
            )
            response.raise_for_status()
            translations = response.json().get("translations", [])
            translated = translations[0].get("text") if translations else None
            return translated if isinstance(translated, str) and translated else None
        except Exception as exc:
            logger.warning(
                "DeepL translation failed %s error_type=%s",
                translation_ref(text, source_lang, target_lang, context),
                type(exc).__name__,
            )
            return None
        finally:
            self._provider_slots.release()

    def _translate_google(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> str | None:
        if not self._provider_slots.acquire(timeout=settings.TRANSLATION_PROVIDER_TIMEOUT_SECONDS):
            logger.warning("Google translation skipped because provider capacity is exhausted")
            return None
        try:
            src = LANG_CODE_MAP.get(source_lang.upper(), source_lang.lower())
            tgt = LANG_CODE_MAP.get(target_lang.upper(), target_lang.lower())
            response = requests.get(
                GOOGLE_TRANSLATE_URL,
                params={"sl": src, "tl": tgt, "q": text},
                headers={"User-Agent": "Vocairo-Text-Analyzer/1.0"},
                timeout=_provider_timeout(),
            )
            response.raise_for_status()
            element = BeautifulSoup(response.text, "html.parser").select_one("div.result-container")
            translated = element.get_text(strip=True) if element else None
            return translated or None
        except Exception as exc:
            logger.warning(
                "Google fallback translation failed %s error_type=%s",
                translation_ref(text, source_lang, target_lang),
                type(exc).__name__,
            )
            return None
        finally:
            self._provider_slots.release()

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
        context_used = bool(translated and context)
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
            context_used = False
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
            context_used=context_used,
        )

    def translate_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
    ) -> list[TranslateResponse]:
        unique_texts = list(dict.fromkeys(text.strip() for text in texts))
        if self._deepl:
            api_key = settings.DEEPL_API_KEY
            acquired = self._provider_slots.acquire(
                timeout=settings.TRANSLATION_PROVIDER_TIMEOUT_SECONDS
            )
            try:
                if not acquired or not api_key:
                    raise RuntimeError("DeepL provider capacity is exhausted")
                response = requests.post(
                    DEEPL_FREE_API_URL if api_key.endswith(":fx") else DEEPL_API_URL,
                    headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
                    json={
                        "text": unique_texts,
                        "source_lang": source_lang.upper(),
                        "target_lang": target_lang.upper(),
                    },
                    timeout=_provider_timeout(),
                )
                response.raise_for_status()
                results = response.json().get("translations", [])
                if len(results) != len(unique_texts):
                    raise RuntimeError("DeepL returned an incomplete batch")
                translated_by_text = {
                    text: TranslateResponse(
                        translated_text=result["text"],
                        source_lang=source_lang,
                        target_lang=target_lang,
                        context_used=False,
                    )
                    for text, result in zip(unique_texts, results)
                }
                return [translated_by_text[text.strip()] for text in texts]
            except Exception as exc:
                logger.warning(
                    "DeepL batch failed count=%d total_chars=%d error_type=%s",
                    len(unique_texts),
                    sum(len(text) for text in unique_texts),
                    type(exc).__name__,
                )
            finally:
                if acquired:
                    self._provider_slots.release()

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

    def validate_translation(
        self,
        source: str,
        target: str,
        native_lang: str,
    ) -> ValidateTranslationResponse:
        expected = self.translate_word(source, "EN", native_lang).translated_text
        score = translation_similarity(expected, target)
        return ValidateTranslationResponse(
            is_valid=score >= VALID_TRANSLATION_SCORE,
            score=score,
        )


def translation_similarity(expected: str, candidate: str) -> float:
    expected_normalized = _normalize_translation(expected)
    candidate_normalized = _normalize_translation(candidate)
    if not expected_normalized or not candidate_normalized:
        return 0.0
    if expected_normalized == candidate_normalized:
        return 1.0
    return round(SequenceMatcher(None, expected_normalized, candidate_normalized).ratio(), 4)


def _normalize_translation(text: str) -> str:
    normalized = normalize("NFKC", text).casefold()
    return " ".join("".join(char if char.isalnum() else " " for char in normalized).split())


def _provider_timeout() -> tuple[float, float]:
    timeout = max(0.1, settings.TRANSLATION_PROVIDER_TIMEOUT_SECONDS)
    return min(2.0, timeout), timeout


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
