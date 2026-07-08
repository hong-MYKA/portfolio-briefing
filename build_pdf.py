# -*- coding: utf-8 -*-
"""
保有株ポートフォリオ・デイリーブリーフィング PDF生成スクリプト(Remote Routine用・汎用版)

使い方:
    python3 build_pdf.py data.json output.pdf

data.json のスキーマ:
{
  "date_str": "2026年7月10日",
  "exec_summary": "エグゼクティブサマリー本文",
  "fund_lag_note": "基準価額タイムラグ等の注意書き(不要なら空文字でも可)",
  "holdings": [
    {
      "name": "銘柄名",
      "code": "コード",
      "price": "36,714円",
      "change": "-483円 (-1.3%)",
      "positive": false,
      "base_date": "基準日 2026/7/9",
      "detail": "詳細解説文",
      "note": "注目点"
    }, ...
  ],
  "news": [
    {
      "date": "2026/7/9",
      "source": "出典",
      "headline": "見出し",
      "summary": "本文要約",
      "impact": "ポートフォリオへの影響",
      "sentiment": "警戒" | "好材料" | "要注視"
    }, ...
  ]
}

このスクリプトは reportlab で日本語+ASCII混在テキストを正しく描画するため、
ASCII文字(数字・記号)だけを Liberation Sans フォントで別途描画するヘルパーを持つ。
DroidSansFallbackFull.ttf や標準CJKフォントだけで数字/記号を描画すると tofu になる
既知の問題を回避するための対応。
"""
import sys
import json
import re
import shutil
import subprocess
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, NextPageTemplate
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER


# ---------- フォント検出 ----------
def _find_font(candidates, fc_match_pattern=None):
    for c in candidates:
        if Path(c).exists():
            return c
    if fc_match_pattern:
        try:
            out = subprocess.check_output(
                ["fc-match", "--format=%{file}", fc_match_pattern]
            ).decode().strip()
            if out and Path(out).exists():
                return out
        except Exception:
            pass
    raise FileNotFoundError(f"フォントが見つかりません: {candidates}")


JP_FONT_PATH = _find_font(
    ["/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"],
    fc_match_pattern="Noto Sans CJK JP",
)
LATIN_REG_PATH = _find_font(
    ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"],
    fc_match_pattern="Liberation Sans",
)
LATIN_BOLD_PATH = _find_font(
    ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
     "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"],
    fc_match_pattern="Liberation Sans:style=Bold",
)

pdfmetrics.registerFont(TTFont("JPFont", JP_FONT_PATH))
pdfmetrics.registerFont(TTFont("LatinReg", LATIN_REG_PATH))
pdfmetrics.registerFont(TTFont("LatinBold", LATIN_BOLD_PATH))

NAVY = colors.HexColor("#0f2a4a")
GOLD = colors.HexColor("#c9962b")
GREEN = colors.HexColor("#1e7d32")
GREEN_BG = colors.HexColor("#e6f4ea")
RED = colors.HexColor("#c62828")
RED_BG = colors.HexColor("#fdecea")
AMBER = colors.HexColor("#b26a00")
AMBER_BG = colors.HexColor("#fff4e0")
GRAY_BG = colors.HexColor("#f2f4f7")
TEXT_DARK = colors.HexColor("#1a1a1a")


def _split_ascii_runs(text):
    """テキストをASCIIランと非ASCIIランに分割して (text, is_ascii) のリストを返す"""
    runs = []
    cur = ""
    cur_ascii = None
    for ch in text:
        is_ascii = (ord(ch) < 128)
        if cur_ascii is None:
            cur_ascii = is_ascii
            cur = ch
        elif is_ascii == cur_ascii:
            cur += ch
        else:
            runs.append((cur, cur_ascii))
            cur = ch
            cur_ascii = is_ascii
    if cur:
        runs.append((cur, cur_ascii))
    return runs


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def mixed_font(text, bold=False):
    """日本語とASCIIが混在するテキストに、ASCII部分だけLatinフォントタグを付与する。
    ASCII/非ASCIIのランに分割してからエスケープするため、エンティティ化による
    プレースホルダー衝突が起きない。"""
    text = str(text)
    latin_tag = "LatinBold" if bold else "LatinReg"
    out = []
    for chunk, is_ascii in _split_ascii_runs(text):
        chunk_escaped = esc(chunk)
        if is_ascii:
            out.append(f'<font name="{latin_tag}">{chunk_escaped}</font>')
        else:
            out.append(chunk_escaped)
    return "".join(out)


