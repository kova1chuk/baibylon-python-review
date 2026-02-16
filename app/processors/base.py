"""Base processor class for file processing operations."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


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

    def log_processing_start(self, filename: str, file_size: int) -> None:
        self.logger.info("Starting processing of %s (size: %d bytes)", filename, file_size)

    def log_processing_success(self, filename: str, text_length: int) -> None:
        self.logger.info("Successfully processed %s (extracted %d characters)", filename, text_length)

    def log_processing_error(self, filename: str, error_message: str) -> None:
        self.logger.error("Failed to process %s: %s", filename, error_message)

    def validate_text_content(self, text: str) -> tuple[bool, str]:
        if not text:
            return False, "No text content extracted"
        if not text.strip():
            return False, "Extracted text is empty"
        if len(text.strip()) < 10:
            return False, "Extracted text is too short (minimum 10 characters)"
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
