"""Subtitle processing for extracting text from SRT, VTT, TXT formats."""

import os
import re
from dataclasses import dataclass
from typing import Optional

from app.processors.base import BaseProcessor, ProcessingResult


@dataclass
class SubtitleFileInfo:
    filename: str
    file_extension: str
    file_size: int
    content: str
    encoding: str


class SubtitleProcessor(BaseProcessor):

    SUPPORTED_EXTENSIONS: list[str] = [".srt", ".vtt", ".txt"]

    def clean_html_tags(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def validate_file_extension(self, filename: str) -> tuple[bool, str]:
        if not filename:
            return False, "No filename provided"
        ext = os.path.splitext(filename.lower())[1]
        if ext not in self.SUPPORTED_EXTENSIONS:
            supported = ", ".join(self.SUPPORTED_EXTENSIONS)
            return False, f"Unsupported file format. Supported formats: {supported}"
        return True, ""

    def read_subtitle_file(
        self, file_content: bytes, filename: str
    ) -> tuple[bool, str, Optional[SubtitleFileInfo]]:
        is_valid, error_message = self.validate_file_extension(filename)
        if not is_valid:
            return False, error_message, None

        ext = os.path.splitext(filename.lower())[1]
        file_size = len(file_content)

        try:
            content = file_content.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            try:
                content = file_content.decode("latin-1")
                encoding = "latin-1"
            except Exception as exc:
                self.log_processing_error(filename, exc)
                return False, "Failed to decode subtitle file", None

        return True, "", SubtitleFileInfo(
            filename=filename,
            file_extension=ext,
            file_size=file_size,
            content=content,
            encoding=encoding,
        )

    def extract_text_from_srt(self, content: str) -> str:
        lines = content.split("\n")
        text_lines: list[str] = []
        skip_next = False

        for line in lines:
            line = line.strip()
            if not line:
                skip_next = False
                continue
            if skip_next:
                skip_next = False
                continue
            if re.match(r"^\d+$", line):
                skip_next = True
                continue
            if re.match(r"^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$", line):
                continue
            cleaned = self.clean_html_tags(line)
            if cleaned:
                text_lines.append(cleaned)

        return " ".join(text_lines)

    def extract_text_from_vtt(self, content: str) -> str:
        lines = content.split("\n")
        text_lines: list[str] = []
        skip_next = False

        for line in lines:
            line = line.strip()
            if not line or line == "WEBVTT":
                continue
            if re.match(r"^\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}", line):
                skip_next = True
                continue
            if skip_next and re.match(r"^[A-Za-z]+:", line):
                continue
            if skip_next:
                skip_next = False
            cleaned = self.clean_html_tags(line)
            if cleaned:
                text_lines.append(cleaned)

        return " ".join(text_lines)

    def extract_text_from_txt(self, content: str) -> str:
        text_lines: list[str] = []
        for line in content.split("\n"):
            line = line.strip()
            if line:
                cleaned = self.clean_html_tags(line)
                if cleaned:
                    text_lines.append(cleaned)
        return " ".join(text_lines)

    def extract_text_from_subtitles(self, content: str, file_extension: str) -> str:
        ext = file_extension.lower()
        if ext == ".srt":
            return self.extract_text_from_srt(content)
        if ext == ".vtt":
            return self.extract_text_from_vtt(content)
        if ext == ".txt":
            return self.extract_text_from_txt(content)
        raise ValueError(f"Unsupported file extension: {ext}")

    def process_file(self, file_content: bytes, filename: str) -> ProcessingResult:
        self.log_processing_start(filename, len(file_content))

        success, error_message, file_info = self.read_subtitle_file(file_content, filename)
        if not success:
            return self.create_error_result(error_message)

        try:
            extracted_text = self.extract_text_from_subtitles(
                file_info.content, file_info.file_extension
            )
            is_valid, error_message = self.validate_text_content(extracted_text)
            if not is_valid:
                return self.create_error_result(error_message)

            self.log_processing_success(filename, len(extracted_text))
            return self.create_success_result(extracted_text, file_info)

        except Exception as exc:
            self.log_processing_error(filename, exc)
            return self.create_error_result("Failed to extract text from subtitles")
