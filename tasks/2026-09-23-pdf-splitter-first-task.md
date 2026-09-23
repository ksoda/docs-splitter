# 判断・検証記録: 初回試行 — 目次単位のPDF分割

状態: 実装完了・実物PDFレビュー待ち（仮説検証は未完了）
担当・決定者: Claude Code（実装・記録） / ユーザー（目的・仕様判断）
開始日・レビュー条件: 2026-09-23。実装完了後、実物PDFの確認と利用後にレビューする。
関連する決定ID: N-01〜N-05。development-discipline commit 15e2b37

## 何を決めるか

- 対象者と困りごと: 本人。目次上の学習単位を、紙面を保ったPDFとして取り出したい。
- 期待する変化: 特集を一つのPDFにしてNotebookへ投入し、通して理解できる。
- 守る価値・制約: 元PDFを変更しない。個人利用のみで再配布しない。LLM/APIを実装・実行時に呼ばない。

## 前提と検証

- 主要な仮説: PDFアウトラインの階層で範囲を決めてページを分割すれば、本文の見た目と順序を保った学習単位を作れる。
- 対案・別の説明: 既存のテキストチャンク化を続ける、または既存のPDF編集ツールで手作業する。
- 予想される観察: 合成PDFでは期待するページ範囲が再現される。実物では境界確認の時間と誤りが記録できる。
- 判断を変える証拠・反証条件: ページの欠落・重複・順序違い、元PDFまたは既存出力の変更、境界判断が数十秒を繰り返し超える、確認件数が1冊10〜20件を大きく超える。
- 検証方法と証拠の取得元: pypdfで作成した合成PDFの自動テスト。実物PDFは環境変数が設定された場合だけローカルで確認し、内容ではなく要約を記録する。
- 観察期間・判断できない場合の扱い: 実装完了後、雑誌1冊を確認する。情報不足や曖昧な境界があれば停止して判断を求める。

## 実行と権限

- 最小の変更: テキストチャンク機能を撤去し、選択した目次階層のページ範囲を分割PDFとして出す経路に置き換える。本文照合と境界確認表示もPRDの条件に従う。
- 実装の受入条件と検証:
  - pypdfで作成した合成PDFをテストデータとしてコミットする。
  - 自動検査で全ページが一つの分割単位または未分類に割り当てられ、ページ数と順序が一致する。
  - 出力ページ範囲が期待と一致し、元PDFを変えず、既存出力を上書きしない。
  - 全境界を照合し、不一致・未分類隣接境界、および規定数の一致境界を人が確認できる。
  - E2Eテストを実行し、実物PDF検査は環境変数未設定ならスキップする。
- 復旧方法（必要な場合）: 各論理変更をローカルコミットし、問題があれば該当コミットをrevertする。元PDFには書き込まない。
- agentへの委譲範囲: Claude Codeに実装、テスト、文書更新、ローカルコミット、記録を任せる。目的・成功条件・制約の変更、人手境界判断、pushはユーザーが判断する。pypdf／reportlabはN-05で許可済み。これ以外の依存追加はユーザーが判断する。
- 時間・費用上限: 無人実行1回60分またはClaude利用枠到達の早い方で停止。usage creditsはoff。使用した実行系を課題とコミットCo-Authored-Byに記録する。
- 停止条件、停止する人: N-02の境界確認条件、同一テスト2回の失敗、仕様判断が必要、60分または利用枠到達でClaude Codeが停止し報告する。pypdf／reportlab以外の依存が必要なら導入せず報告する。
- 目標・予算等の変更権者: ユーザー。

## 結果と判断

- 観察された事実・証拠へのリンク:
  - `python3 -c "import pypdf"` は `ModuleNotFoundError` になる（未インストール）。
  - リポジトリに `pyproject.toml` / `requirements*.txt` など依存宣言ファイルが存在しない。
  - `python3 -m pip list` に PDF処理ライブラリは含まれない。
  - 停止時点の `AGENTS.md` Runbook は「想定ランタイム: `python3` と標準ライブラリのみ」と明記していた（本更新でpypdfを追記）。
  - 標準ライブラリに PDF のアウトライン読み取り・ページ分割PDF出力ができるモジュールはない（`help('modules')` で該当なし）。
  - 停止時点の `PRD.md` 5節はPDF処理にpypdfを「候補」としていた（本更新でpypdfを選定済みに変更）。
