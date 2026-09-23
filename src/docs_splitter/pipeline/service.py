from __future__ import annotations

from docs_splitter.adapters import pdf_io
from docs_splitter.core.boundary import build_boundary_checks, select_review_items
from docs_splitter.core.normalize import build_units
from docs_splitter.domain import ReviewRequiredError, SplitPlan, SplitRequest


def build_plan(request: SplitRequest) -> SplitPlan:
    total_pages = pdf_io.read_page_count(request.pdf_path)
    units, unclassified = build_units(
        toc=request.toc,
        split_level=request.split_level,
        total_pages=total_pages,
    )
    page_starts = tuple(unit.page_range.start for unit in units)
    actual_texts = pdf_io.read_first_lines(request.pdf_path, page_starts)
    boundary_checks = build_boundary_checks(units=units, actual_texts=actual_texts)
    review_items = select_review_items(units=units, unclassified=unclassified, boundary_checks=boundary_checks)
    return SplitPlan(
        doc_id=request.doc_id,
        total_pages=total_pages,
        units=units,
        unclassified=unclassified,
        boundary_checks=boundary_checks,
        review_items=review_items,
    )


def execute_split(request: SplitRequest, plan: SplitPlan, output_dir: str, confirmed: bool) -> tuple[str, ...]:
    """確認済みの範囲だけを分割PDFとして出す (FR-4)。

    `confirmed` は、`plan.review_items` を利用者が確認し終えたことの明示的な合図。
    review_items が残る状態で確認なしに出力することは許さない。
    """
    if plan.review_items and not confirmed:
        raise ReviewRequiredError(
            f"{len(plan.review_items)} boundary review item(s) are unresolved; "
            "review the plan and pass confirmed=True before writing split PDFs"
        )
    return pdf_io.write_unit_pdfs(pdf_path=request.pdf_path, units=plan.units, output_dir=output_dir)
