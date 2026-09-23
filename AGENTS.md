# AGENTS.md

このファイルは `docs-splitter` リポジトリ専用の運用ガイドである。
汎用的なコーディング原則より、ここでしか分からない実行・設計情報を優先する。

## Language Policy

- 思考は英語で行い、ユーザーへの応答は日本語で行う。
- 技術用語は正確に使い、不要な言語混在を避ける。

## Project Snapshot

- 目的: PDF の TOC（目次）を基準に、紙面を保ったまま階層単位の分割 PDF を出す CLI パイプライン。
- 主要入力: JSON (`doc_id`, `pdf_path`, `split_level`, `toc[]`)。`toc` は `level`/`title`/`page_start` のフラットな一覧。
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
- テスト:
  - `PYTHONPATH=src .venv/bin/python -m unittest tests/test_core.py tests/test_e2e.py`
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