def split_runs(text):
    return _split_ascii_runs(text)


# ---------- 段落スタイル ----------
def pstyle(name, size=10, leading=14, color=TEXT_DARK, align=TA_LEFT, font="JPFont"):
    return ParagraphStyle(
        name, fontName=font, fontSize=size, leading=leading, textColor=color, alignment=align
    )


style_body = pstyle("body", 9.5, 14.5)
style_body_bold = pstyle("body_bold", 9.5, 14.5)
style_h2 = pstyle("h2", 14, 18, color=NAVY)
style_h3 = pstyle("h3", 11.5, 15, color=colors.white)
style_small = pstyle("small", 8.3, 12, color=colors.HexColor("#555555"))
style_news_head = pstyle("news_head", 11, 15, color=TEXT_DARK)
style_news_meta = pstyle("news_meta", 8.3, 12, color=colors.HexColor("#666666"))

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm


def P(text, style=style_body, bold=False):
    return Paragraph(mixed_font(text, bold=bold), style)


def make_header_footer(date_str):
    def draw_header_footer(canvas, doc):
        canvas.saveState()
        banner_h = 26 * mm
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - banner_h, PAGE_W, banner_h, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(0, PAGE_H - banner_h - 1.6 * mm, PAGE_W, 1.6 * mm, fill=1, stroke=0)

        canvas.setFillColor(colors.white)
        canvas.setFont("JPFont", 17)
        title_y = PAGE_H - 13 * mm
        canvas.drawString(MARGIN, title_y, "保有株ポートフォリオ・デイリーブリーフィング")

        x = MARGIN
        y2 = title_y - 7.5 * mm
        for text, is_ascii in split_runs(date_str):
            font = "LatinReg" if is_ascii else "JPFont"
            canvas.setFont(font, 10.5)
            canvas.drawString(x, y2, text)
            x += canvas.stringWidth(text, font, 10.5)

        footer_y = 10 * mm
        canvas.setStrokeColor(colors.HexColor("#cccccc"))
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN, footer_y + 5 * mm, PAGE_W - MARGIN, footer_y + 5 * mm)

        canvas.setFillColor(colors.HexColor("#555555"))
        footer_left = "保有株ポートフォリオ・デイリーブリーフィング　" + date_str
        x = MARGIN
        for text, is_ascii in split_runs(footer_left):
            font = "LatinReg" if is_ascii else "JPFont"
            canvas.setFont(font, 8)
            canvas.drawString(x, footer_y, text)
            x += canvas.stringWidth(text, font, 8)

        page_num_text = f"- {doc.page} -"
        canvas.setFont("LatinReg", 8)
        canvas.drawRightString(PAGE_W - MARGIN, footer_y, page_num_text)
        canvas.restoreState()
    return draw_header_footer


