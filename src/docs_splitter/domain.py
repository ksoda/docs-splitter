from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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


class PageCoverageError(DomainError):
    code = "PAGE_COVERAGE_ERROR"


class OutputExistsError(DomainError):
    code = "OUTPUT_EXISTS"


class ReviewRequiredError(DomainError):
    code = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class PageRange:
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 1:
            raise TocRangeError(f"page range start must be >= 1: {self.start}")
        if self.end < self.start:
            raise TocRangeError(f"page range end must be >= start: {self.start}-{self.end}")

    @property
    def length(self) -> int:
        return self.end - self.start + 1


@dataclass(frozen=True)
class TocEntry:
    level: int
    title: str
    page_start: int


@dataclass(frozen=True)
class SplitRequest:
    doc_id: str
    pdf_path: str
    split_level: int
    toc: tuple[TocEntry, ...]


@dataclass(frozen=True)
class Unit:
    name: str
    level: int
    page_range: PageRange


class MatchStatus(Enum):
    MATCHED = "matched"
    MISMATCHED = "mismatched"


@dataclass(frozen=True)
class BoundaryCheck:
    unit_name: str
    level: int
    page_start: int
    expected_title: str
    actual_text: str
    status: MatchStatus


class ReviewReason(Enum):
    MISMATCH = "mismatch"
    UNCLASSIFIED_ADJACENT = "unclassified_adjacent"
    SAMPLE = "sample"


@dataclass(frozen=True)
class ReviewItem:
    boundary: BoundaryCheck
    reason: ReviewReason


@dataclass(frozen=True)
class SplitPlan:
    doc_id: str
    total_pages: int
    units: tuple[Unit, ...]
    unclassified: tuple[PageRange, ...]
    boundary_checks: tuple[BoundaryCheck, ...]
    review_items: tuple[ReviewItem, ...]
