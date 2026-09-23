from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from docs_splitter.domain import InputValidationError, OutputExistsError, Unit


def read_page_count(pdf_path: str) -> int:
    reader = _open_reader(pdf_path)
    return len(reader.pages)


def read_first_lines(pdf_path: str, page_starts: tuple[int, ...]) -> dict[int, str]:
    reader = _open_reader(pdf_path)
    total = len(reader.pages)
    result: dict[int, str] = {}
    for page_start in page_starts:
        if page_start < 1 or page_start > total:
            raise InputValidationError(f"page number out of range: {page_start}")
        text = reader.pages[page_start - 1].extract_text() or ""
        result[page_start] = _first_nonempty_line(text)
    return result


def write_unit_pdfs(pdf_path: str, units: tuple[Unit, ...], output_dir: str) -> tuple[str, ...]:
    reader = _open_reader(pdf_path)
    output_root = Path(output_dir)
    planned_paths = [output_root / f"{index:03d}_{_safe_name(unit.name)}.pdf" for index, unit in enumerate(units, start=1)]
    for path in planned_paths:
        if path.exists():
            raise OutputExistsError(f"output already exists: {path}")

    output_root.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for unit, path in zip(units, planned_paths):
        writer = PdfWriter()
        for page_number in range(unit.page_range.start, unit.page_range.end + 1):
            writer.add_page(reader.pages[page_number - 1])
        with path.open("wb") as handle:
            writer.write(handle)
        written.append(str(path))
    return tuple(written)


def _open_reader(pdf_path: str) -> PdfReader:
    if not Path(pdf_path).exists():
        raise InputValidationError(f"pdf file not found: {pdf_path}")
    try:
        return PdfReader(pdf_path)
    except PdfReadError as exc:
        raise InputValidationError(f"failed to read pdf: {pdf_path}: {exc}") from exc


def _first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in name) or "unit"
