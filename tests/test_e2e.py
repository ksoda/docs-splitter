from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "tests" / "data"
SAMPLE_PDF = DATA_DIR / "sample_magazine.pdf"


class E2ETest(unittest.TestCase):
    def test_define_only_mode_reports_units_and_review_items(self) -> None:
        original_hash = _sha256(SAMPLE_PDF)
        output_path = _temp_path(suffix=".json")
        try:
            result = _run_cli(input_path=DATA_DIR / "input_ok.json", output_path=output_path)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            plan = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(plan["doc_id"], "sample-magazine")
            self.assertEqual(plan["total_pages"], 5)
            self.assertEqual(
                [(u["name"], u["page_start"], u["page_end"]) for u in plan["units"]],
                [("特集A", 2, 3), ("特集B", 4, 5)],
            )
            self.assertEqual(
                [(u["page_start"], u["page_end"]) for u in plan["unclassified"]],
                [(1, 1)],
            )
            self.assertTrue(all(c["status"] == "matched" for c in plan["boundary_checks"]))
            reasons = {item["unit_name"]: item["reason"] for item in plan["review_items"]}
            self.assertEqual(reasons["特集A"], "unclassified_adjacent")
            self.assertEqual(reasons["特集B"], "sample")

            self.assertEqual(_sha256(SAMPLE_PDF), original_hash, "original PDF must not be modified")
        finally:
            output_path.unlink(missing_ok=True)

    def test_page_range_inconsistency_is_reported_and_nothing_is_written(self) -> None:
        output_path = _temp_path(suffix=".json")
        try:
            result = _run_cli(
                input_path=DATA_DIR / "input_page_range_invalid.json",
                output_path=output_path,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("TOC_RANGE_INCONSISTENT", result.stderr)
            self.assertFalse(output_path.exists())
        finally:
            output_path.unlink(missing_ok=True)

    def test_split_without_confirmation_is_refused(self) -> None:
        output_path = _temp_path(suffix=".json")
        split_dir = _temp_dir()
        try:
            result = _run_cli(
                input_path=DATA_DIR / "input_ok.json",
                output_path=output_path,
                split_output_dir=split_dir,
                confirm_reviewed=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("REVIEW_REQUIRED", result.stderr)
            self.assertEqual(list(split_dir.iterdir()), [])
        finally:
            output_path.unlink(missing_ok=True)
            _rmdir(split_dir)

    def test_confirmed_split_writes_page_faithful_pdfs_without_touching_original(self) -> None:
        original_hash = _sha256(SAMPLE_PDF)
        output_path = _temp_path(suffix=".json")
        split_dir = _temp_dir()
        try:
            result = _run_cli(
                input_path=DATA_DIR / "input_ok.json",
                output_path=output_path,
                split_output_dir=split_dir,
                confirm_reviewed=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            written = sorted(split_dir.iterdir())
            self.assertEqual(len(written), 2)

            from pypdf import PdfReader

            page_counts = [len(PdfReader(str(p)).pages) for p in written]
            self.assertEqual(page_counts, [2, 2])
            first_lines = [
                next(
                    line.strip()
                    for line in (PdfReader(str(p)).pages[0].extract_text() or "").splitlines()
                    if line.strip()
                )
                for p in written
            ]
            self.assertEqual(first_lines, ["特集A", "特集B"])

            self.assertEqual(_sha256(SAMPLE_PDF), original_hash, "original PDF must not be modified")

            rerun = _run_cli(
                input_path=DATA_DIR / "input_ok.json",
                output_path=output_path,
                split_output_dir=split_dir,
                confirm_reviewed=True,
            )
            self.assertEqual(rerun.returncode, 1)
            self.assertIn("OUTPUT_EXISTS", rerun.stderr)
        finally:
            output_path.unlink(missing_ok=True)
            _rmdir(split_dir)


def _temp_path(suffix: str) -> Path:
    fd, path = tempfile.mkstemp(prefix="docs_splitter_", suffix=suffix)
    os.close(fd)
    Path(path).unlink(missing_ok=True)
    return Path(path)


def _temp_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="docs_splitter_split_"))


def _rmdir(path: Path) -> None:
    for child in path.glob("**/*"):
        if child.is_file():
            child.unlink()
    path.rmdir()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_cli(
    input_path: Path,
    output_path: Path,
    split_output_dir: Path | None = None,
    confirm_reviewed: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR / "src")
    args = [
        sys.executable,
        "-m",
        "docs_splitter.cli",
        "--input",
        str(input_path),
        "--output",
        str(output_path),
    ]
    if split_output_dir is not None:
        args += ["--split-output-dir", str(split_output_dir)]
    if confirm_reviewed:
        args += ["--confirm-reviewed"]
    return subprocess.run(
        args,
        cwd=ROOT_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


if __name__ == "__main__":
    unittest.main()
