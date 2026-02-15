from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TocNode:
    level: int
    title: str
    page_start: int
    page_end: int | None
    children: tuple["TocNode", ...]


@dataclass(frozen=True)
class SplitRequest:
    doc_id: str
    max_tokens: int
    pages: tuple[str, ...]
    toc: tuple[TocNode, ...]


@dataclass(frozen=True)
class NormalizedNode:
    level: int
    title: str
    page_start: int
    page_end: int
    children: tuple["NormalizedNode", ...]


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    node_path: tuple[str, ...]
    page_start: int
    page_end: int
    text: str
    tokens: int


@dataclass(frozen=True)
class SplitResult:
    doc_id: str
    chunks: tuple[Chunk, ...]


class DomainError(Exception):
    """Base domain error."""

    code: str = "DOMAIN_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InputValidationError(DomainError):
    code = "INPUT_VALIDATION_ERROR"


class TocRangeError(DomainError):
    code = "TOC_RANGE_INCONSISTENT"


class TokenLimitError(DomainError):
    code = "TOKEN_LIMIT_EXCEEDED"

