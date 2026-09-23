# 判断・検証記録: pstack・Superpowers部分導入

状態: Skillと合成フィクスチャ検証を導入し、手順を一度実行済み。PRD全体と実物PDFの検証は未完了。
実行系: 実装と初回検証はOpenAI Codex (GPT-6、ローカルツール実行)。
引き継ぎ後のレビュー、再検証、記録はClaude Code (Claude Opus 5.5)。
対象: docs-splitter CLI。利用者は開発者本人。
関連判断: development-disciplineのL-04-pilot-02。既存のN-05停止条件を維持する。

## 出典と適用範囲

| 上流 | 固定版 | 対象ファイル | ライセンス |
| --- | --- | --- | --- |
| cursor/plugins pstack | 0.15.3 / b42effe0aa50f59c693d7e2924714e015e00bf7c | create-verification-skill、principle-prove-it-works | MIT, Lauren Tan |
| obra/superpowers | v6.4.1 / 5bf4e78011075bcfc0dc295f0724994cd123ee71 | verification-before-completion、systematic-debugging | MIT, Jesse Vincent |

共通Skillの正本はdevelopment-discipline/.agents/skills/に置き、
同じSKILL.mdとUPSTREAM-NOTICES.mdを.claude/skills/へ複写した。
導入Skillはverified-delivery、systematic-debugging、
create-project-verification。プロジェクト専用のverify-docs-splitterと
scripts/verify_project.pyも追加した。上流全体やCursor固有機能は導入していない。

## 実行可能な検証

リポジトリ直下で、新しい証拠ディレクトリを毎回指定して実行する。

    .venv/bin/python scripts/verify_project.py --output-dir /tmp/docs-splitter-evidence-20260923-run-01

初回検証（Codex）の実行コマンドと証拠:

    .venv/bin/python scripts/verify_project.py --output-dir /tmp/docs-splitter-evidence-codex-final-20260923

初回の対象revisionはjj working copy 6fedab2546bae05d2326010d18d6c37c00911189で、
この記録ファイル追加前の状態である。

引き継ぎ後の再検証（Claude Code）は、この記録を含む最終内容で実行した。

    .venv/bin/python scripts/verify_project.py --output-dir /tmp/docs-splitter-evidence-claude-handoff-20260923

対象revisionは証拠先のmanifest.jsonとreport.mdに記録される。

検査は、コミット済み合成PDF・JSON、分割定義のみのCLI、期待する単位と未分類範囲、
全ページの連続割当、不確認時の出力拒否、合成フィクスチャの確認合図による分割、
各出力ファイル内の全ページ抽出テキストと元ページの順序一致、入力SHA-256、
既存PDF出力を壊さない再実行拒否を確認する。作業用ファイル削除後もログ、定義、
分割PDF、report.md、manifest.jsonは証拠先に残る。証拠先が既にあれば停止する。

## 実行結果

- PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_*.py': 32 tests、成功。
- scripts/verify_project.py: exit 0。合成PDF 5ページの範囲と全ページ割当が一致。
- 出力した4ページを入力の対応する範囲・ファイルごとに抽出テキストで照合し、順序・内容の差を検査した。見た目の完全一致は証明しない。
- 未確認実行はREVIEW_REQUIREDで拒否。既存出力への再実行はOUTPUT_EXISTSで拒否し、既存ファイルのSHA-256は同じ。
- 入力不足・既存証拠ディレクトリ・ページ欠落・順序違い・内容違いのテストを含む。
- skill-creator quick_validateでdevelopment-discipline側3件とdocs-splitter側4件が有効。共通3 Skill本文と上流通知のコピーの一致も確認した。
- 作業ディレクトリ外からの絶対パス実行をテストした。
- 引き継ぎ後、差分全体をレビューし、全テスト（32 tests、成功）、7 Skillのquick_validate、
  共通3 Skillと上流通知のコピー一致を再確認した。検証スクリプトは上記の新しい証拠先で再実行した。

## 要求別の状態

| 要求・既知の差 | 状態 | 根拠と範囲 |
| --- | --- | --- |
| FR-1 PDFアウトライン読取・階層保持 | 不適合 | 現行入力はJSONの目次で、PDFしおりを読まない。 |
| FR-1 曖昧さや不整合の全経路 | 未検証 | 不正ページ範囲は既存E2Eが検査するが、全種の曖昧入力を試していない。 |
| FR-2 全ページの連続した範囲割当 | 確認済み | この合成JSONでは期待範囲2–3、4–5、未分類1を検査した。 |
| FR-3 境界の完全一致照合 | 確認済み | 合成フィクスチャ2境界に限る。 |
| FR-3 曖昧候補提示 | 不適合 | 実装されていない。 |
| FR-3 人手確認 | 未検証 | review_items生成は合成で確認。実物の人手確認は未実施。 |
| FR-3 複数階層の層分け | 不適合 | 現行の境界選択は単一split_level。 |
| FR-3 縮小画像の確認表示 | 不適合 | 実装されていない。 |
| FR-4 元PDF不変・既存PDF出力拒否 | 確認済み | 合成フィクスチャでハッシュ比較。 |
| FR-4 紙面の見た目を保つ | 未検証 | 抽出テキストのみ照合し、視覚的完全一致は証明しない。 |
| FR-4 確認合図と定義のみ出力 | 確認済み | 合成フィクスチャの実行経路だけを検査した。 |
| 境界承認履歴 | 不適合 | 確認済み合図はあるが、誰が何を確認したか保存しない。 |
| PRDの実物PDF境界確認・時間条件 | 未検証 | この作業では実物PDFを開いていない。 |
| 実行時にLLM/APIを呼ばない | 未検証 | この実行でネットワーク通信監視はしていない。 |

テストや合成フィクスチャ検証の成功を、上表の不適合・未検証事項の解消に読み替えない。
今回の導入を理由に要求を削除したり、自動的に権限を拡張したりしない。

## 停止条件と権限

N-05に従い、既存の停止・エスカレーションと権限をそのまま適用する。
固定回数の再試行制限、全作業へのTDD強制、グローバル設定変更は加えない。
確認合図はこのコミット済み合成フィクスチャ専用で、実物PDFのレビューを代行しない。
