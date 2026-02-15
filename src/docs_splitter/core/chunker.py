from __future__ import annotations

from docs_splitter.domain import Chunk, NormalizedNode, TokenLimitError


def build_chunks(
    doc_id: str,
    pages: tuple[str, ...],
    toc: tuple[NormalizedNode, ...],
    max_tokens: int,
) -> tuple[Chunk, ...]:
    leaves = _collect_leaf_nodes(toc=toc, path=())
    chunks: list[Chunk] = []
    for path, node in leaves:
        text = _extract_text(pages=pages, start=node.page_start, end=node.page_end)
        node_chunks = _split_node_text(
            doc_id=doc_id,
            node_path=path,
            page_start=node.page_start,
            page_end=node.page_end,
            text=text,
            max_tokens=max_tokens,
        )
        chunks.extend(node_chunks)
    return tuple(chunks)


def _collect_leaf_nodes(
    toc: tuple[NormalizedNode, ...],
    path: tuple[str, ...],
) -> tuple[tuple[tuple[str, ...], NormalizedNode], ...]:
    leaves: list[tuple[tuple[str, ...], NormalizedNode]] = []
    for node in toc:
        node_path = path + (node.title,)
        if not node.children:
            leaves.append((node_path, node))
            continue
        leaves.extend(_collect_leaf_nodes(node.children, node_path))
    return tuple(leaves)


def _extract_text(pages: tuple[str, ...], start: int, end: int) -> str:
    page_slice = pages[start - 1 : end]
    return "\n".join(page_slice).strip()


def _split_node_text(
    doc_id: str,
    node_path: tuple[str, ...],
    page_start: int,
    page_end: int,
    text: str,
    max_tokens: int,
) -> tuple[Chunk, ...]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text] if text else []
    chunks: list[Chunk] = []
    current_parts: list[str] = []
    for paragraph in paragraphs:
        paragraph_tokens = _count_tokens(paragraph)
        if paragraph_tokens > max_tokens:
            raise TokenLimitError(f"single paragraph exceeds max_tokens: {node_path}")
        candidate_parts = current_parts + [paragraph]
        candidate_text = "\n\n".join(candidate_parts)
        if _count_tokens(candidate_text) <= max_tokens:
            current_parts = candidate_parts
            continue
        chunks.append(
            _make_chunk(
                doc_id=doc_id,
                node_path=node_path,
                page_start=page_start,
                page_end=page_end,
                text="\n\n".join(current_parts),
            )
        )
        current_parts = [paragraph]
    if current_parts:
        chunks.append(
            _make_chunk(
                doc_id=doc_id,
                node_path=node_path,
                page_start=page_start,
                page_end=page_end,
                text="\n\n".join(current_parts),
            )
        )
    return tuple(chunks)


def _make_chunk(
    doc_id: str,
    node_path: tuple[str, ...],
    page_start: int,
    page_end: int,
    text: str,
) -> Chunk:
    return Chunk(
        doc_id=doc_id,
        node_path=node_path,
        page_start=page_start,
        page_end=page_end,
        text=text,
        tokens=_count_tokens(text),
    )


def _count_tokens(text: str) -> int:
    compact = "".join(text.split())
    return len(compact)

