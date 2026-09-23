from __future__ import annotations

from docs_splitter.domain import PageCoverageError, PageRange, TocEntry, TocRangeError, Unit


def build_units(
    toc: tuple[TocEntry, ...],
    split_level: int,
    total_pages: int,
) -> tuple[tuple[Unit, ...], tuple[PageRange, ...]]:
    if total_pages <= 0:
        raise TocRangeError(f"total_pages must be positive: {total_pages}")
    selected = [entry for entry in toc if entry.level == split_level]
    if not selected:
        raise TocRangeError(f"no toc entries at split_level={split_level}")
    selected.sort(key=lambda entry: entry.page_start)
    _validate_strictly_increasing(selected)

    units: list[Unit] = []
    for index, entry in enumerate(selected):
        if entry.page_start < 1:
            raise TocRangeError(f"invalid page_start: {entry.title} ({entry.page_start})")
        next_start = selected[index + 1].page_start if index + 1 < len(selected) else None
        end = next_start - 1 if next_start is not None else total_pages
        if end > total_pages:
            raise TocRangeError(f"page range exceeds total pages: {entry.title} (end={end})")
        units.append(Unit(name=entry.title, level=entry.level, page_range=PageRange(entry.page_start, end)))

    unclassified: list[PageRange] = []
    first_start = units[0].page_range.start
    if first_start > 1:
        unclassified.append(PageRange(1, first_start - 1))

    validate_full_coverage(units=tuple(units), unclassified=tuple(unclassified), total_pages=total_pages)
    return tuple(units), tuple(unclassified)


def validate_full_coverage(
    units: tuple[Unit, ...],
    unclassified: tuple[PageRange, ...],
    total_pages: int,
) -> None:
    ranges = sorted(
        [unit.page_range for unit in units] + list(unclassified),
        key=lambda page_range: page_range.start,
    )
    expected_next = 1
    for page_range in ranges:
        if page_range.start != expected_next:
            raise PageCoverageError(
                f"pages are not contiguous: expected start {expected_next}, got {page_range.start}"
            )
        expected_next = page_range.end + 1
    if expected_next - 1 != total_pages:
        raise PageCoverageError(
            f"pages do not cover total_pages: covered up to {expected_next - 1}, expected {total_pages}"
        )


def _validate_strictly_increasing(entries: list[TocEntry]) -> None:
    for previous, current in zip(entries, entries[1:]):
        if current.page_start <= previous.page_start:
            raise TocRangeError(
                f"toc entries at split_level must have strictly increasing page_start: "
                f"{previous.title}({previous.page_start}) -> {current.title}({current.page_start})"
            )
