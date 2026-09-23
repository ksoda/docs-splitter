# AGENTS.md

このファイルは `docs-splitter` リポジトリ専用の運用ガイドである。
汎用的なコーディング原則より、ここでしか分からない実行・設計情報を優先する。

## Language Policy

- 思考は英語で行い、ユーザーへの応答は日本語で行う。
- 技術用語は正確に使い、不要な言語混在を避ける。

## Skill applicability

- When debugging failures or unexpected results, use .claude/skills/systematic-debugging/SKILL.md before changing code.
- Before reporting a task complete or checks passing, use .claude/skills/verified-delivery/SKILL.md and state requirement-level evidence and remaining gaps.
- When creating or changing a project verification path, use .claude/skills/create-project-verification/SKILL.md.
- To exercise this repository's PDF split CLI and retain evidence, use .claude/skills/verify-docs-splitter/SKILL.md.

## Project Snapshot

- 目的: PDF の TOC（目次）を基準に、紙面を保ったまま階層単位の分割 PDF を出す CLI パイプライン。
- 主要入力: JSON (`doc_id`, `pdf_path`, `split_level`, `toc[]`)。`toc` は `level`/`title`/`page_start` のフラットな一覧。PDFアウトライン（しおり）は読み取らない。
- 主要出力: 分割定義 JSON (`doc_id`, `total_pages`, `units[]`, `unclassified[]`, `boundary_checks[]`, `review_items[]`)。
  `--split-output-dir` 指定時は、人手確認済みの合図 (`--confirm-reviewed`) がある場合だけ分割 PDF も出す。
  失敗時は stderr に `DomainError.code` を出す。
- スコープ外: UI 提供、PDF 編集、レイアウト完全再現、テキストのトークンチャンク化（撤去済み）。

## Runbook

- 初期セットアップ（初回のみ、pypdf/reportlab は外部管理環境の `python3` に直接は入れられないためプロジェクト専用venvを使う）:
  - `uv venv .venv && uv pip install --python .venv/bin/python pypdf reportlab`
- 合成PDFフィクスチャの再生成（通常は不要。`tests/data/sample_magazine.pdf` を変える場合のみ）:
  - `.venv/bin/python tests/fixtures/make_sample_pdf.py`
- CLI 実行:
  - `PYTHONPATH=src .venv/bin/python -m docs_splitter.cli --input tests/data/input_ok.json --output /tmp/plan.json`
  - 分割PDFも出す場合: 上記に `--split-output-dir /tmp/split --confirm-reviewed` を追加。
- プロジェクト検証（リポジトリ直下で新しい証拠先を指定）:
  - .venv/bin/python scripts/verify_project.py --output-dir /tmp/docs-splitter-evidence-20260923-run-01
  - 証拠先が既にあると停止するため、毎回異なる未使用のパスを使う。
- 全テスト:
  - PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_*.py'
- 想定ランタイム: `python3`（`.venv` 経由）、標準ライブラリ、pypdf。
  reportlabも許可済み（主に合成PDFフィクスチャ生成用）。その他の依存追加はdevelopment-disciplineのN-05に従う。

## Autonomous Loop

- 自律ループはCLIのClaude Codeで動かす（例: `claude --remote-control "docs-splitter"`）。判断の根拠はdevelopment-disciplineの `docs/first-pilot-conditions.md`（N-05）。
- 既定モデルは `opusplan`（計画モードはOpus、実行はSonnet）。記録・集計・定型作業は `routine` サブエージェント（Haiku）、エスカレーション後は `escalation` サブエージェント（Opus）に任せる。
- `.claude/hooks/loop_guard.py` が停止とエスカレーションの合図を出す。セッション開始・resume・`/clear` から60分（`LOOP_GUARD_LIMIT_MINUTES`）を超えると、Read系と `tasks/` への記録以外のツールを拒否する。同じテストの2回目の失敗、同じファイルの5回目の書き直し、ツールエラーの3連続でエスカレーション、同じテストの3回目の失敗かツールエラーの5連続で停止を指示する。しきい値は暫定値。
- 状態は `.claude/state/`（Git管理外）に置く。テスト: `python3 -m unittest tests/test_loop_guard.py`。

## Architecture Boundaries

