# AGENTS.md

このファイルは `docs-splitter` リポジトリ専用の運用ガイドである。
汎用的なコーディング原則より、ここでしか分からない実行・設計情報を優先する。

## Language Policy

- 思考は英語で行い、ユーザーへの応答は日本語で行う。
- 技術用語は正確に使い、不要な言語混在を避ける。

## Project Snapshot

- 目的: PDF の TOC を基準に、階層付きチャンクへ分割する CLI パイプライン。
- 主要入力: JSON (`doc_id`, `max_tokens`, `pages`, `toc`)。
- 主要出力: JSON (`doc_id`, `chunks[]`)。失敗時は stderr に `DomainError.code` を出す。
- スコープ外: UI 提供、PDF 編集、レイアウト完全再現。

## Runbook

- CLI 実行:
  - `PYTHONPATH=src python3 -m docs_splitter.cli --input tests/data/input_ok.json --output /tmp/output.json`
- E2E テスト:
  - `PYTHONPATH=src python3 -m unittest tests/test_e2e.py`
- 想定ランタイム: `python3` と標準ライブラリのみ。

## Architecture Boundaries

- `adapters/`: 外部 I/O と境界検証を担当。ここで生データを受け、ドメイン型へ変換する。
- `core/`: 純粋変換ロジックを担当 (`normalize`, `chunker`)。
- `pipeline/`: 処理順序の制御とエラー伝播を担当。
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
  - トークン上限 (`max_tokens`) を設定可能なまま維持する。
  - 変換ロジックに単体または既存 E2E へのテスト追加を行う。
  - バリデーション層を迂回しない。
- 振る舞い変更時:
  - `README.md` を更新する。
  - `SKILLS.md` を更新する（アーキテクチャ/哲学変更時）。
  - 破壊的変更は明示的に記録する。

## Gotchas

- `page_end` が `None` の TOC は正規化で確定されるため、前提を崩す変更は `core/normalize.py` を起点に確認する。
- トークン制約違反は `TOKEN_LIMIT_EXCEEDED` として扱う。終了コードや stderr 契約を変える場合はテスト更新が必須。
- E2E は `PYTHONPATH=src` 前提。実行方法変更時は `README.md` と `tests/test_e2e.py` を同時に更新する。

## Maintenance Notes

- この文書は「短く、プロジェクト固有情報中心」を維持する。
- 新しい運用知見はこのファイルに追記し、重複する一般論は削除する。
- セクション名は原則維持し、削除時は置換理由をコミットメッセージに残す。
