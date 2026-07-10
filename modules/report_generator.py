"""
Downloadable PDF audit report generation (ReportLab).

Produces a shareable artifact of the analysis: overall score,
per-category breakdown, and every flag with its evidence quote,
page reference, and recommendation.
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

from modules.agents import AnalysisResult

LEVEL_COLORS = {"HIGH": colors.HexColor("#e74c3c"), "MED": colors.HexColor("#f39c12"), "LOW": colors.HexColor("#f1c40f")}


def build_report(result: AnalysisResult, source_filename: str = "lease.pdf") -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, topMargin=0.7 * inch, bottomMargin=0.7 * inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontSize=20)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=14)
    body = styles["BodyText"]
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=9, textColor=colors.grey)

    story = []
    story.append(Paragraph("LeaseScan AI &mdash; Audit Report", title_style))
    story.append(
        Paragraph(
            f"Source: {source_filename} &nbsp;|&nbsp; Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            small,
        )
    )
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"Overall Score: {result.overall_score}/100", h2))
    story.append(Paragraph(result.summary, body))
    if result.used_ocr:
        story.append(Paragraph("Note: this document required OCR to extract text (scanned pages detected).", small))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", color=colors.lightgrey))

    # Category score table
    story.append(Paragraph("Category Scores", h2))
    cat_data = [["Category", "Score", "Flags"]] + [
        [a.agent_name, f"{a.category_score}/100", str(len(a.flags))] for a in result.agents
    ]
    cat_table = Table(cat_data, colWidths=[2.6 * inch, 1.5 * inch, 1.5 * inch])
    cat_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(cat_table)
    story.append(Spacer(1, 14))

    # Findings per agent
    story.append(Paragraph("Findings & Evidence", h2))
    if not result.all_flags:
        story.append(Paragraph("No significant issues were flagged.", body))

    for agent in result.agents:
        if not agent.flags:
            continue
        story.append(Paragraph(agent.agent_name, ParagraphStyle("AgentHeader", parent=styles["Heading3"], spaceBefore=10)))
        for f in agent.flags:
            level_color = LEVEL_COLORS.get(f.level, colors.grey)
            story.append(
                Paragraph(
                    f'<font color="{level_color.hexval()}"><b>[{f.level}]</b></font> {f.issue} '
                    f'<font color="grey" size=8>(confidence {f.confidence}%)</font>',
                    body,
                )
            )
            story.append(Paragraph(f.risk, body))
            if f.evidence_quote:
                story.append(
                    Paragraph(
                        f'Evidence (Page {f.evidence_page}): &ldquo;{f.evidence_quote}&rdquo;',
                        ParagraphStyle("Quote", parent=body, leftIndent=12, textColor=colors.HexColor("#555555")),
                    )
                )
            if f.recommendation:
                story.append(Paragraph(f"<b>Recommendation:</b> {f.recommendation}", body))
            story.append(Spacer(1, 8))

    doc.build(story)
    return buffer.getvalue()