def price_pill_table(change_text, positive):
    bg = GREEN_BG if positive else RED_BG
    fg = GREEN if positive else RED
    t = Table([[P(change_text, pstyle("pill", 9.5, 13, color=fg, align=TA_CENTER))]],
              colWidths=[32 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.6, fg),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return t


def sentiment_tag(label):
    mapping = {
        "警戒": (RED, "警戒"),
        "好材料": (GREEN, "好材料"),
        "要注視": (AMBER, "要注視"),
    }
    color_, text = mapping.get(label, (AMBER, label))
    t = Table([[P(text, pstyle("tagtxt", 8, 11, color=colors.white, align=TA_CENTER))]], colWidths=[20 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return t


def callout_box(title, body_text, color_, bg_):
    inner = Table(
        [[P(title, pstyle("ctitle", 9, 13, color=color_), bold=True)],
         [P(body_text, style_body)]],
        colWidths=[164 * mm]
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_),
        ("BOX", (0, 0), (-1, -1), 0.7, color_),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return inner


def navy_header_bar(text):
    t = Table([[P(text, style_h3)]], colWidths=[178 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def build(data, output_path):
    date_str = data["date_str"]
    holdings = data["holdings"]
    news = data["news"]
    exec_summary = data.get("exec_summary", "")
    fund_lag_note = data.get("fund_lag_note", "")

    doc = BaseDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=32 * mm, bottomMargin=20 * mm,
    )
    frame = Frame(MARGIN, 20 * mm, PAGE_W - 2 * MARGIN, PAGE_H - 32 * mm - 20 * mm, id="normal")
    template = PageTemplate(id="main", frames=[frame], onPage=make_header_footer(date_str))
    doc.addPageTemplates([template])

    story = []

    story.append(P("1. エグゼクティブサマリー", style_h2))
    story.append(Spacer(1, 4 * mm))
    story.append(P(exec_summary, style_body))
    if fund_lag_note:
        story.append(Spacer(1, 3 * mm))
        story.append(callout_box("基準価額のタイムラグに関する注意", fund_lag_note, AMBER, AMBER_BG))
    story.append(Spacer(1, 8 * mm))

    story.append(P("2. 保有銘柄価格サマリー", style_h2))
    story.append(Spacer(1, 4 * mm))
    table_rows = [[
        P("銘柄名 / コード", style_body_bold, bold=True),
        P("価格(基準価額 / 株価)", style_body_bold, bold=True),
        P("前日比", style_body_bold, bold=True),
    ]]
    for h in holdings:
        name_cell = P(f"{h['name']}\n【{h['code']}】", style_body)
        price_cell = P(h["price"], pstyle("pricecell", 10, 14), bold=True)
        pill = price_pill_table(h["change"], h["positive"])
        table_rows.append([name_cell, price_cell, pill])

    summary_table = Table(table_rows, colWidths=[90 * mm, 42 * mm, 46 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_BG]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10 * mm))

    story.append(P("3. 重要ニュース TOP5", style_h2))
    story.append(Spacer(1, 4 * mm))
    for i, n in enumerate(news, start=1):
        badge = Table([[P(str(i), pstyle("badge", 12, 14, color=colors.white, align=TA_CENTER), bold=True)]],
                       colWidths=[8 * mm], rowHeights=[8 * mm])
        badge.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NAVY),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        headline_para = P(n["headline"], style_news_head, bold=True)
        tag = sentiment_tag(n["sentiment"])
        head_row = Table([[badge, headline_para, tag]], colWidths=[10 * mm, 148 * mm, 20 * mm])
        head_row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (0, 0), 0),
            ("LEFTPADDING", (1, 0), (1, 0), 6),
        ]))
        story.append(head_row)
        story.append(Spacer(1, 1.5 * mm))
        story.append(P(f"{n['source']}　|　{n['date']}", style_news_meta))
        story.append(Spacer(1, 1.5 * mm))
        story.append(P(n["summary"], style_body))
        story.append(Spacer(1, 2 * mm))
        story.append(callout_box("ポートフォリオへの影響", n["impact"], NAVY, colors.HexColor("#eef2f7")))
        story.append(Spacer(1, 6 * mm))

    story.append(NextPageTemplate("main"))
    story.append(P("4. 銘柄別 詳細レポート", style_h2))
    story.append(Spacer(1, 4 * mm))
    for h in holdings:
        story.append(navy_header_bar(f"{h['name']}　【{h['code']}】"))
        story.append(Spacer(1, 3 * mm))
        price_row = Table(
            [[P(h["price"], pstyle("bigprice", 15, 18, color=NAVY), bold=True),
              price_pill_table(h["change"], h["positive"])]],
            colWidths=[100 * mm, 40 * mm]
        )
        price_row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        story.append(price_row)
        story.append(Spacer(1, 1 * mm))
        story.append(P(h["base_date"], style_small))
        story.append(Spacer(1, 3 * mm))
        story.append(P(h["detail"], style_body))
        story.append(Spacer(1, 3 * mm))
        story.append(callout_box("注目点", h["note"], GOLD, colors.HexColor("#fbf3e3")))
        story.append(Spacer(1, 8 * mm))

    doc.build(story)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("使い方: python3 build_pdf.py data.json output.pdf", file=sys.stderr)
        sys.exit(1)
    data_path, output_path = sys.argv[1], sys.argv[2]
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    build(data, output_path)
    print(f"生成完了: {output_path}")
