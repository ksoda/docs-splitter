from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURE_PDF = ROOT_DIR / "tests" / "data" / "sample_magazine.pdf"
FIXTURE_JSON = ROOT_DIR / "tests" / "data" / "input_ok.json"
EXPECTED_TOTAL_PAGES = 5
EXPECTED_FIXTURE_SHA256 = "07393af5ceb4d488a3bc5f33305890f22c4f1095f2a3cfab71ac2a746fcdab45"
EXPECTED_REQUEST_SHA256 = "41576b082c41a811724f1c872f7bc2741249ef619456ab72cc51a1655a975b50"
EXPECTED_UNITS = (("特集A", 2, 3), ("特集B", 4, 5))
EXPECTED_UNCLASSIFIED = ((1, 1),)

PRD_REQUIREMENTS: tuple[dict[str, str], ...] = (
    {"id": "FR-1a", "status": "不適合", "requirement": "PDFのアウトラインを読み、階層を保つ", "evidence": "CLI入力はJSONのtocであり、PDFアウトラインは読み取らない。"},
    {"id": "FR-1b", "status": "未検証", "requirement": "曖昧さ・不整合時に推測せず報告する", "evidence": "不正ページ範囲は既存E2Eが検査するが、曖昧入力の全経路はこのフィクスチャで検査しない。"},
    {"id": "FR-2", "status": "確認済み", "requirement": "ページ範囲と割り当てが全ページを連続して覆う", "evidence": "今回の合成JSONに対し期待範囲、未分類範囲、ページ連続性を検査する。"},
    {"id": "FR-3a", "status": "確認済み", "requirement": "全境界を照合し、空白を除いて完全一致だけを自動一致とする", "evidence": "今回の合成フィクスチャの各境界照合結果を検査する。"},
    {"id": "FR-3b", "status": "不適合", "requirement": "曖昧一致候補を提示する", "evidence": "現行実装に候補提示はない。"},
    {"id": "FR-3c", "status": "未検証", "requirement": "不一致・未分類隣接境界・層別標本を人が確認する", "evidence": "合成フィクスチャのreview_items生成だけを確認する。実物での人手確認はしない。"},
    {"id": "FR-3d", "status": "不適合", "requirement": "確認画面に開始・直前ページの縮小画像を示す", "evidence": "現行CLIに縮小画像表示はない。"},
    {"id": "FR-3e", "status": "未検証", "requirement": "境界を数十秒で判断し、確認件数を抑える", "evidence": "所要時間・実物PDFの件数を測定しない。"},
    {"id": "FR-3f", "status": "不適合", "requirement": "複数階層にまたがる層分けを扱う", "evidence": "現行実装の境界と標本は指定された単一split_levelだけを扱う。"},
    {"id": "FR-4a", "status": "未検証", "requirement": "分割後の見た目を保つ", "evidence": "出力ページごとの抽出テキストを比較するが、視覚的な完全一致は証明しない。"},
    {"id": "FR-4b", "status": "確認済み", "requirement": "元PDFを変更せず既存出力を上書きしない", "evidence": "元PDF SHA-256と合成分割出力の再実行前後を比較する。"},
    {"id": "FR-4c", "status": "確認済み", "requirement": "確認なしでは分割出力せず、定義のみも生成できる", "evidence": "合成フィクスチャで未確認拒否、確認合図後のPDF出力、定義のみ出力を検査する。"},
    {"id": "SC-1", "status": "未検証", "requirement": "実物PDFの規定境界確認を完了する", "evidence": "この検査は合成フィクスチャのみを使用する。"},
    {"id": "NF-1", "status": "未検証", "requirement": "実行時にLLMや外部APIを呼ばない", "evidence": "この実行は通信監視を行わない。"},
    {"id": "KNOWN-1", "status": "不適合", "requirement": "境界承認の履歴を記録する", "evidence": "現行CLIは確認済みの真偽値を受け取るが、誰が何を確認したかの履歴は保存しない。"},
)

def compare_page_sequence(expected: Sequence[str], actual: Sequence[str]) -> list[str]:
    errors: list[str] = []
    if len(expected) != len(actual):
        errors.append(f"page count differs: expected {len(expected)}, observed {len(actual)}")
    for index, (expected_text, actual_text) in enumerate(zip(expected, actual), start=1):
        if expected_text != actual_text:
            errors.append(f"page {index} extracted content differs")
    return errors


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_pages(path: Path) -> list[str]:
    from pypdf import PdfReader
    return [(page.extract_text() or "") for page in PdfReader(str(path)).pages]