- 解釈と別の説明: 初回の停止判断は誤りだった。development-disciplineのN-04は合成PDFをpypdfで作るよう定め、N-05はpypdf／reportlab以外の依存追加をユーザー判断としているため、pypdfは既に許可されている。AGENTS.mdの標準ライブラリのみという一般的な想定は、この試行に関する個別決定に置き換わる。自前でPDFパーサ／ライターを実装せず、pypdfを使って再開する。
- 不確実性・証拠不足: 境界確認に要する時間、Notebookでの利用効果は未検証（実物PDFでの確認が別途必要）。
- 予想との差: 未実施（実物PDF確認は別途、環境変数設定時のみ）。
- 実装完了 / 未完了: 実装完了。`PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p "test_*.py"` で25件のテストが成功（`tests/test_core.py` 14件、`tests/test_e2e.py` 4件、既存の`tests/test_loop_guard.py` 7件）。合成PDF (`tests/data/sample_magazine.pdf`) をpypdf/reportlabで作成しコミットした。CLIは分割定義JSON出力（既定）と、`--confirm-reviewed`確認後のみの分割PDF出力（`--split-output-dir`）を実装。元PDF非改変とテスト実行前後のSHA256一致、既存出力の上書き拒否(`OUTPUT_EXISTS`)を自動テストで検証済み。
- 検証の判断: 実装受入条件（本節の「実装の受入条件と検証」）は満たしたと判断。Codexが同じ25件のテストを再実行し、全件成功した。本課題全体の仮説検証（Notebook投入時の学習効果、実物PDFでの境界確認所要時間）は未実施で判断不能のまま。PRD全体の充足も意味しない。あいまい一致候補と境界の縮小画像は未実装で、複数階層の層分けや承認履歴も初回実装に含めていない。
- 次の行動: 実物PDFでの境界確認は環境変数設定時に別途実施。現時点では無人実行を停止し、実装結果をユーザーに報告する。
- 判断者・日付・理由: Codex、2026-09-23、N-04／N-05の既存許可を見落とし、一般的なAGENTS.md記述を優先して誤停止したため。
- 更新した仕様・用語・決定記録・手順: PRDとAGENTS.mdの依存条件をpypdf／reportlab許可に合わせ、追加依存の停止条件を修正（Codex）。本セッションでAGENTS.md（Project Snapshot/Runbook/Architecture Boundaries/Change Checklist/Gotchas）、README.md、SKILLS.mdをPDF分割の実装内容に合わせて更新し、venvセットアップ手順を追記した（Claude Sonnet 5）。破壊的変更: CLIの入出力JSONスキーマを`doc_id/max_tokens/pages/toc→chunks[]`から`doc_id/pdf_path/split_level/toc[]→units[]/unclassified[]/boundary_checks[]/review_items[]`へ全面変更し、`core/chunker.py`とトークン分割機能を撤去した。`TOKEN_LIMIT_EXCEEDED`エラーコードは廃止し、`TOC_RANGE_INCONSISTENT`/`PAGE_COVERAGE_ERROR`/`OUTPUT_EXISTS`/`REVIEW_REQUIRED`を新設。
- 人間の介入時間、総費用、所要時間: 試行終了時に記録する。
- この規律自体の問題と修正案: 試行終了時に記録する。

## 知見

### 観察事実

Claude Codeの初回実行は依存判断の誤読で停止し、commit c68c2e9に記録した。pypdfがN-04／N-05で許可済みと確認し、誤停止の解釈を訂正した（本更新のCo-Authored-By: Codex）。OpenCode+ChatGPT Plusは規約上の許可を確認できず採用しなかった。development-disciplineの決定はcommit 15e2b37.

再開したClaude Codeセッションでは、system の `python3` が externally-managed のため pip が使えず、`uv venv .venv && uv pip install --python .venv/bin/python pypdf reportlab` でプロジェクト専用venvを作って導入した。reportlabはpillow・charset-normalizerを必須の推移依存として持ち込む（reportlab 5.0.1のRequires-Distで確認、extraではなく必須）。これらはreportlab自体の要件であり、個別に選定した追加依存ではない。

### 解釈

検証したいのはPDF分割機能と初回の自律ループ運用である。実装完了だけでは、特集が学習に適した投入単位かは判断できない。

本実装はPRDの要求全体ではなく、初回に必要な最小経路に絞った。あいまい一致の候補提示（FR-3が望ましい機能とする部分）は実装せず、完全一致／不一致の二値判定のみとした。境界確認の「層」は選択した`split_level`一段のみを対象とする簡略化とし、複数階層をまたぐ層分けは扱っていない。1境界あたりの確認表示に必要な縮小画像（FR-3）は、承認済み依存にPDFラスタライザが含まれないため実装せず、ページ本文の先頭行テキストで代替した。分割PDFの実出力は、人手確認済みの明示的な合図（`--confirm-reviewed`）を要求するゲート付きで実装し、確認プロセス自体（どの境界をどう承認したかの記録）はスコープ外とした。これらは実装完了の判断を「本タスクの受入条件を満たす」に限定しており、PRD全体の充足を意味しない。

### 適用範囲

この課題で実物PDFを確認する場合に限る。内容を保存せず、結果の要約だけを記録する。