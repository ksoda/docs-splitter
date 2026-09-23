"""合成PDFフィクスチャの生成スクリプト。

再現可能な合成テストPDF (`tests/data/sample_magazine.pdf`) を作る。
本文はreportlabで描画し（pypdfはテキスト描画を持たないため）、
ページの組み立てと書き出しはpypdfで行う。
再生成する場合: `.venv/bin/python tests/fixtures/make_sample_pdf.py`
"""

from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import registerFont
from reportlab.pdfgen import canvas

FONT_NAME = "HeiseiMin-W3"
registerFont(UnicodeCIDFont(FONT_NAME))

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_magazine.pdf"

# (page text lines,) — 1行目が境界照合に使う「照合文字列」になる。
PAGES: tuple[tuple[str, ...], ...] = (
    ("前付け", "雑誌の表紙・目次ページ。"),
    ("特集A", "特集Aの扉ページ。"),
    ("特集A 第1章", "特集A内の第1章本文。"),
    ("特集B", "特集Bの扉ページ。"),
    ("特集B 第1章", "特集B内の第1章本文。"),
)


def _render_page(lines: tuple[str, ...]) -> bytes:
    buffer = io.BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=A4)
    pdf_canvas.setFont(FONT_NAME, 14)
    _, height = A4
    y = height - 72
    for line in lines:
        pdf_canvas.drawString(72, y, line)
        y -= 20
    pdf_canvas.showPage()
    pdf_canvas.save()
    return buffer.getvalue()


def build_sample_pdf(output_path: Path = OUTPUT_PATH) -> Path:
    writer = PdfWriter()
    for lines in PAGES:
        page_bytes = _render_page(lines)
        reader = PdfReader(io.BytesIO(page_bytes))
        writer.add_page(reader.pages[0])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)
    return output_path


if __name__ == "__main__":
    path = build_sample_pdf()
    print(f"wrote {path}")
