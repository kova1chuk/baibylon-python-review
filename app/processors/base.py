"""Base processor class for file processing operations."""

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from app.config import settings


@dataclass
class ProcessingResult:
    """Result of a file processing operation."""

    success: bool
    error_message: str = ""
    extracted_text: Optional[str] = None
    file_info: Optional[Any] = None


class BaseProcessor(ABC):
    """Base class for file processors."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def file_reference(filename: str) -> str:
        digest = hashlib.sha256(filename.encode("utf-8", errors="replace")).hexdigest()[:12]
        return f"sha256:{digest};chars={len(filename)}"

    def log_processing_start(self, filename: str, file_size: int) -> None:
        self.logger.info(
            "Starting file processing file_ref=%s bytes=%d",
            self.file_reference(filename),
            file_size,
        )

    def log_processing_success(self, filename: str, text_length: int) -> None:
        self.logger.info(
            "Completed file processing file_ref=%s extracted_chars=%d",
            self.file_reference(filename),
            text_length,
        )

    def log_processing_error(self, filename: str, error: BaseException) -> None:
        self.logger.error(
            "File processing failed file_ref=%s error_type=%s",
            self.file_reference(filename),
            type(error).__name__,
        )

    def validate_text_content(self, text: str) -> tuple[bool, str]:
        if not text:
            return False, "No text content extracted"
        if not text.strip():
            return False, "Extracted text is empty"
        if len(text.strip()) < 10:
            return False, "Extracted text is too short (minimum 10 characters)"
        if len(text) > settings.MAX_EXTRACTED_TEXT_CHARS:
            return False, "Extracted text is too large"
        return True, ""

    def validate_file_extension(self, filename: str) -> tuple[bool, str]:
        if not filename:
            return False, "No filename provided"
        return True, ""

    def create_error_result(self, error_message: str) -> ProcessingResult:
        return ProcessingResult(success=False, error_message=error_message)

    def create_success_result(
        self, extracted_text: str, file_info: Optional[Any] = None
    ) -> ProcessingResult:
        return ProcessingResult(success=True, extracted_text=extracted_text, file_info=file_info)

    @abstractmethod
    def process_file(self, file_content: bytes, filename: str) -> ProcessingResult:
        ...