def target_revision(root: Path) -> dict[str, str | None]:
    result: dict[str, str | None] = {"provider": None, "revision": None}
    for command, provider in (
        (["jj", "log", "-r", "@", "--no-graph", "-T", "commit_id"], "jj"),
        (["git", "rev-parse", "HEAD"], "git"),
    ):
        try:
            completed = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
        except OSError:
            continue
        if completed.returncode == 0 and completed.stdout.strip():
            result.update(provider=provider, revision=completed.stdout.strip())
            return result
    return result


def _record(checks: list[dict[str, str]], name: str, passed: bool, detail: str) -> bool:
    checks.append({"name": name, "status": "passed" if passed else "failed", "detail": detail})
    return passed


def _intervals_cover_all(plan: dict[str, Any], total_pages: int) -> tuple[bool, str]:
    intervals: list[tuple[int, int]] = []
    for unit in plan["units"]:
        intervals.append((int(unit["page_start"]), int(unit["page_end"])))
    for item in plan["unclassified"]:
        intervals.append((int(item["page_start"]), int(item["page_end"])))
    intervals.sort()
    next_page = 1
    for start, end in intervals:
        if start != next_page or end < start:
            return False, f"expected next page {next_page}, got interval {start}-{end}"
        next_page = end + 1
    if next_page != total_pages + 1:
        return False, f"coverage ends at {next_page - 1}, expected {total_pages}"
    return True, f"continuous assignment covers pages 1-{total_pages}"


def _expected_output_name(index: int, name: str) -> str:
    safe_name = "".join(character if character.isalnum() else "_" for character in name) or "unit"
    return f"{index:03d}_{safe_name}.pdf"


