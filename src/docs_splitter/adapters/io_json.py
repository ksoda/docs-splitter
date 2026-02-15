from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from docs_splitter.domain import (
    Chunk,
    InputValidationError,
    SplitRequest,
    SplitResult,
    TocNode,
)


def load_request(path: str) -> SplitRequest:
    payload: dict[str, Any] = _load_json_object(path)
    return _parse_request(payload)


def save_result(path: str, result: SplitResult) -> None:
    output = {
        "doc_id": result.doc_id,
        "chunks": [_chunk_to_dict(chunk) for chunk in result.chunks],
    }
    Path(path).write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_json_object(path: str) -> dict[str, Any]:
    try:
        content = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise InputValidationError(f"input file not found: {path}") from exc
    try:
        decoded: Any = json.loads(content)
    except json.JSONDecodeError as exc:
        raise InputValidationError(f"invalid json: {exc.msg}") from exc
    if not isinstance(decoded, dict):
        raise InputValidationError("root must be a JSON object")
    return decoded


def _parse_request(payload: dict[str, Any]) -> SplitRequest:
    doc_id = _require_str(payload, "doc_id")
    max_tokens = _require_int(payload, "max_tokens")
    if max_tokens <= 0:
        raise InputValidationError("max_tokens must be positive")
    pages = _require_str_list(payload, "pages")
    if not pages:
        raise InputValidationError("pages must not be empty")
    toc_raw = payload.get("toc")
    if not isinstance(toc_raw, list) or not toc_raw:
        raise InputValidationError("toc must be a non-empty list")
    toc = tuple(_parse_toc_node(node) for node in toc_raw)
    return SplitRequest(
        doc_id=doc_id,
        max_tokens=max_tokens,
        pages=tuple(pages),
        toc=toc,
    )


def _parse_toc_node(raw: Any) -> TocNode:
    if not isinstance(raw, dict):
        raise InputValidationError("toc node must be an object")
    level = _require_int(raw, "level")
    if level <= 0:
        raise InputValidationError("toc level must be >= 1")
    title = _require_str(raw, "title")
    page_start = _require_int(raw, "page_start")
    page_end_raw = raw.get("page_end")
    page_end: int | None
    if page_end_raw is None:
        page_end = None
    elif isinstance(page_end_raw, int):
        page_end = page_end_raw
    else:
        raise InputValidationError("page_end must be int or null")
    children_raw = raw.get("children", [])
    if not isinstance(children_raw, list):
        raise InputValidationError("children must be a list")
    children = tuple(_parse_toc_node(child) for child in children_raw)
    return TocNode(
        level=level,
        title=title,
        page_start=page_start,
        page_end=page_end,
        children=children,
    )


def _chunk_to_dict(chunk: Chunk) -> dict[str, Any]:
    return {
        "doc_id": chunk.doc_id,
        "node_path": list(chunk.node_path),
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "text": chunk.text,
        "tokens": chunk.tokens,
    }


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"{key} must be non-empty string")
    return value


def _require_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise InputValidationError(f"{key} must be int")
    return value


def _require_str_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise InputValidationError(f"{key} must be list[str]")
    out: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise InputValidationError(f"{key}[{index}] must be string")
        out.append(item)
    return out

