from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ANALYZER_API_KEY: str = ""
    DEEPL_API_KEY: str = ""
    GOOGLE_CLOUD_CREDENTIALS_PATH: str = ""
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3006"
    DEBUG: bool = False
    MAX_UPLOAD_BYTES: int = 20 * 1024 * 1024
    MAX_EPUB_UNCOMPRESSED_BYTES: int = 100 * 1024 * 1024
    MAX_EPUB_ARCHIVE_ENTRIES: int = 10_000
    MAX_EXTRACTED_TEXT_CHARS: int = 2_000_000

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
