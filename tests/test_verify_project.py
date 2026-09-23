from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "scripts"))
from verify_project import PRD_REQUIREMENTS, ROOT_DIR, compare_page_sequence, verify_project


class ProjectVerificationTest(unittest.TestCase):
    def test_page_content_comparison_detects_missing_page(self) -> None:
        errors = compare_page_sequence(["page one", "page two", "page three"], ["page one", "page three"])
        self.assertTrue(any("page count differs" in error for error in errors))

    def test_page_content_comparison_detects_wrong_order(self) -> None:
        errors = compare_page_sequence(["page one", "page two"], ["page two", "page one"])
        self.assertTrue(errors)

    def test_page_content_comparison_detects_changed_content(self) -> None:
        errors = compare_page_sequence(["page one", "page two"], ["page one", "changed"])
        self.assertTrue(any("page 2 extracted content differs" in error for error in errors))

    def test_missing_fixture_fails_and_writes_failure_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="verify-missing-") as temporary:
            output = Path(temporary) / "evidence"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = verify_project(
                    output,
                    fixture_pdf=Path(temporary) / "missing.pdf",
                    invocation="test missing fixture",
                )
            self.assertEqual(result, 1)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["exit_code"], 1)
            self.assertEqual(manifest["checks"][0]["status"], "failed")
            self.assertIn("missing.pdf", manifest["checks"][0]["detail"])

    def test_known_prd_gaps_remain_visible(self) -> None:
        statuses = {item["id"]: item["status"] for item in PRD_REQUIREMENTS}
        self.assertEqual(statuses["FR-1a"], "不適合")
        self.assertEqual(statuses["FR-3b"], "不適合")
        self.assertEqual(statuses["FR-3d"], "不適合")
        self.assertEqual(statuses["FR-3f"], "不適合")
        self.assertEqual(statuses["KNOWN-1"], "不適合")
        self.assertEqual(statuses["FR-4a"], "未検証")
        self.assertEqual(statuses["SC-1"], "未検証")

    def test_cli_locates_repository_from_another_working_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="verify-cwd-") as temporary:
            evidence = Path(temporary) / "evidence"
            python = ROOT_DIR / ".venv" / "bin" / "python"
            script = ROOT_DIR / "scripts" / "verify_project.py"
            completed = subprocess.run(
                [str(python), str(script), "--output-dir", str(evidence)],
                cwd=temporary,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stderr + completed.stdout)
            report = json.loads((evidence / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(report["exit_code"], 0)
            self.assertTrue(report["target_revision"]["revision"])
            self.assertTrue((evidence / "split-output" / "001_特集A.pdf").is_file())

    def test_existing_evidence_directory_is_preserved_and_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="verify-existing-") as temporary:
            output = Path(temporary) / "evidence"
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("preserve", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = verify_project(output, invocation="test existing evidence")
            self.assertEqual(result, 2)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")
            self.assertFalse((output / "manifest.json").exists())
            self.assertIn("already exists", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
