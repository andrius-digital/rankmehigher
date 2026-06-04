from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib import colors

OUTPUT = "/Users/markaslevinas/Downloads/rankmehigher/QTA_Tax_Keyword_Report.pdf"

DARK = HexColor("#1a1a2e")
PRIMARY = HexColor("#16213e")
ACCENT = HexColor("#0f3460")
HIGHLIGHT = HexColor("#e94560")
LIGHT_BG = HexColor("#f8f9fa")
WHITE = HexColor("#ffffff")
GRAY = HexColor("#6c757d")
LIGHT_GRAY = HexColor("#e9ecef")
GREEN = HexColor("#28a745")
BLUE = HexColor("#0066cc")
ORANGE = HexColor("#fd7e14")
DARK_TEXT = HexColor("#212529")

styles = {
    "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=28, textColor=WHITE, alignment=TA_LEFT, leading=34),
    "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=14, textColor=HexColor("#adb5bd"), alignment=TA_LEFT, leading=20),
    "meta": ParagraphStyle("meta", fontName="Helvetica", fontSize=10, textColor=HexColor("#adb5bd"), alignment=TA_LEFT, leading=14),
    "section_title": ParagraphStyle("section_title", fontName="Helvetica-Bold", fontSize=18, textColor=DARK, leading=24, spaceBefore=20, spaceAfter=6),
    "section_tag": ParagraphStyle("section_tag", fontName="Helvetica-Bold", fontSize=9, textColor=WHITE, leading=12),
    "subsection": ParagraphStyle("subsection", fontName="Helvetica-Bold", fontSize=13, textColor=ACCENT, leading=18, spaceBefore=14, spaceAfter=4),
    "keyword": ParagraphStyle("keyword", fontName="Helvetica", fontSize=10, textColor=DARK_TEXT, leading=14),
    "keyword_bold": ParagraphStyle("keyword_bold", fontName="Helvetica-Bold", fontSize=10, textColor=DARK_TEXT, leading=14),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10, textColor=DARK_TEXT, leading=16, spaceAfter=6),
    "body_bold": ParagraphStyle("body_bold", fontName="Helvetica-Bold", fontSize=10, textColor=DARK_TEXT, leading=16, spaceAfter=6),
    "table_header": ParagraphStyle("table_header", fontName="Helvetica-Bold", fontSize=9, textColor=WHITE, leading=13),
    "table_cell": ParagraphStyle("table_cell", fontName="Helvetica", fontSize=9, textColor=DARK_TEXT, leading=13),
    "table_cell_bold": ParagraphStyle("table_cell_bold", fontName="Helvetica-Bold", fontSize=9, textColor=DARK_TEXT, leading=13),
    "step_num": ParagraphStyle("step_num", fontName="Helvetica-Bold", fontSize=11, textColor=WHITE, leading=14),
    "step_text": ParagraphStyle("step_text", fontName="Helvetica", fontSize=10, textColor=DARK_TEXT, leading=15),
    "footer": ParagraphStyle("footer", fontName="Helvetica", fontSize=8, textColor=GRAY, alignment=TA_CENTER, leading=10),
    "badge": ParagraphStyle("badge", fontName="Helvetica-Bold", fontSize=8, textColor=WHITE, alignment=TA_CENTER, leading=11),
}


def add_header_footer(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFillColor(ACCENT)
        canvas.rect(0, letter[1] - 4, letter[0], 4, fill=1, stroke=0)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRAY)
        canvas.drawString(72, letter[1] - 28, "QTA Tax — SEO Keyword Research Report")
        canvas.drawRightString(letter[0] - 72, letter[1] - 28, f"Page {doc.page}")
        canvas.setStrokeColor(LIGHT_GRAY)
        canvas.line(72, letter[1] - 34, letter[0] - 72, letter[1] - 34)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRAY)
    canvas.drawCentredString(letter[0] / 2, 30, "Prepared by RankMeHigher  |  Confidential  |  May 27, 2026")
    canvas.restoreState()


