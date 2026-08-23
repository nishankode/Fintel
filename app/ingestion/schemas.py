from pydantic import BaseModel


class ParsedFilingSection(BaseModel):
    section_key: str
    text: str
    character_count: int


class ParsedFilingDocument(BaseModel):
    text: str
    character_count: int
    sections: list[ParsedFilingSection]