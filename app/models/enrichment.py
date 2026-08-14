from pydantic import BaseModel, Field


class EnrichWordRequest(BaseModel):
    text: str = Field(..., description="Word to enrich")
    word_id: str | None = Field(
        None,
        description="Deprecated and ignored; persistence is owned by the NestJS API",
        deprecated=True,
    )


class WordSense(BaseModel):
    pos: str
    definition: str
    examples: list[str]
    synonyms: list[str]


class WordNlpData(BaseModel):
    zipf_frequency: float
    is_top_1k: bool
    is_top_5k: bool
    is_top_10k: bool
    is_top_50k: bool
    pos_available: list[str]
    senses: list[WordSense]
    synonyms: list[str]
    antonyms: list[str]
    hypernyms: list[str]
    derived_forms: list[str]
    verb_frames: list[str]
    examples: list[str]
    estimated_level: str
    suggested_priority: int
    primary_definition: str


class EnrichWordResponse(BaseModel):
    success: bool
    data: WordNlpData
    db_updated: bool = Field(
        False,
        description="Always false; the analyzer does not have database access",
    )


class WordPhoneticsData(BaseModel):
    phonetic_text: str = ""
    phonetic_audio_link: str = ""


class WordZipfBatchRequest(BaseModel):
    words: list[str] = Field(..., min_length=1, max_length=1000)
    lang: str = Field("en", description="ISO 639-1 language code understood by wordfreq")


class WordZipfResult(BaseModel):
    text: str
    zipf_frequency: float | None = Field(
        None, description="None when `lang` has no wordfreq data"
    )


class WordZipfBatchResponse(BaseModel):
    lang_supported: bool
    results: list[WordZipfResult]


class SupportedLanguagesResponse(BaseModel):
    languages: list[str]
