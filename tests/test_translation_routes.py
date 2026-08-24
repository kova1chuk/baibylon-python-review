import asyncio
import logging
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Lock
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.config import settings
from app.main import app
from app.models.translation import (
    TranslateBatchRequest,
    TranslateRequest,
    TranslateResponse,
    ValidateTranslationResponse,
)
from app.routers.health import health_check
from app.routers.text import analyze_epub
from app.routers.translation import translate, translate_batch
from app.services.translation_service import (
    TranslationService,
    translation_key,
    translation_similarity,
)


def response(text: str) -> TranslateResponse:
    return TranslateResponse(
        translated_text=f"translated:{text}",
        source_lang="en",
        target_lang="uk",
        context_used=False,
    )


class TranslationRoutesTest(unittest.TestCase):
    def test_validation_endpoint_requires_api_key_and_matches_backend_contract(self):
        class Validator:
            def validate_translation(self, source, target, native_lang):
                return ValidateTranslationResponse(is_valid=True, score=0.97)

        body = {"source": "apple", "target": "яблуко", "native_lang": "uk"}
        with (
            patch.object(settings, "ANALYZER_API_KEY", "internal-secret"),
            patch("app.routers.translation.get_translator", return_value=Validator()),
        ):
            client = TestClient(app)
            self.assertEqual(client.post("/api/translation/validate", json=body).status_code, 401)
            response = client.post(
                "/api/translation/validate",
                json=body,
                headers={"X-API-Key": "internal-secret"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"is_valid": True, "score": 0.97})

    def test_slow_provider_does_not_block_health(self):
        class SlowTranslator:
            def translate_word(self, text, source, target, context=None):
                time.sleep(0.08)
                return response(text)

        async def scenario():
            with patch("app.routers.translation.get_translator", return_value=SlowTranslator()):
                task = asyncio.create_task(
                    translate(TranslateRequest(text="private phrase", source_lang="en", target_lang="uk"))
                )
                await asyncio.sleep(0.01)
                started = asyncio.get_running_loop().time()
                health = await health_check()
                elapsed = asyncio.get_running_loop().time() - started
                result = await task
                return health, result, elapsed

        health, result, elapsed = asyncio.run(scenario())
        self.assertEqual(health.status, "healthy")
        self.assertEqual(result.translated_text, "translated:private phrase")
        self.assertLess(elapsed, 0.04)

    def test_translation_timeout_is_bounded(self):
        class SlowTranslator:
            def translate_word(self, text, source, target, context=None):
                time.sleep(0.08)
                return response(text)

        with (
            patch("app.routers.translation.get_translator", return_value=SlowTranslator()),
            patch.object(settings, "TRANSLATION_TIMEOUT_SECONDS", 0.01),
        ):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(
                    translate(
                        TranslateRequest(text="private phrase", source_lang="en", target_lang="uk")
                    )
                )

        self.assertEqual(raised.exception.status_code, 504)

    def test_slow_provider_does_not_block_epub_work(self):
        class SlowTranslator:
            def translate_word(self, text, source, target, context=None):
                time.sleep(0.08)
                return response(text)

        async def scenario():
            upload = UploadFile(BytesIO(b"epub"), size=4, filename="book.epub")
            with (
                patch("app.routers.translation.get_translator", return_value=SlowTranslator()),
                patch("app.routers.text._analyze_upload", return_value="epub-ready"),
            ):
                translation = asyncio.create_task(
                    translate(
                        TranslateRequest(
                            text="private phrase",
                            source_lang="en",
                            target_lang="uk",
                        )
                    )
                )
                await asyncio.sleep(0.01)
                started = asyncio.get_running_loop().time()
                epub = await analyze_epub(upload)
                elapsed = asyncio.get_running_loop().time() - started
                await translation
                return epub, elapsed

        epub, elapsed = asyncio.run(scenario())
        self.assertEqual(epub, "epub-ready")
        self.assertLess(elapsed, 0.04)

    def test_errors_do_not_log_raw_translation_text(self):
        secret = "customer confidential sentence"

        class BrokenTranslator:
            def translate_word(self, text, source, target, context=None):
                raise ValueError(secret)

        with (
            patch("app.routers.translation.get_translator", return_value=BrokenTranslator()),
            self.assertLogs("app.routers.translation", level=logging.ERROR) as captured,
        ):
            with self.assertRaises(HTTPException):
                asyncio.run(
                    translate(TranslateRequest(text=secret, source_lang="en", target_lang="uk"))
                )

        self.assertNotIn(secret, "\n".join(captured.output))

    def test_batch_bounds_count_and_total_characters(self):
        with patch.object(settings, "TRANSLATION_BATCH_MAX_ITEMS", 1):
            with self.assertRaises(ValidationError):
                TranslateBatchRequest(texts=["one", "two"], source_lang="en", target_lang="uk")

        with patch.object(settings, "TRANSLATION_BATCH_MAX_TOTAL_CHARS", 5):
            with self.assertRaises(ValidationError):
                TranslateBatchRequest(texts=["three", "four"], source_lang="en", target_lang="uk")

    def test_batch_route_uses_bounded_threadpool_path(self):
        class BatchTranslator:
            def translate_batch(self, texts, source, target):
                return [response(text) for text in texts]

        body = TranslateBatchRequest(texts=["one", "two"], source_lang="en", target_lang="uk")
        with patch("app.routers.translation.get_translator", return_value=BatchTranslator()):
            result = asyncio.run(translate_batch(body))

        self.assertEqual([item.translated_text for item in result.results], ["translated:one", "translated:two"])


