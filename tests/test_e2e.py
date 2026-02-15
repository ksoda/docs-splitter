from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "tests" / "data"


class E2ETest(unittest.TestCase):
    def test_split_success(self) -> None:
        output_path = _temp_output_path()
        try:
            result = _run_cli(
                input_path=DATA_DIR / "input_ok.json",
                output_path=output_path,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["doc_id"], "sample-doc")
            self.assertGreaterEqual(len(payload["chunks"]), 2)
            for chunk in payload["chunks"]:
                self.assertLessEqual(chunk["tokens"], 30)
        finally:
            output_path.unlink(missing_ok=True)

    def test_split_token_limit_error(self) -> None:
        output_path = _temp_output_path()
        try:
            result = _run_cli(
                input_path=DATA_DIR / "input_too_large.json",
                output_path=output_path,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("TOKEN_LIMIT_EXCEEDED", result.stderr)
            self.assertFalse(output_path.exists())
        finally:
            output_path.unlink(missing_ok=True)


def _temp_output_path() -> Path:
    fd, path = tempfile.mkstemp(prefix="docs_splitter_", suffix=".json")
    os.close(fd)
    Path(path).unlink(missing_ok=True)
    return Path(path)


def _run_cli(input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR / "src")
    return subprocess.run(
        [
            "python3",
            "-m",
            "docs_splitter.cli",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        cwd=ROOT_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


if __name__ == "__main__":
    unittest.main()