def cover_page():
    elements = []
    cover_bg = Table([[""]], colWidths=[letter[0]], rowHeights=[letter[1]])
    cover_bg.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    accent_bar = Table([[""]], colWidths=[letter[0] - 144], rowHeights=[4])
    accent_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HIGHLIGHT),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    elements.append(Spacer(1, 2.5 * inch))
    elements.append(accent_bar)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("SEO Keyword", styles["title"]))
    elements.append(Paragraph("Research Report", styles["title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Keyword Opportunities for qtatax.com/blog", styles["subtitle"]))
    elements.append(Spacer(1, 30))

    divider = Table([[""]], colWidths=[60], rowHeights=[2])
    divider.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HIGHLIGHT),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(divider)
    elements.append(Spacer(1, 16))

    elements.append(Paragraph("Client: QTA Tax", styles["meta"]))
    elements.append(Paragraph("Website: qtatax.com", styles["meta"]))
    elements.append(Paragraph("Date: May 27, 2026", styles["meta"]))
    elements.append(Paragraph("Prepared by: RankMeHigher", styles["meta"]))
    elements.append(PageBreak())
    return elements


def section_header(number, title, tag_color, tag_text):
    elements = []
    tag_table = Table(
        [[Paragraph(f"  SECTION {number}  |  {tag_text}  ", styles["section_tag"])]],
        colWidths=[None],
    )
    tag_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), tag_color),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(tag_table)
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(title, styles["section_title"]))
    sep = HRFlowable(width="100%", thickness=1.5, color=tag_color, spaceBefore=2, spaceAfter=10)
    elements.append(sep)
    return elements


def keyword_table(keywords, col_count=2):
    rows = []
    per_col = (len(keywords) + col_count - 1) // col_count
    cols = []
    for c in range(col_count):
        start = c * per_col
        end = min(start + per_col, len(keywords))
        cols.append(keywords[start:end])

    max_rows = max(len(col) for col in cols)
    for r in range(max_rows):
        row = []
        for c in range(col_count):
            if r < len(cols[c]):
                bullet = Paragraph(f'<font color="#e94560">●</font>  {cols[c][r]}', styles["keyword"])
                row.append(bullet)
            else:
                row.append("")
        rows.append(row)

    col_width = (letter[0] - 144) / col_count
    t = Table(rows, colWidths=[col_width] * col_count)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    return t