- `adapters/`: 外部 I/O と境界検証を担当。`io_json.py` は入出力 JSON、`pdf_io.py` は pypdf 経由の PDF 読み書き（ページ数取得、境界照合用テキスト抽出、分割PDF書き出し）を担う。
- `core/`: 純粋変換ロジックを担当 (`normalize.py`: TOCからのユニット/未分類ページ算定と全ページ被覆検証、`boundary.py`: 境界照合の分類と人手確認対象の選定)。I/O禁止。
- `pipeline/`: 処理順序の制御とエラー伝播を担当 (`service.py`: `build_plan`, `execute_split`)。
- `domain.py`: 不変データモデル (`@dataclass(frozen=True)`) とドメイン例外を定義する。

## Non-Negotiables

- 新規関数には型注釈を付与する。
- 層間で生 `dict` を受け渡さない。
- 外部入力は境界で必ず検証する。
- ドメインモデルの不変性を壊さない。
- 包括例外 (`except Exception`) で握りつぶさない。
- グローバルな可変状態を導入しない。

## Change Checklist

- 機能追加時:
  - 全ページが単位または未分類に割り当てられる不変条件 (`core/normalize.validate_full_coverage`) を維持する。
  - 変換ロジックに単体 (`tests/test_core.py`) または既存 E2E (`tests/test_e2e.py`) へのテスト追加を行う。
  - バリデーション層を迂回しない。
  - 元PDFへの書き込み・既存出力の上書きを追加しない。
- 振る舞い変更時:
  - `README.md` を更新する。
  - `SKILLS.md` を更新する（アーキテクチャ/哲学変更時）。
  - 破壊的変更は明示的に記録する。

## Gotchas

- `split_level` に一致する TOC エントリだけがユニット境界になる。ネストした子エントリはユニット化に使わないため、境界にしたい階層は `split_level` で明示的に選ぶ。
- 各ユニットの `page_end` は次の同一 `split_level` エントリの `page_start - 1`（最後は `total_pages`）で決まる。先頭エントリが1ページ目より後なら、その手前は自動的に `unclassified` になる。
- 境界照合は「ページの最初の非空行」対「TOCタイトル」の空白除去完全一致のみを自動一致とする（あいまい候補提示は初回スコープ外）。
- `execute_split` は `review_items` が残る状態で `confirmed=False`（CLIでは `--confirm-reviewed` 未指定）だと `REVIEW_REQUIRED` で拒否する。
- テストは `.venv`（`uv venv .venv && uv pip install --python .venv/bin/python pypdf reportlab`）経由の `python3` が前提。system の `python3` は externally-managed のため pypdf を直接入れられない。実行方法変更時は `README.md` と `tests/test_e2e.py` を同時に更新する。

## Maintenance Notes

- この文書は「短く、プロジェクト固有情報中心」を維持する。
- 新しい運用知見はこのファイルに追記し、重複する一般論は削除する。
- セクション名は原則維持し、削除時は置換理由をコミットメッセージに残す。

## 課題・Wiki・Skill抽出の運用

- 課題状態の正本は `.tickets/`。既存の `tasks/` は判断・検証の根拠としてリンクする。
- 着手時は `tk start ID`。Codexでは現在のセッションを自動で紐付ける。
  自動紐付けができない場合は `tk bind ID codex|claude SESSION.jsonl` を実行する。
  Claudeへ委譲した記録も、同じ課題へ明示的に追加できる。
- 実装完了と仮説評価を分けてticketへ記録し、課題の受入条件を満たして判断を残した時に
  `tk close ID --note "根拠と判断"`。停止時は `tk pause ID --note "停止理由"`。
  時間・利用枠の上限による停止時は `--defer` を付け、追加のモデル呼出しをしない。
- 課題の区切りで `wiki/` の知識・根拠・確認日を更新し、`tk index` で横断索引を更新する。
  抽出失敗は課題の結果と別に記録される。後で `tk learn` で再試行する。
- Skill候補は `tk skills list` / `tk skills show ID` で確認する。候補生成は正式採用ではない。
  本人が内容を採用した後だけ `tk skills adopt ID --reviewed` を使う。
  共通Skillを共有するにはdevelopment-disciplineの `scripts/install_links.py` を実行する。
- 新しい要件・目標・予算の変更は、Wikiや生成Skillから自動的に採用しない。
