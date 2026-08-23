import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ingestion.schemas import (
    ParsedFilingDocument,
    ParsedFilingSection,
    PreparedChunk,
)


logger = logging.getLogger(__name__)


class FilingChunkingService:
    def __init__(
        self,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
    ) -> None:
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            strip_whitespace=True,
        )

    def chunk_document(
        self,
        document: ParsedFilingDocument,
    ) -> list[PreparedChunk]:

        sections = document.sections

        if not sections:
            sections = [
                ParsedFilingSection(
                    section_key="full_document",
                    text=document.text,
                    character_count=document.character_count,
                )
            ]

        prepared_chunks: list[PreparedChunk] = []

        for section in sections:
            texts = self.splitter.split_text(
                section.text
            )

            for chunk_index, text in enumerate(texts):
                if not text.strip():
                    continue

                prepared_chunks.append(
                    PreparedChunk(
                        section_key=section.section_key,
                        chunk_index=chunk_index,
                        text=text,
                        character_count=len(text),
                    )
                )

        logger.info(
            "Document chunking completed: sections=%s chunks=%s",
            len(sections),
            len(prepared_chunks),
        )

        return prepared_chunks