def build_report():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=letter,
        topMargin=50,
        bottomMargin=50,
        leftMargin=72,
        rightMargin=72,
    )

    story = []

    # ── SECTION 1 ──
    story.extend(section_header("01", "High-Ranking Potential", GREEN, "LOCAL + LOW COMPETITION"))
    story.append(Paragraph("Tax Preparation + Location", styles["subsection"]))
    story.append(keyword_table([
        "tax preparation Oak Brook IL",
        "tax preparer near Oak Brook",
        "tax services Hinsdale IL",
        "tax preparation Naperville IL",
        "tax services Elmhurst IL",
        "tax preparer Lombard IL",
        "tax services Burr Ridge IL",
        "tax firm DuPage County",
        "CPA near Oak Brook IL",
        "tax accountant Chicagoland",
    ]))
    story.append(Spacer(1, 14))
    story.append(Paragraph("IRS / Enrolled Agent + Location", styles["subsection"]))
    story.append(keyword_table([
        "IRS Enrolled Agent Oak Brook",
        "enrolled agent near me Chicagoland",
        "IRS representation Oak Brook IL",
        "IRS audit help DuPage County",
    ]))
    story.append(PageBreak())

    # ── SECTION 2 ──
    story.extend(section_header("02", "Strong Ranking Potential", BLUE, "NICHE INDUSTRY + SERVICE"))

    story.append(Paragraph("Real Estate", styles["subsection"]))
    story.append(keyword_table([
        "1031 exchange tax accountant Illinois",
        "real estate tax planning Chicago suburbs",
        "1031 exchange CPA Oak Brook",
        "rental property tax deductions Illinois",
        "real estate investor tax preparer near me",
        "depreciation tax strategy real estate",
    ]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Cannabis", styles["subsection"]))
    story.append(keyword_table([
        "cannabis tax accountant Illinois",
        "280E tax compliance Illinois",
        "cannabis business tax preparation Chicago",
        "marijuana dispensary bookkeeping Illinois",
    ]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Dental Practices", styles["subsection"]))
    story.append(keyword_table([
        "dental practice tax services Illinois",
        "dentist tax accountant Chicago",
        "dental office bookkeeping DuPage County",
    ]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Healthcare", styles["subsection"]))
    story.append(keyword_table([
        "healthcare tax services Chicagoland",
        "medical practice accountant Oak Brook",
        "doctor tax preparation Illinois",
    ]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Law Firms", styles["subsection"]))
    story.append(keyword_table([
        "law firm accounting Illinois",
        "attorney tax services Oak Brook",
        "law firm bookkeeping Chicago suburbs",
    ]))
    story.append(PageBreak())

    # ── SECTION 3 ──
    story.extend(section_header("03", "Medium Competition Keywords", ORANGE, "SERVICE-SPECIFIC LONG-TAIL"))

    story.append(Paragraph("Bookkeeping &amp; Payroll", styles["subsection"]))
    story.append(keyword_table([
        "small business bookkeeping Oak Brook IL",
        "payroll services DuPage County",
        "bookkeeping for small business Chicagoland",
    ]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Capital Gains", styles["subsection"]))
    story.append(keyword_table([
        "capital gains tax help Illinois",
        "capital gains tax accountant Chicago",
        "how to reduce capital gains tax Illinois",
    ]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Tax Planning", styles["subsection"]))
    story.append(keyword_table([
        "year-round tax planning Illinois",
        "proactive tax planning small business",
        "tax planning strategies for high earners Illinois",
        "trust accounting services Illinois",
    ]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Filing-Specific", styles["subsection"]))
    story.append(keyword_table([
        "W-2 filing services Illinois",
        "1099 tax preparation Oak Brook",
        "K-1 filing help Chicago suburbs",
        "multi-state tax return preparation",
    ]))
    story.append(PageBreak())

    # ── SECTION 4 ──
    story.extend(section_header("04", "Blog Content Keyword Ideas", ACCENT, "INFORMATIONAL / TOP-OF-FUNNEL"))
    story.append(Paragraph("Target these keywords with dedicated blog posts to capture organic search traffic:", styles["body"]))
    story.append(Spacer(1, 8))

    blog_data = [
        ["what is a 1031 exchange and how does it work", "Educational"],
        ["tax deductions for small business owners 2026", "Seasonal"],
        ["how to reduce capital gains tax on real estate", "Problem-solving"],
        ["estimated tax payment deadlines 2026", "Seasonal"],
        ["cannabis 280E tax deduction explained", "Niche educational"],
        ["dental practice tax deductions checklist", "Niche list"],
        ["do I need an enrolled agent or a CPA", "Comparison"],
        ["real estate depreciation recapture explained", "Educational"],
        ["tax benefits of hiring a bookkeeper", "Awareness"],
        ["how much does a tax accountant cost in Illinois", "Transactional"],
        ["best tax strategies for landlords in Illinois", "Problem-solving"],
        ["new Illinois tax law changes 2026", "News / seasonal"],
        ["payroll tax mistakes small businesses make", "Problem-solving"],
        ["trust tax return filing requirements Illinois", "Specific"],
        ["how to choose a tax preparer in Chicago", "Local buying guide"],
    ]

    intent_colors = {
        "Educational": GREEN,
        "Seasonal": ORANGE,
        "Problem-solving": HIGHLIGHT,
        "Niche educational": BLUE,
        "Niche list": BLUE,
        "Comparison": HexColor("#6f42c1"),
        "Awareness": HexColor("#20c997"),
        "Transactional": HexColor("#d63384"),
        "News / seasonal": ORANGE,
        "Specific": ACCENT,
        "Local buying guide": GREEN,
    }

    header_row = [
        Paragraph("Keyword", styles["table_header"]),
        Paragraph("Search Intent", styles["table_header"]),
    ]
    table_rows = [header_row]
    for kw, intent in blog_data:
        badge_color = intent_colors.get(intent, GRAY)
        badge = Table(
            [[Paragraph(intent, styles["badge"])]],
            colWidths=[None],
        )
        badge.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), badge_color),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("ROUNDEDCORNERS", [3, 3, 3, 3]),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        table_rows.append([
            Paragraph(kw, styles["table_cell"]),
            badge,
        ])

    blog_table = Table(table_rows, colWidths=[320, 120])
    blog_style = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]
    for i in range(1, len(table_rows)):
        if i % 2 == 0:
            blog_style.append(("BACKGROUND", (0, i), (-1, i), LIGHT_BG))
    blog_table.setStyle(TableStyle(blog_style))
    story.append(blog_table)

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print(f"PDF saved to: {OUTPUT}")


if __name__ == "__main__":
    build_report()
