from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from docs_splitter.domain import (
    BoundaryCheck,
    InputValidationError,
    PageRange,
    ReviewItem,
    SplitPlan,
    SplitRequest,
    TocEntry,
    Unit,
)


def load_request(path: str) -> SplitRequest:
    payload: dict[str, Any] = _load_json_object(path)
    return _parse_request(payload)


def save_plan(path: str, plan: SplitPlan) -> None:
    output = {
        "doc_id": plan.doc_id,
        "total_pages": plan.total_pages,
        "units": [_unit_to_dict(unit) for unit in plan.units],
        "unclassified": [_page_range_to_dict(page_range) for page_range in plan.unclassified],
        "boundary_checks": [_boundary_check_to_dict(check) for check in plan.boundary_checks],
        "review_items": [_review_item_to_dict(item) for item in plan.review_items],
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
    pdf_path = _require_str(payload, "pdf_path")
    split_level = _require_int(payload, "split_level")
    if split_level <= 0:
        raise InputValidationError("split_level must be >= 1")
    toc_raw = payload.get("toc")
    if not isinstance(toc_raw, list) or not toc_raw:
        raise InputValidationError("toc must be a non-empty list")
    toc = tuple(_parse_toc_entry(entry) for entry in toc_raw)
    return SplitRequest(doc_id=doc_id, pdf_path=pdf_path, split_level=split_level, toc=toc)


def _parse_toc_entry(raw: Any) -> TocEntry:
    if not isinstance(raw, dict):
        raise InputValidationError("toc entry must be an object")
    level = _require_int(raw, "level")
    if level <= 0:
        raise InputValidationError("toc level must be >= 1")
    title = _require_str(raw, "title")
    page_start = _require_int(raw, "page_start")
    if page_start <= 0:
        raise InputValidationError("page_start must be >= 1")
    return TocEntry(level=level, title=title, page_start=page_start)


def _unit_to_dict(unit: Unit) -> dict[str, Any]:
    return {
        "name": unit.name,
        "level": unit.level,
        "page_start": unit.page_range.start,
        "page_end": unit.page_range.end,
    }


def _page_range_to_dict(page_range: PageRange) -> dict[str, Any]:
    return {"page_start": page_range.start, "page_end": page_range.end}


def _boundary_check_to_dict(check: BoundaryCheck) -> dict[str, Any]:
    return {
        "unit_name": check.unit_name,
        "level": check.level,
        "page_start": check.page_start,
        "expected_title": check.expected_title,
        "actual_text": check.actual_text,
        "status": check.status.value,
    }


def _review_item_to_dict(item: ReviewItem) -> dict[str, Any]:
    return {
        "unit_name": item.boundary.unit_name,
        "page_start": item.boundary.page_start,
        "reason": item.reason.value,
    }


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"{key} must be non-empty string")
    return value


def _require_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise InputValidationError(f"{key} must be int")
    return value
