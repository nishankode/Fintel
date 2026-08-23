import logging

from edgar.documents import HTMLParser, ParserConfig

from app.ingestion.schemas import (
    ParsedFilingDocument,
    ParsedFilingSection,
)


logger = logging.getLogger(__name__)


class FilingParserService:
    def parse(
        self,
        html: str,
        filing_type: str,
    ) -> ParsedFilingDocument:

        config = ParserConfig(
            form=filing_type,
        )

        parser = HTMLParser(config)

        document = parser.parse(html)

        full_text = document.text().strip()

        if not full_text:
            raise ValueError(
                "Parsed filing contains no text"
            )

        sections: list[ParsedFilingSection] = []

        for section_key, section in document.sections.items():

            section_text = section.text().strip()

            if not section_text:
                continue

            sections.append(
                ParsedFilingSection(
                    section_key=str(section_key),
                    text=section_text,
                    character_count=len(section_text),
                )
            )

        logger.info(
            "Filing parsed successfully: "
            "filing_type=%s characters=%s sections=%s",
            filing_type,
            len(full_text),
            len(sections),
        )

        return ParsedFilingDocument(
            text=full_text,
            character_count=len(full_text),
            sections=sections,
        )