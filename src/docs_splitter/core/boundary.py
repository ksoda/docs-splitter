from __future__ import annotations

from docs_splitter.domain import BoundaryCheck, MatchStatus, PageRange, ReviewItem, ReviewReason, Unit

SAMPLE_SIZE_PER_LEVEL = 2


def normalize_for_match(text: str) -> str:
    return "".join(text.split())


def classify(expected_title: str, actual_text: str) -> MatchStatus:
    if normalize_for_match(expected_title) == normalize_for_match(actual_text):
        return MatchStatus.MATCHED
    return MatchStatus.MISMATCHED


def build_boundary_checks(
    units: tuple[Unit, ...],
    actual_texts: dict[int, str],
) -> tuple[BoundaryCheck, ...]:
    checks: list[BoundaryCheck] = []
    for unit in units:
        actual_text = actual_texts[unit.page_range.start]
        checks.append(
            BoundaryCheck(
                unit_name=unit.name,
                level=unit.level,
                page_start=unit.page_range.start,
                expected_title=unit.name,
                actual_text=actual_text,
                status=classify(unit.name, actual_text),
            )
        )
    return tuple(checks)


def select_review_items(
    units: tuple[Unit, ...],
    unclassified: tuple[PageRange, ...],
    boundary_checks: tuple[BoundaryCheck, ...],
) -> tuple[ReviewItem, ...]:
    """全境界を照合済みの前提で、人が確認すべき境界を選ぶ。

    不一致は全件、未分類に隣接する境界は全件、一致境界は層(level)ごとに2件を
    標本として選ぶ。標本を取った層に不一致が1件でもあれば、その層は全件を選ぶ。
    1件の境界が複数条件に該当する場合は最初に該当した理由だけを記録する。
    """
    adjacent_starts = _adjacent_page_starts(units=units, unclassified=unclassified)
    mismatched_levels = {check.level for check in boundary_checks if check.status is MatchStatus.MISMATCHED}

    items: list[ReviewItem] = []
    covered_starts: set[int] = set()

    for check in boundary_checks:
        if check.status is MatchStatus.MISMATCHED:
            items.append(ReviewItem(boundary=check, reason=ReviewReason.MISMATCH))
            covered_starts.add(check.page_start)

    for check in boundary_checks:
        if check.page_start in covered_starts:
            continue
        if check.page_start in adjacent_starts:
            items.append(ReviewItem(boundary=check, reason=ReviewReason.UNCLASSIFIED_ADJACENT))
            covered_starts.add(check.page_start)

    by_level: dict[int, list[BoundaryCheck]] = {}
    for check in boundary_checks:
        if check.status is MatchStatus.MATCHED and check.page_start not in covered_starts:
            by_level.setdefault(check.level, []).append(check)
    for level, checks in by_level.items():
        sample = checks if level in mismatched_levels else checks[:SAMPLE_SIZE_PER_LEVEL]
        for check in sample:
            items.append(ReviewItem(boundary=check, reason=ReviewReason.SAMPLE))
            covered_starts.add(check.page_start)

    return tuple(items)


def _adjacent_page_starts(units: tuple[Unit, ...], unclassified: tuple[PageRange, ...]) -> set[int]:
    starts: set[int] = set()
    for unit in units:
        for gap in unclassified:
            if unit.page_range.start == gap.end + 1 or unit.page_range.end == gap.start - 1:
                starts.add(unit.page_range.start)
    return starts
