from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.config import settings


TranslationText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=5_000),
]
LanguageCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=16),
]


class TranslateRequest(BaseModel):
    text: TranslationText = Field(..., description="Text to translate")
    source_lang: LanguageCode = Field("EN", description="Source language code")
    target_lang: LanguageCode = Field(..., description="Target language code")
    context: TranslationText | None = Field(
        None,
        description="Surrounding sentence for context-aware translation",
    )


class TranslateResponse(BaseModel):
    translated_text: str
    source_lang: str
    target_lang: str
    context_used: bool


class TranslateBatchRequest(BaseModel):
    texts: list[TranslationText] = Field(..., min_length=1)
    source_lang: LanguageCode = Field("EN", description="Source language code")
    target_lang: LanguageCode = Field(..., description="Target language code")

    @model_validator(mode="after")
    def validate_batch_bounds(self):
        if len(self.texts) > settings.TRANSLATION_BATCH_MAX_ITEMS:
            raise ValueError(
                f"Batch exceeds the {settings.TRANSLATION_BATCH_MAX_ITEMS}-item limit"
            )
        if sum(len(text) for text in self.texts) > settings.TRANSLATION_BATCH_MAX_TOTAL_CHARS:
            raise ValueError(
                "Batch exceeds the total translation character limit"
            )
        return self


class TranslateBatchResponse(BaseModel):
    results: list[TranslateResponse]


ValidationText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=256),
]


class ValidateTranslationRequest(BaseModel):
    source: ValidationText
    target: ValidationText
    native_lang: LanguageCode


class ValidateTranslationResponse(BaseModel):
    is_valid: bool
    score: float = Field(..., ge=0, le=1)
