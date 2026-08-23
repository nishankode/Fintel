from pydantic import BaseModel


class ParsedFilingSection(BaseModel):
    section_key: str
    text: str
    character_count: int


class ParsedFilingDocument(BaseModel):
    text: str
    character_count: int
    sections: list[ParsedFilingSection]

class PreparedChunk(BaseModel):
    section_key: str
    chunk_index: int
    text: str
    character_count: int