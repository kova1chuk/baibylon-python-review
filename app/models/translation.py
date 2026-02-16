from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    text: str = Field(..., description="Text to translate")
    source_lang: str = Field("EN", description="Source language code")
    target_lang: str = Field(..., description="Target language code")
    context: str | None = Field(None, description="Surrounding sentence for context-aware translation")


class TranslateResponse(BaseModel):
    translated_text: str
    source_lang: str
    target_lang: str
    context_used: bool
