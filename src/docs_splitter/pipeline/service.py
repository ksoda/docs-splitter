from __future__ import annotations

from docs_splitter.core.chunker import build_chunks
from docs_splitter.core.normalize import normalize_toc
from docs_splitter.domain import NormalizedNode, SplitRequest, SplitResult, TocRangeError


def run_split(request: SplitRequest) -> SplitResult:
    total_pages = len(request.pages)
    normalized_toc = normalize_toc(toc=request.toc, total_pages=total_pages)
    _validate_toc_bounds(total_pages=total_pages, toc=normalized_toc)
    chunks = build_chunks(
        doc_id=request.doc_id,
        pages=request.pages,
        toc=normalized_toc,
        max_tokens=request.max_tokens,
    )
    return SplitResult(doc_id=request.doc_id, chunks=chunks)


def _validate_toc_bounds(total_pages: int, toc: tuple[NormalizedNode, ...]) -> None:
    for node in toc:
        if node.page_start > total_pages:
            raise TocRangeError(f"page_start exceeds total pages: {node.title}")
        if node.page_end > total_pages:
            raise TocRangeError(f"page_end exceeds total pages: {node.title}")
        _validate_toc_bounds(total_pages=total_pages, toc=node.children)
