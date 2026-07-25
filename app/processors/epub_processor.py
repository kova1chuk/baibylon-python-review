"""EPUB processing for extracting text from EPUB files."""

import io
import os
import tempfile
import zipfile
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup
from ebooklib import epub

from app.config import settings
from app.processors.base import BaseProcessor, ProcessingResult


@dataclass
class EpubFileInfo:
    filename: str
    file_size: int
    book: epub.EpubBook
    temp_file_path: str
    title: str = ""


class EpubProcessor(BaseProcessor):

    def validate_file_extension(self, filename: str) -> tuple[bool, str]:
        if not filename:
            return False, "No filename provided"
        if not filename.lower().endswith(".epub"):
            return False, "File must be an EPUB file"
        return True, ""

    def read_epub_file(
        self, file_content: bytes, filename: str
    ) -> tuple[bool, str, Optional[EpubFileInfo]]:
        is_valid, error_message = self.validate_file_extension(filename)
        if not is_valid:
            return False, error_message, None

        file_size = len(file_content)
        temp_file_path: str | None = None

        try:
            with zipfile.ZipFile(io.BytesIO(file_content)) as archive:
                entries = archive.infolist()
                if len(entries) > settings.MAX_EPUB_ARCHIVE_ENTRIES:
                    return False, "EPUB archive contains too many files", None
                if sum(entry.file_size for entry in entries) > settings.MAX_EPUB_UNCOMPRESSED_BYTES:
                    return False, "EPUB archive is too large after decompression", None

            with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp:
                tmp.write(file_content)
                temp_file_path = tmp.name

            book = epub.read_epub(temp_file_path)
            title = self.extract_title_from_epub(book)

            file_info = EpubFileInfo(
                filename=filename,
                file_size=file_size,
                book=book,
                temp_file_path=temp_file_path,
                title=title,
            )
            return True, "", file_info

        except Exception as exc:
            if temp_file_path:
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass
            error_msg = f"Failed to read EPUB file: {exc}"
            self.logger.error(error_msg)
            return False, error_msg, None

    def extract_title_from_epub(self, book: epub.EpubBook) -> str:
        try:
            if hasattr(book, "metadata") and book.metadata:
                dc_ns = "http://purl.org/dc/elements/1.1/"
                if dc_ns in book.metadata and "title" in book.metadata[dc_ns]:
                    title = book.metadata[dc_ns]["title"][0][0]
                    if title:
                        return title.strip()
                if "title" in book.metadata:
                    title = book.metadata["title"][0][0]
                    if title:
                        return title.strip()
            return ""
        except Exception as exc:
            self.logger.warning("Failed to extract title from EPUB metadata: %s", exc)
            return ""

    def extract_text_from_epub(self, book: epub.EpubBook) -> str:
        parts: list[str] = []
        total_length = 0
        for item in book.get_items():
            if item.get_type() == 9:  # ITEM_DOCUMENT
                soup = BeautifulSoup(item.get_content(), "html.parser")
                part = soup.get_text()
                total_length += len(part) + 1
                if total_length > settings.MAX_EXTRACTED_TEXT_CHARS:
                    raise ValueError("Extracted text is too large")
                parts.append(part)
        return " ".join(parts)

    def process_file(self, file_content: bytes, filename: str) -> ProcessingResult:
        self.log_processing_start(filename, len(file_content))

        success, error_message, file_info = self.read_epub_file(file_content, filename)
        if not success:
            return self.create_error_result(error_message)

        try:
            extracted_text = self.extract_text_from_epub(file_info.book)

            try:
                os.unlink(file_info.temp_file_path)
            except Exception as exc:
                self.logger.warning("Failed to clean up temporary file: %s", exc)

            is_valid, error_message = self.validate_text_content(extracted_text)
            if not is_valid:
                return self.create_error_result(error_message)

            self.log_processing_success(filename, len(extracted_text))
            return self.create_success_result(extracted_text, file_info)

        except Exception as e:
            try:
                os.unlink(file_info.temp_file_path)
            except Exception:
                pass
            error_msg = f"Failed to extract text from EPUB: {e}"
            self.log_processing_error(filename, error_msg)
            return self.create_error_result(error_msg)
