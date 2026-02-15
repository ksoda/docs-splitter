from __future__ import annotations

from docs_splitter.domain import NormalizedNode, TocNode, TocRangeError


def normalize_toc(toc: tuple[TocNode, ...], total_pages: int) -> tuple[NormalizedNode, ...]:
    if total_pages <= 0:
        raise TocRangeError("total_pages must be positive")
    return _normalize_siblings(siblings=toc, parent_end=total_pages)


def _normalize_siblings(
    siblings: tuple[TocNode, ...],
    parent_end: int,
) -> tuple[NormalizedNode, ...]:
    normalized: list[NormalizedNode] = []
    for index, node in enumerate(siblings):
        next_start = siblings[index + 1].page_start if index + 1 < len(siblings) else None
        inferred_end = node.page_end
        if inferred_end is None and next_start is not None:
            inferred_end = next_start - 1
        if inferred_end is None:
            inferred_end = parent_end
        if node.page_start <= 0:
            raise TocRangeError(f"invalid page_start: {node.page_start}")
        if inferred_end < node.page_start:
            raise TocRangeError(
                f"page range inconsistent: {node.title} ({node.page_start}-{inferred_end})"
            )
        if inferred_end > parent_end:
            raise TocRangeError(
                f"page_end exceeds parent: {node.title} ({inferred_end}>{parent_end})"
            )
        children = _normalize_siblings(node.children, inferred_end)
        normalized.append(
            NormalizedNode(
                level=node.level,
                title=node.title,
                page_start=node.page_start,
                page_end=inferred_end,
                children=children,
            )
        )
    return tuple(normalized)