def _write_reports(evidence_dir: Path, report: dict[str, Any]) -> None:
    (evidence_dir / "manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# docs-splitter verification",
        "",
        f"- Exit code: {report['exit_code']}",
        f"- Target revision: {report['target_revision'].get('revision') or 'unavailable'} ({report['target_revision'].get('provider') or 'unknown'})",
        f"- Invocation: {report['invocation']}",
        "",
        "## Checks",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {item['name']} | {item['status']} | {item['detail'].replace('|', '/')} |"
        for item in report["checks"]
    )
    lines.extend(["", "## PRD status", "", "| ID | Status | Requirement | Evidence boundary |", "| --- | --- | --- | --- |"])
    lines.extend(
        f"| {item['id']} | {item['status']} | {item['requirement']} | {item['evidence']} |"
        for item in report["prd_requirements"]
    )
    lines.extend(["", "## Commands", ""])
    for item in report["commands"]:
        lines.append(f"- {item['name']}: exit {item['exit_code']}: {shlex.join(item['argv'])}")
    (evidence_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_project(
    output_dir: Path,
    *,
    repo_root: Path = ROOT_DIR,
    fixture_pdf: Path = FIXTURE_PDF,
    fixture_json: Path = FIXTURE_JSON,
    invocation: str | None = None,
) -> int:
    evidence_dir = output_dir.expanduser().resolve()
    try:
        evidence_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(f"evidence directory already exists: {evidence_dir}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"cannot create evidence directory: {exc}", file=sys.stderr)
        return 2

    report: dict[str, Any] = {
        "invocation": invocation or shlex.join(sys.argv),
        "target_revision": target_revision(repo_root),
        "exit_code": 1,
        "checks": [],
        "commands": [],
        "fixture_sha256": {},
        "prd_requirements": list(PRD_REQUIREMENTS),
        "visual_fidelity_claim": "not established; extracted page text is compared",
        "real_pdf_reviewed": False,
    }
    checks: list[dict[str, str]] = report["checks"]
    missing = [str(path) for path in (fixture_pdf, fixture_json) if not path.is_file()]
    if missing:
        _record(checks, "committed synthetic inputs available", False, "missing: " + ", ".join(missing))
        _write_reports(evidence_dir, report)
        return 1
    _record(checks, "committed synthetic inputs available", True, "using the checked-in PDF and JSON fixture")
    report["fixture_sha256"] = {
        "pdf": sha256(fixture_pdf),
        "json": sha256(fixture_json),
    }
    hashes_match = (
        report["fixture_sha256"]["pdf"] == EXPECTED_FIXTURE_SHA256
        and report["fixture_sha256"]["json"] == EXPECTED_REQUEST_SHA256
    )
    if not _record(checks, "committed fixture hashes", hashes_match, json.dumps(report["fixture_sha256"], ensure_ascii=False)):
        _write_reports(evidence_dir, report)
        return 1

    try:
        payload = json.loads(fixture_json.read_text(encoding="utf-8"))
        referenced_pdf = Path(payload["pdf_path"])
        if not referenced_pdf.is_absolute():
            referenced_pdf = (repo_root / referenced_pdf).resolve()
        if referenced_pdf != fixture_pdf.resolve():
            _record(checks, "request references committed synthetic PDF", False, "input JSON points to a different PDF")
            _write_reports(evidence_dir, report)
            return 1
        source_pages = extract_pages(fixture_pdf)
        _record(
            checks,
            "synthetic PDF page count and extractable content",
            len(source_pages) == EXPECTED_TOTAL_PAGES and all(source_pages),
            f"expected {EXPECTED_TOTAL_PAGES} nonempty pages, observed {len(source_pages)}",
        )
        if len(source_pages) != EXPECTED_TOTAL_PAGES or not all(source_pages):
            _write_reports(evidence_dir, report)
            return 1
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        _record(checks, "synthetic fixture can be read", False, f"{type(exc).__name__}: {exc}")
        _write_reports(evidence_dir, report)
        return 1

    logs_dir = evidence_dir / "logs"
    logs_dir.mkdir()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")

    def invoke(name: str, output_path: Path, split_dir: Path | None = None, confirm: bool = False) -> subprocess.CompletedProcess[str]:
        argv = [
            sys.executable,
            "-m",
            "docs_splitter.cli",
            "--input",
            str(fixture_json),
            "--output",
            str(output_path),
        ]
        if split_dir is not None:
            argv.extend(["--split-output-dir", str(split_dir)])
        if confirm:
            argv.append("--confirm-reviewed")
        completed = subprocess.run(
            argv, cwd=repo_root, env=env, text=True, capture_output=True, check=False
        )
        (logs_dir / f"{name}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
        (logs_dir / f"{name}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
        report["commands"].append({"name": name, "argv": argv, "exit_code": completed.returncode})
        return completed

    revision = report["target_revision"]
    revision_ok = bool(revision.get("revision"))
    final_exit = 0
    if not _record(checks, "target revision captured", revision_ok, f"{revision.get('provider') or 'unknown'}: {revision.get('revision') or 'unavailable'}"):
        final_exit = 1
    original_hash = sha256(fixture_pdf)
    with tempfile.TemporaryDirectory(prefix="docs-splitter-verify-", dir=evidence_dir) as temporary:
        work = Path(temporary)
        plan_path = work / "define-only-plan.json"
        defined = invoke("define-only", plan_path)
        if not _record(checks, "CLI definition generation", defined.returncode == 0 and plan_path.is_file(), f"exit={defined.returncode}; {defined.stderr.strip() or 'plan written'}"):
            final_exit = 1
        if plan_path.is_file():
            shutil.copyfile(plan_path, evidence_dir / "split-plan.json")
            try:
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                units = tuple(
                    (unit["name"], int(unit["page_start"]), int(unit["page_end"]))
                    for unit in plan["units"]
                )
                gaps = tuple(
                    (int(item["page_start"]), int(item["page_end"]))
                    for item in plan["unclassified"]
                )
                ranges_match = units == EXPECTED_UNITS and gaps == EXPECTED_UNCLASSIFIED
                if not _record(checks, "expected split and unclassified ranges", ranges_match, f"units={units}; unclassified={gaps}"):
                    final_exit = 1
                coverage_ok, coverage_detail = _intervals_cover_all(plan, EXPECTED_TOTAL_PAGES)
                if not _record(checks, "continuous assignment of every page", coverage_ok, coverage_detail):
                    final_exit = 1
                boundary_checks = plan["boundary_checks"]
                boundaries_ok = (
                    len(boundary_checks) == len(EXPECTED_UNITS)
                    and all(item["status"] == "matched" for item in boundary_checks)
                )
                if not _record(checks, "fixture boundary checks", boundaries_ok, f"observed {len(boundary_checks)} checks; all expected checks must match"):
                    final_exit = 1
                has_review_items = bool(plan["review_items"])
                if not _record(checks, "review items are surfaced", has_review_items, f"observed {len(plan['review_items'])} review item(s)"):
                    final_exit = 1
                no_split_output = not (work / "define-only-split").exists()
                if not _record(checks, "definition-only mode writes no PDFs", no_split_output, "no split output directory was requested"):
                    final_exit = 1
            except (OSError, ValueError, KeyError, TypeError) as exc:
                _record(checks, "split plan has expected structure", False, f"{type(exc).__name__}: {exc}")
                final_exit = 1
        else:
            final_exit = 1

        unreviewed_dir = work / "unreviewed-output"
        unreviewed = invoke("unreviewed", work / "unreviewed-plan.json", unreviewed_dir)
        unreviewed_refused = (
            unreviewed.returncode != 0
            and "REVIEW_REQUIRED" in unreviewed.stderr
            and (not unreviewed_dir.exists() or not any(unreviewed_dir.iterdir()))
        )
        if not _record(checks, "unreviewed split is refused", unreviewed_refused, f"exit={unreviewed.returncode}; refusal code and no PDF output required"):
            final_exit = 1

        split_dir = work / "split-output"
        confirmed = invoke("synthetic-confirmed", work / "confirmed-plan.json", split_dir, confirm=True)
        output_paths = sorted(split_dir.iterdir()) if split_dir.exists() else []
        outputs = [path for path in output_paths if path.is_file() and path.suffix == ".pdf"]
        expected_names = [
            _expected_output_name(index, name)
            for index, (name, _, _) in enumerate(EXPECTED_UNITS, start=1)
        ]
        output_set_ok = [item.name for item in outputs] == expected_names and [item.name for item in output_paths] == expected_names
        if not _record(checks, "synthetic confirmed PDF output", confirmed.returncode == 0 and output_set_ok, f"exit={confirmed.returncode}; files={[item.name for item in output_paths]}"):
            final_exit = 1

        if output_set_ok:
            content_errors: list[str] = []
            compared_pages = 0
            for path, (unit_name, start, end) in zip(outputs, EXPECTED_UNITS):
                expected_unit_pages = source_pages[start - 1 : end]
                try:
                    observed_unit_pages = extract_pages(path)
                except (OSError, ValueError, ImportError) as exc:
                    content_errors.append(f"{unit_name}: unreadable output ({type(exc).__name__})")
                    continue
                compared_pages += len(expected_unit_pages)
                content_errors.extend(
                    f"{unit_name}: {error}"
                    for error in compare_page_sequence(expected_unit_pages, observed_unit_pages)
                )
            if not _record(checks, "every output page matches its corresponding input page text in order", not content_errors, "; ".join(content_errors) or f"compared {compared_pages} output pages in their expected files"):
                final_exit = 1

            before_rerun = {path.name: sha256(path) for path in outputs}
            rerun = invoke("existing-output-rerun", work / "rerun-plan.json", split_dir, confirm=True)
            after_rerun = {
                path.name: sha256(path) if path.is_file() else "directory"
                for path in sorted(split_dir.iterdir())
            }
            rejected_unchanged = (
                rerun.returncode != 0
                and "OUTPUT_EXISTS" in rerun.stderr
                and before_rerun == after_rerun
            )
            if not _record(checks, "existing outputs are rejected and unchanged", rejected_unchanged, f"exit={rerun.returncode}; output hashes unchanged={before_rerun == after_rerun}"):
                final_exit = 1
            artifact_dir = evidence_dir / "split-output"
            artifact_dir.mkdir()
            for path in outputs:
                shutil.copyfile(path, artifact_dir / path.name)
        else:
            _record(checks, "every output page matches its corresponding input page text in order", False, "expected output set was not produced")
            _record(checks, "existing outputs are rejected and unchanged", False, "no confirmed output set was available")
            final_exit = 1

    unchanged = sha256(fixture_pdf) == original_hash
    if not _record(checks, "source PDF SHA-256 unchanged", unchanged, f"before={original_hash}; after={sha256(fixture_pdf)}"):
        final_exit = 1
    report["exit_code"] = final_exit
    _write_reports(evidence_dir, report)
    print(f"verification exit={final_exit}; evidence={evidence_dir}")
    return final_exit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify docs-splitter against its committed synthetic PDF fixture.")
    parser.add_argument("--output-dir", required=True, help="new directory for durable verification evidence")
    args = parser.parse_args(argv)
    command = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]] if argv is None else [sys.executable, str(Path(__file__).resolve()), *argv]
    invocation = shlex.join(command)
    return verify_project(Path(args.output_dir), invocation=invocation)


if __name__ == "__main__":
    raise SystemExit(main())
