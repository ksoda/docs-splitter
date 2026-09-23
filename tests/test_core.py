from __future__ import annotations

import unittest

from docs_splitter.core.boundary import build_boundary_checks, select_review_items
from docs_splitter.core.normalize import build_units, validate_full_coverage
from docs_splitter.domain import (
    MatchStatus,
    PageCoverageError,
    PageRange,
    ReviewReason,
    TocEntry,
    TocRangeError,
    Unit,
)


class BuildUnitsTest(unittest.TestCase):
    def test_units_and_unclassified_cover_all_pages_in_order(self) -> None:
        toc = (
            TocEntry(level=1, title="特集A", page_start=2),
            TocEntry(level=2, title="特集A 第1章", page_start=3),
            TocEntry(level=1, title="特集B", page_start=4),
        )
        units, unclassified = build_units(toc=toc, split_level=1, total_pages=5)
        self.assertEqual(
            units,
            (
                Unit(name="特集A", level=1, page_range=PageRange(2, 3)),
                Unit(name="特集B", level=1, page_range=PageRange(4, 5)),
            ),
        )
        self.assertEqual(unclassified, (PageRange(1, 1),))
        validate_full_coverage(units=units, unclassified=unclassified, total_pages=5)

    def test_no_gap_when_first_unit_starts_at_page_one(self) -> None:
        toc = (TocEntry(level=1, title="特集A", page_start=1),)
        units, unclassified = build_units(toc=toc, split_level=1, total_pages=3)
        self.assertEqual(unclassified, ())
        self.assertEqual(units[0].page_range, PageRange(1, 3))

    def test_non_increasing_page_start_is_rejected(self) -> None:
        toc = (
            TocEntry(level=1, title="特集A", page_start=2),
            TocEntry(level=1, title="特集B", page_start=2),
        )
        with self.assertRaises(TocRangeError):
            build_units(toc=toc, split_level=1, total_pages=5)

    def test_page_start_beyond_total_pages_is_rejected(self) -> None:
        toc = (
            TocEntry(level=1, title="特集A", page_start=2),
            TocEntry(level=1, title="特集B", page_start=99),
        )
        with self.assertRaises(TocRangeError):
            build_units(toc=toc, split_level=1, total_pages=5)

    def test_no_entries_at_split_level_is_rejected(self) -> None:
        toc = (TocEntry(level=2, title="第1章", page_start=1),)
        with self.assertRaises(TocRangeError):
            build_units(toc=toc, split_level=1, total_pages=3)


class ValidateFullCoverageTest(unittest.TestCase):
    def test_gap_between_ranges_is_rejected(self) -> None:
        units = (Unit(name="A", level=1, page_range=PageRange(1, 2)),)
        unclassified = (PageRange(4, 5),)
        with self.assertRaises(PageCoverageError):
            validate_full_coverage(units=units, unclassified=unclassified, total_pages=5)

    def test_overlap_between_ranges_is_rejected(self) -> None:
        units = (
            Unit(name="A", level=1, page_range=PageRange(1, 3)),
            Unit(name="B", level=1, page_range=PageRange(3, 5)),
        )
        with self.assertRaises(PageCoverageError):
            validate_full_coverage(units=units, unclassified=(), total_pages=5)

    def test_coverage_short_of_total_pages_is_rejected(self) -> None:
        units = (Unit(name="A", level=1, page_range=PageRange(1, 3)),)
        with self.assertRaises(PageCoverageError):
            validate_full_coverage(units=units, unclassified=(), total_pages=5)


class BoundaryClassificationTest(unittest.TestCase):
    def test_exact_match_after_stripping_whitespace_is_matched(self) -> None:
        units = (Unit(name="特集A", level=1, page_range=PageRange(1, 2)),)
        checks = build_boundary_checks(units=units, actual_texts={1: " 特集A \n"})
        self.assertEqual(checks[0].status, MatchStatus.MATCHED)

    def test_different_text_is_mismatched(self) -> None:
        units = (Unit(name="特集A", level=1, page_range=PageRange(1, 2)),)
        checks = build_boundary_checks(units=units, actual_texts={1: "別の見出し"})
        self.assertEqual(checks[0].status, MatchStatus.MISMATCHED)


class ReviewSelectionTest(unittest.TestCase):
    def test_unclassified_adjacent_boundary_is_always_reviewed(self) -> None:
        units = (Unit(name="特集A", level=1, page_range=PageRange(2, 3)),)
        unclassified = (PageRange(1, 1),)
        checks = build_boundary_checks(units=units, actual_texts={2: "特集A"})
        items = select_review_items(units=units, unclassified=unclassified, boundary_checks=checks)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].reason, ReviewReason.UNCLASSIFIED_ADJACENT)

    def test_mismatch_is_always_reviewed(self) -> None:
        units = (Unit(name="特集A", level=1, page_range=PageRange(1, 2)),)
        checks = build_boundary_checks(units=units, actual_texts={1: "違う"})
        items = select_review_items(units=units, unclassified=(), boundary_checks=checks)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].reason, ReviewReason.MISMATCH)

    def test_matched_boundaries_are_sampled_two_per_level(self) -> None:
        units = tuple(
            Unit(name=f"章{i}", level=2, page_range=PageRange(i, i))
            for i in range(1, 6)
        )
        checks = build_boundary_checks(units=units, actual_texts={i: f"章{i}" for i in range(1, 6)})
        items = select_review_items(units=units, unclassified=(), boundary_checks=checks)
        self.assertEqual(len(items), 2)
        self.assertTrue(all(item.reason == ReviewReason.SAMPLE for item in items))

    def test_one_mismatch_forces_full_review_of_its_level(self) -> None:
        units = tuple(
            Unit(name=f"章{i}", level=2, page_range=PageRange(i, i))
            for i in range(1, 6)
        )
        texts = {i: f"章{i}" for i in range(1, 6)}
        texts[3] = "違う見出し"
        checks = build_boundary_checks(units=units, actual_texts=texts)
        items = select_review_items(units=units, unclassified=(), boundary_checks=checks)
        self.assertEqual(len(items), 5)


if __name__ == "__main__":
    unittest.main()
