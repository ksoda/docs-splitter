# PDF目次分割パイプライン

## 概要

本プロジェクトは、PDFの目次（TOC）を基準に、紙面をそのまま保った
分割PDFを取り出すCLIである。テキストのトークンチャンク化は行わない
（撤去済み）。

詳細な要求仕様は `PRD.md`、設計契約は `DESIGN_SPEC.md` を参照。

---

## スコープ

- 目次付きPDF（書籍・雑誌）
- CLI利用前提
- UIは提供しない
- 元PDFは変更せず、既存の出力ファイルも上書きしない

---

## アーキテクチャ概要

- `adapters`: 外部入出力（JSON、pypdf経由のPDF読み書き）とデータ検証
- `core`: ドメインモデルと純粋変換（TOCからのユニット算定、境界照合）
- `pipeline`: 処理順序制御とエラー伝播

---

## セットアップ

system の `python3` は externally-managed のため、pypdf/reportlab は
プロジェクト専用venvに入れる。

```bash
uv venv .venv
uv pip install --python .venv/bin/python pypdf reportlab
```

---

## E2E最小実装

価値検証しやすい最小経路として、以下を E2E で実装済み。

- 入力JSONの境界検証
- 選択したTOC階層(`split_level`)からのユニット・未分類ページ算定と全ページ被覆検証
- ページ本文とTOCタイトルの境界照合（空白除去完全一致のみ自動一致）
- 不一致・未分類隣接境界・層ごとの標本一致境界を人手確認対象として選定
- 確認済み合図 (`--confirm-reviewed`) がある場合のみ、分割PDFを新規出力
- エラー分類付きのJSON出力（分割定義のみのモードがデフォルト）

実行例（分割定義のみ）:

```bash
PYTHONPATH=src .venv/bin/python -m docs_splitter.cli \
  --input tests/data/input_ok.json --output /tmp/plan.json
```

実行例（人手確認後、分割PDFも出す）:

```bash
PYTHONPATH=src .venv/bin/python -m docs_splitter.cli \
  --input tests/data/input_ok.json --output /tmp/plan.json \
  --split-output-dir /tmp/split --confirm-reviewed
```

テスト:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

## 再現可能な検証

リポジトリ直下で、毎回まだ存在しない証拠ディレクトリを指定して実行する。

    .venv/bin/python scripts/verify_project.py --output-dir /tmp/docs-splitter-evidence-20260923-run-01

検証スクリプトはコミット済みの合成PDFとJSONから入力を用意し、定義のみのCLI、
人手確認なしの拒否、合成フィクスチャでの確認済み分割、全出力ページの抽出テキスト
照合、元PDFのSHA-256、既存出力の上書き拒否を調べる。コマンド・終了値・対象revision・
検査結果・PRD要求ごとの状態は証拠ディレクトリに残る。既知のPRD未達と未検証事項は
テスト成功後も別に記録する。合成フィクスチャ向けの確認合図は実物PDFを承認しない。

合成PDFフィクスチャ (`tests/data/sample_magazine.pdf`) の再生成:

```bash
.venv/bin/python tests/fixtures/make_sample_pdf.py
```
