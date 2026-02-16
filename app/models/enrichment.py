from pydantic import BaseModel, Field


class EnrichWordRequest(BaseModel):
    text: str = Field(..., description="Word to enrich")
    word_id: str | None = Field(None, description="UUID of existing en_words row")


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
    db_updated: bool = False