class TranslationServiceTest(unittest.TestCase):
    def test_translation_similarity_normalizes_case_spacing_and_punctuation(self):
        self.assertEqual(translation_similarity("  Яблуко! ", "яблуко"), 1.0)
        self.assertLess(translation_similarity("яблуко", "груша"), 0.82)
        self.assertEqual(translation_similarity("яблуко", "!!!"), 0.0)

    def test_singleflight_keys_preserve_semantic_case_and_context(self):
        self.assertNotEqual(
            translation_key("Polish", "en", "uk"),
            translation_key("polish", "en", "uk"),
        )
        self.assertNotEqual(
            translation_key("bank", "en", "uk", "river bank"),
            translation_key("bank", "en", "uk", "financial bank"),
        )

    def test_identical_concurrent_requests_share_one_provider_call(self):
        service = TranslationService()
        service._deepl = None
        calls = 0
        lock = Lock()

        def slow_google(text, source, target):
            nonlocal calls
            with lock:
                calls += 1
            time.sleep(0.05)
            return "море"

        with patch.object(service, "_translate_google", side_effect=slow_google):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(service.translate_word, " Sea ", "EN", "UK")
                second = pool.submit(service.translate_word, "Sea", "en", "uk")
                results = [first.result(), second.result()]

        self.assertEqual(calls, 1)
        self.assertEqual([item.translated_text for item in results], ["море", "море"])

    def test_google_fallback_does_not_claim_deepl_context_usage(self):
        service = TranslationService()
        service._deepl = object()

        with (
            patch.object(service, "_translate_deepl", return_value=None),
            patch.object(service, "_translate_google", return_value="берег"),
        ):
            result = service.translate_word("bank", "en", "uk", "river bank")

        self.assertEqual(result.translated_text, "берег")
        self.assertFalse(result.context_used)

    def test_google_batch_fallback_has_bounded_concurrency_and_preserves_order(self):
        service = TranslationService()
        service._deepl = None
        active = 0
        peak = 0
        lock = Lock()

        def bounded_google(text, source, target):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.02)
            with lock:
                active -= 1
            return f"translated:{text}"

        with (
            patch.object(settings, "TRANSLATION_BATCH_CONCURRENCY", 2),
            patch.object(service, "_translate_google", side_effect=bounded_google),
        ):
            results = service.translate_batch(["one", "two", "three", "one"], "en", "uk")

        self.assertLessEqual(peak, 2)
        self.assertEqual(
            [item.translated_text for item in results],
            ["translated:one", "translated:two", "translated:three", "translated:one"],
        )

    def test_provider_logs_and_errors_never_contain_raw_text(self):
        service = TranslationService()
        service._deepl = None
        secret = "customer confidential sentence"

        with (
            patch(
                "app.services.translation_service.requests.get",
                side_effect=ValueError(secret),
            ),
            self.assertLogs("app.services.translation_service", level=logging.WARNING) as captured,
        ):
            with self.assertRaises(RuntimeError) as raised:
                service.translate_word(secret, "en", "uk")

        self.assertNotIn(secret, "\n".join(captured.output))
        self.assertNotIn(secret, str(raised.exception))

    def test_google_provider_network_call_has_a_hard_timeout(self):
        service = TranslationService()
        service._deepl = None

        class ProviderResponse:
            text = '<div class="result-container">море</div>'

            @staticmethod
            def raise_for_status():
                return None

        with (
            patch.object(settings, "TRANSLATION_PROVIDER_TIMEOUT_SECONDS", 1.25),
            patch(
                "app.services.translation_service.requests.get",
                return_value=ProviderResponse(),
            ) as request,
        ):
            translated = service._translate_google("sea", "en", "uk")

        self.assertEqual(translated, "море")
        self.assertEqual(request.call_args.kwargs["timeout"], (1.25, 1.25))


if __name__ == "__main__":
    unittest.main()
