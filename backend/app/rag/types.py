from dataclasses import dataclass, field


@dataclass(slots=True)
class Page:
    """One page of a PDF, or one section of a DOCX/TXT/Markdown file."""

    number: int  # 1-based
    text: str
    ocr: bool = False


@dataclass(slots=True)
class ChunkDraft:
    index: int
    page_start: int
    page_end: int
    context: str
    content: str
    token_count: int
    embedding: list[float] = field(default_factory=list)

    @property
    def embedding_text(self) -> str:
        return f"{self.context}\n\n{self.content}" if self.context else self.content
