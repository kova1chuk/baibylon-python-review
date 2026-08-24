import asyncio
import io
import inspect
import unittest
import zipfile
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.config import settings
from app.processors.epub_processor import EpubProcessor
from app.processors.subtitle_processor import SubtitleProcessor
from app.routers.image import analyze_image, image_health
from app.routers.text import analyze_plain_text, analyze_subtitle
from app.upload import read_bounded_upload


class UploadLimitsTest(unittest.TestCase):
    def test_upload_read_is_bounded_even_without_content_length(self):
        upload = UploadFile(file=io.BytesIO(b"12345"), filename="large.srt", size=None)
        with patch.object(settings, "MAX_UPLOAD_BYTES", 4):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(read_bounded_upload(upload))
        self.assertEqual(raised.exception.status_code, 413)

    def test_epub_rejects_excessive_decompressed_size(self):
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("large.xhtml", b"x" * 100)

        with patch.object(settings, "MAX_EPUB_UNCOMPRESSED_BYTES", 50):
            success, message, info = EpubProcessor().read_epub_file(
                content.getvalue(), "book.epub"
            )

        self.assertFalse(success)
        self.assertIn("too large", message)
        self.assertIsNone(info)

    def test_epub_parser_failure_exposes_no_exception_or_filename_details(self):
        secret = "SECRET upstream detail\nforged-log-line /tmp/private-book.epub"
        filename = "private\nforged.epub"
        processor = EpubProcessor()
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w") as archive:
            archive.writestr("mimetype", "application/epub+zip")

        with patch("app.processors.epub_processor.epub.read_epub", side_effect=RuntimeError(secret)):
            with self.assertLogs("EpubProcessor", level="ERROR") as captured:
                success, message, info = processor.read_epub_file(content.getvalue(), filename)

        self.assertFalse(success)
        self.assertEqual(message, "Invalid or unreadable EPUB file")
        self.assertIsNone(info)
        logs = "\n".join(captured.output)
        self.assertNotIn(secret, logs)
        self.assertNotIn(filename, logs)
        self.assertNotIn("private-book", logs)
        self.assertIn("error_type=RuntimeError", logs)

    def test_subtitle_rejects_excessive_extracted_text(self):
        with patch.object(settings, "MAX_EXTRACTED_TEXT_CHARS", 20):
            result = SubtitleProcessor().process_file(
                b"This subtitle line is deliberately longer than twenty characters.",
                "lesson.txt",
            )

        self.assertFalse(result.success)
        self.assertIn("too large", result.error_message)

    def test_heavy_upload_processing_runs_in_the_threadpool(self):
        upload = UploadFile(file=io.BytesIO(b"subtitle content"), filename="lesson.srt", size=16)
        sentinel = object()
        with patch("app.routers.text.run_in_threadpool", new_callable=AsyncMock) as run:
            run.return_value = sentinel
            result = asyncio.run(analyze_subtitle(upload))

        self.assertIs(result, sentinel)
        run.assert_awaited_once()

    def test_plain_text_route_is_sync_for_fastapi_threadpool_execution(self):
        self.assertFalse(inspect.iscoroutinefunction(analyze_plain_text))

    def test_image_route_reports_unavailable_instead_of_returning_empty_ocr(self):
        upload = UploadFile(
            file=io.BytesIO(b"image"),
            filename="lesson.png",
            size=5,
            headers={"content-type": "image/png"},
        )
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(analyze_image(upload, engine=None, preprocess=True, validate_words=True))

        self.assertEqual(raised.exception.status_code, 503)

    def test_image_health_reports_real_unavailable_state(self):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(image_health())

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail["available_engines"], [])

    def test_unavailable_image_route_does_not_claim_upload_limit_validation(self):
        upload = UploadFile(
            file=io.BytesIO(b"12345"),
            filename="large.png",
            size=None,
            headers={"content-type": "image/png"},
        )
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(analyze_image(upload, engine=None, preprocess=True, validate_words=True))

        self.assertEqual(raised.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
