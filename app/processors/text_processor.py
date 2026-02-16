"""Text processing for plain text input."""

from dataclasses import dataclass
from typing import Optional

from app.processors.base import BaseProcessor, ProcessingResult


@dataclass
class TextInputInfo:
    text: str
    text_length: int
    cleaned_text: str


class TextProcessor(BaseProcessor):

    def validate_file_extension(self, filename: str) -> tuple[bool, str]:
        return True, ""

    def validate_text_input(self, text: str) -> tuple[bool, str]:
        if not text or not text.strip():
            return False, "No text provided"
        if len(text.strip()) < 10:
            return False, "Text is too short (minimum 10 characters)"
        return True, ""

    def clean_text(self, text: str) -> str:
        return " ".join(text.split())

    def process_text_input(self, text: str) -> tuple[bool, str, Optional[TextInputInfo]]:
        is_valid, error_message = self.validate_text_input(text)
        if not is_valid:
            return False, error_message, None

        try:
            cleaned_text = self.clean_text(text)
            text_info = TextInputInfo(
                text=text,
                text_length=len(text),
                cleaned_text=cleaned_text,
            )
            self.log_processing_success("text input", len(text))
            return True, "", text_info
        except Exception as e:
            error_msg = f"Failed to process text input: {e}"
            self.log_processing_error("text input", error_msg)
            return False, error_msg, None

    def process_file(self, file_content: bytes, filename: str) -> ProcessingResult:
        try:
            text = file_content.decode("utf-8")
            success, error_message, text_info = self.process_text_input(text)
            if not success:
                return self.create_error_result(error_message)
            return self.create_success_result(text_info.cleaned_text, text_info)
        except Exception as e:
            error_msg = f"Failed to process text file: {e}"
            self.log_processing_error(filename, error_msg)
            return self.create_error_result(error_msg)
