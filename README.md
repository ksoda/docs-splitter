# PDF構造分解パイプライン

## 概要

本プロジェクトは、PDFの目次（TOC）を基準に文書を階層構造へ分解し、
ユーザが処理可能な情報単位（チャンク）へ変換するエンジンである。

対象用途：

- 音声化（TTS）
- 要約生成
- 外部LLM処理
- ベクトル検索
- 学習支援

詳細な要求仕様は `PRD.md`、設計契約は `DESIGN_SPEC.md` を参照。

---

## スコープ

- 書籍形式PDF
- 目次付きPDF
- CLI / API利用前提
- UIは提供しない

---

## アーキテクチャ概要

- `adapters`: 外部入出力とデータ正規化
- `core`: ドメインモデルと純粋変換
- `pipeline`: 処理順序制御とエラー伝播
- `services`: 外部連携と再試行/タイムアウト制御

---

## E2E最小実装

価値検証しやすい最小経路として、以下を E2E で実装済み。

- 入力JSONの境界検証
- TOCページ範囲の正規化
- トークン上限制約を満たすチャンク分割
- エラー分類付きのJSON出力

実行例:

```bash
PYTHONPATH=src python3 -m docs_splitter.cli --input tests/data/input_ok.json --output /tmp/output.json
```

テスト:

```bash
PYTHONPATH=src python3 -m unittest tests/test_e2e.py
```
