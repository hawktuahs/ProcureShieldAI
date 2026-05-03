"""
PDF evaluation report generator using ReportLab.
Produces a professional, auditable report suitable for government procurement sign-off.
"""

import io
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Colour palette
C_PASS = colors.HexColor("#22C55E")
C_FAIL = colors.HexColor("#EF4444")
C_REVIEW = colors.HexColor("#F59E0B")
C_OVERRIDE = colors.HexColor("#3B82F6")
C_HEADER = colors.HexColor("#1e3a5f")
C_LIGHT_BLUE = colors.HexColor("#EFF6FF")
C_LIGHT_GREY = colors.HexColor("#F9FAFB")
C_BORDER = colors.HexColor("#E5E7EB")

VERDICT_COLORS = {
    "pass": C_PASS,
    "fail": C_FAIL,
    "needs_review": C_REVIEW,
    "eligible": C_PASS,
    "not_eligible": C_FAIL,
}

VERDICT_LABELS = {
    "pass": "PASS",
    "fail": "FAIL",
    "needs_review": "REVIEW",
    "eligible": "ELIGIBLE",
    "not_eligible": "NOT ELIGIBLE",
}

TYPE_COLORS = {
    "financial": colors.HexColor("#DBEAFE"),
    "technical": colors.HexColor("#D1FAE5"),
    "compliance": colors.HexColor("#FEF3C7"),
    "documentation": colors.HexColor("#F3E8FF"),
}


def _styles():
    base = getSampleStyleSheet()
    custom = {}

    def s(name, **kwargs):
        custom[name] = ParagraphStyle(name, parent=base["Normal"], **kwargs)

    s("Title", fontSize=22, textColor=colors.white, spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica-Bold")
    s("Subtitle", fontSize=11, textColor=colors.HexColor("#93C5FD"), spaceAfter=2, alignment=TA_CENTER)
    s("SectionHeader", fontSize=13, textColor=C_HEADER, spaceBefore=12, spaceAfter=6, fontName="Helvetica-Bold")
    s("Body", fontSize=9, textColor=colors.HexColor("#374151"), spaceAfter=4, leading=13)
    s("Small", fontSize=8, textColor=colors.HexColor("#6B7280"), leading=11)
    s("TableCell", fontSize=8, textColor=colors.HexColor("#374151"), leading=11)
    s("TableCellBold", fontSize=8, textColor=colors.HexColor("#111827"), leading=11, fontName="Helvetica-Bold")
    s("VerdictLabel", fontSize=8, textColor=colors.white, alignment=TA_CENTER, fontName="Helvetica-Bold")
    s("Evidence", fontSize=7.5, textColor=colors.HexColor("#4B5563"), leading=11, leftIndent=6)
    s("CriterionDesc", fontSize=8.5, textColor=colors.HexColor("#1F2937"), leading=12)
    return custom


def _verdict_cell(verdict: Optional[str], human_verdict: Optional[str] = None) -> Table:
    """Render a small coloured verdict badge."""
    effective = human_verdict or verdict or "needs_review"
    label = VERDICT_LABELS.get(effective, effective.upper())
    col = VERDICT_COLORS.get(effective, C_REVIEW)

    override_note = ""
    if human_verdict and human_verdict != verdict:
        override_note = "★ Override"

    styles = _styles()
    data = [[Paragraph(label, styles["VerdictLabel"])]]
    if override_note:
        data.append([Paragraph(override_note, ParagraphStyle("ov", fontSize=6, textColor=C_OVERRIDE, alignment=TA_CENTER))])

    t = Table(data, colWidths=[2.2 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), col),
        ("ROUNDEDCORNERS", [3]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def generate_report(
    tender: dict,
    criteria: list[dict],
    bidders: list[dict],
    evaluations_by_bidder: dict[int, list[dict]],
) -> bytes:
    """
    Build and return the full evaluation PDF as bytes.

    Args:
        tender: Tender record dict (id, name, upload_time, status)
        criteria: List of Criterion dicts
        bidders: List of Bidder dicts (id, name, overall_verdict, overall_reasoning, status)
        evaluations_by_bidder: {bidder_id: [CriterionEvaluation dicts joined with criterion data]}
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = _styles()
    story = []

    def hr():
        return HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceAfter=8)

    # -----------------------------------------------------------------------
    # COVER PAGE
    # -----------------------------------------------------------------------
    header_data = [[
        Paragraph("TenderEval AI", styles["Title"]),
        Paragraph("AI-Powered Procurement Evaluation Report", styles["Subtitle"]),
    ]]
    header_table = Table([[
        Paragraph("TenderEval AI", styles["Title"]),
    ]], colWidths=[17 * cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_HEADER),
        ("TOPPADDING", (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3 * cm))

    subtitle_table = Table([[
        Paragraph("AI-Powered Procurement Evaluation Report", ParagraphStyle(
            "st", fontSize=10, textColor=C_HEADER, alignment=TA_CENTER
        ))
    ]], colWidths=[17 * cm])
    subtitle_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_LIGHT_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(subtitle_table)
    story.append(Spacer(1, 0.6 * cm))

    # Summary stats
    eligible = sum(1 for b in bidders if b.get("overall_verdict") == "eligible")
    not_eligible = sum(1 for b in bidders if b.get("overall_verdict") == "not_eligible")
    needs_review = sum(1 for b in bidders if b.get("overall_verdict") == "needs_review")

    summary_data = [
        ["Tender", tender["name"]],
        ["Report Generated", datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")],
        ["Total Bidders", str(len(bidders))],
        ["Eligible", str(eligible)],
        ["Not Eligible", str(not_eligible)],
        ["Needs Review", str(needs_review)],
        ["Criteria Extracted", str(len(criteria))],
    ]
    summary_table = Table(summary_data, colWidths=[5 * cm, 12 * cm])
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), C_HEADER),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, C_LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(summary_table)
    story.append(PageBreak())

    # -----------------------------------------------------------------------
    # SECTION 1 — EXTRACTED CRITERIA
    # -----------------------------------------------------------------------
    story.append(Paragraph("1. Eligibility Criteria", styles["SectionHeader"]))
    story.append(hr())

    criteria_data = [["#", "Type", "Description", "Threshold", "Mandatory", "Confidence"]]
    for i, c in enumerate(criteria, 1):
        criteria_data.append([
            str(i),
            c["criterion_type"].title(),
            Paragraph(c["description"], styles["TableCell"]),
            c.get("threshold_value") or "—",
            "Yes" if c.get("is_mandatory") else "No",
            f"{float(c.get('extraction_confidence', 0)) * 100:.0f}%",
        ])

    ct = Table(criteria_data, colWidths=[0.6 * cm, 2.5 * cm, 6.5 * cm, 3 * cm, 1.8 * cm, 1.8 * cm])
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(ct)
    story.append(PageBreak())

    # -----------------------------------------------------------------------
    # SECTION 2 — BIDDER SUMMARY MATRIX
    # -----------------------------------------------------------------------
    story.append(Paragraph("2. Bidder Summary Matrix", styles["SectionHeader"]))
    story.append(hr())

    # Limit matrix columns to top 20 criteria (mandatory first) for readability
    MAX_MATRIX_COLS = 20
    matrix_criteria = sorted(criteria, key=lambda c: (not c.get("is_mandatory", False), c.get("id", 0)))
    matrix_truncated = len(criteria) > MAX_MATRIX_COLS
    if matrix_truncated:
        matrix_criteria = matrix_criteria[:MAX_MATRIX_COLS]

    if matrix_truncated:
        story.append(Paragraph(
            f"<i>Showing top {MAX_MATRIX_COLS} criteria (mandatory first) of {len(criteria)} total. "
            "Full details per bidder are in Section 3.</i>",
            styles["Small"]
        ))
        story.append(Spacer(1, 0.2 * cm))

    # Summary table when many criteria (bidder-level pass/fail/review counts)
    if len(criteria) > MAX_MATRIX_COLS:
        summary_matrix_header = ["Bidder", "Overall", "Pass", "Fail", "Review", "Score"]
        summary_matrix_data = [summary_matrix_header]
        for bidder in bidders:
            bid_evals = evaluations_by_bidder.get(bidder["id"], [])
            eval_by_criterion = {e["criterion_id"]: e for e in bid_evals}
            passed = sum(1 for c in criteria
                         if eval_by_criterion.get(c["id"]) and
                         (eval_by_criterion[c["id"]].get("human_verdict") or eval_by_criterion[c["id"]].get("verdict")) == "pass")
            failed = sum(1 for c in criteria
                         if eval_by_criterion.get(c["id"]) and
                         (eval_by_criterion[c["id"]].get("human_verdict") or eval_by_criterion[c["id"]].get("verdict")) == "fail")
            review_count = len(bid_evals) - passed - failed
            score = f"{round(passed / len(bid_evals) * 100)}%" if bid_evals else "—"
            overall_verdict = bidder.get("overall_verdict") or "needs_review"
            overall_label = VERDICT_LABELS.get(overall_verdict, overall_verdict.upper())
            summary_matrix_data.append([
                Paragraph(bidder["name"], styles["TableCellBold"]),
                Paragraph(overall_label, ParagraphStyle("ov2", fontSize=7, textColor=colors.white,
                                                         alignment=TA_CENTER, fontName="Helvetica-Bold")),
                str(passed), str(failed), str(review_count), score,
            ])
        smt = Table(summary_matrix_data, colWidths=[5 * cm, 2.5 * cm, 2 * cm, 2 * cm, 2 * cm, 2 * cm], repeatRows=1)
        smt_style = [
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGNMENT", (2, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT_GREY]),
        ]
        for row_idx, bidder in enumerate(bidders, 1):
            ov = bidder.get("overall_verdict") or "needs_review"
            smt_style.append(("BACKGROUND", (1, row_idx), (1, row_idx), VERDICT_COLORS.get(ov, C_REVIEW)))
        smt.setStyle(TableStyle(smt_style))
        story.append(smt)
        story.append(Spacer(1, 0.4 * cm))

    crit_headers = [Paragraph(c["description"][:35] + ("…" if len(c["description"]) > 35 else ""),
                               ParagraphStyle("ch", fontSize=7, textColor=colors.white, leading=9))
                     for c in matrix_criteria]
    matrix_header = [
        Paragraph("Bidder", ParagraphStyle("bh", fontSize=8, textColor=colors.white, fontName="Helvetica-Bold")),
        Paragraph("Overall", ParagraphStyle("oh", fontSize=8, textColor=colors.white, fontName="Helvetica-Bold")),
    ] + crit_headers

    crit_col_w = max(1.5 * cm, min(2.5 * cm, 14 * cm / max(len(matrix_criteria), 1)))
    col_widths = [4 * cm, 2.2 * cm] + [crit_col_w] * len(matrix_criteria)

    matrix_data = [matrix_header]
    for bidder in bidders:
        bid_evals = evaluations_by_bidder.get(bidder["id"], [])
        eval_by_criterion = {e["criterion_id"]: e for e in bid_evals}

        overall_verdict = bidder.get("overall_verdict") or "needs_review"
        overall_label = VERDICT_LABELS.get(overall_verdict, overall_verdict.upper())

        row = [
            Paragraph(bidder["name"], styles["TableCellBold"]),
            Paragraph(overall_label, ParagraphStyle("ov", fontSize=7, textColor=colors.white,
                                                     alignment=TA_CENTER, fontName="Helvetica-Bold")),
        ]
        for c in matrix_criteria:
            e = eval_by_criterion.get(c["id"])
            if e:
                effective = e.get("human_verdict") or e.get("verdict", "needs_review")
                label = VERDICT_LABELS.get(effective, "?")
                row.append(Paragraph(label, ParagraphStyle("mc", fontSize=7, textColor=colors.white,
                                                            alignment=TA_CENTER, fontName="Helvetica-Bold")))
            else:
                row.append(Paragraph("—", styles["Small"]))
        matrix_data.append(row)

    mt = Table(matrix_data, colWidths=col_widths, repeatRows=1)
    matrix_style = [
        ("BACKGROUND", (0, 0), (-1, 0), C_HEADER),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (0, -1), [colors.white, C_LIGHT_GREY]),
    ]
    for row_idx, bidder in enumerate(bidders, 1):
        bid_evals = evaluations_by_bidder.get(bidder["id"], [])
        eval_by_criterion = {e["criterion_id"]: e for e in bid_evals}
        overall_verdict = bidder.get("overall_verdict") or "needs_review"
        matrix_style.append(("BACKGROUND", (1, row_idx), (1, row_idx), VERDICT_COLORS.get(overall_verdict, C_REVIEW)))
        for col_idx, c in enumerate(matrix_criteria, 2):
            e = eval_by_criterion.get(c["id"])
            if e:
                effective = e.get("human_verdict") or e.get("verdict", "needs_review")
                matrix_style.append(("BACKGROUND", (col_idx, row_idx), (col_idx, row_idx),
                                     VERDICT_COLORS.get(effective, C_REVIEW)))

    mt.setStyle(TableStyle(matrix_style))
    story.append(mt)
    story.append(PageBreak())

    # -----------------------------------------------------------------------
    # SECTION 3 — PER-BIDDER DETAIL
    # -----------------------------------------------------------------------
    story.append(Paragraph("3. Per-Bidder Evaluation Detail", styles["SectionHeader"]))

    for bidder in bidders:
        story.append(hr())
        overall_verdict = bidder.get("overall_verdict") or "needs_review"
        overall_color = VERDICT_COLORS.get(overall_verdict, C_REVIEW)
        overall_label = VERDICT_LABELS.get(overall_verdict, overall_verdict.upper())

        bidder_header = Table([[
            Paragraph(bidder["name"], ParagraphStyle(
                "bname", fontSize=13, textColor=colors.white, fontName="Helvetica-Bold"
            )),
            Paragraph(overall_label, ParagraphStyle(
                "bverdict", fontSize=11, textColor=colors.white,
                fontName="Helvetica-Bold", alignment=TA_RIGHT
            )),
        ]], colWidths=[12 * cm, 5 * cm])
        bidder_header.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_HEADER),
            ("BACKGROUND", (1, 0), (1, 0), overall_color),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(bidder_header)
        story.append(Spacer(1, 0.2 * cm))

        if bidder.get("overall_reasoning"):
            story.append(Paragraph(f"<i>{bidder['overall_reasoning']}</i>", styles["Small"]))
        story.append(Spacer(1, 0.3 * cm))

        bid_evals = evaluations_by_bidder.get(bidder["id"], [])
        eval_by_criterion = {e["criterion_id"]: e for e in bid_evals}

        detail_header = ["#", "Criterion", "Type", "M?", "Extracted Value", "Verdict", "Confidence", "Evidence / Reasoning"]
        detail_data = [detail_header]

        for i, c in enumerate(criteria, 1):
            e = eval_by_criterion.get(c["id"])
            if not e:
                detail_data.append([str(i), Paragraph(c["description"], styles["TableCell"]),
                                     c["criterion_type"].title(), "Y" if c["is_mandatory"] else "N",
                                     "—", "—", "—", "Not evaluated"])
                continue

            effective_verdict = e.get("human_verdict") or e.get("verdict", "needs_review")
            conf = float(e.get("confidence", 0))
            conf_pct = f"{conf * 100:.0f}%"

            evidence_text = ""
            if e.get("evidence_snippet"):
                evidence_text = f'<font size="7">"{e["evidence_snippet"][:200]}"</font>'
            if e.get("reasoning"):
                evidence_text += f'<br/><font size="7" color="#6B7280">{e["reasoning"][:200]}</font>'
            if e.get("human_verdict") and e["human_verdict"] != e.get("verdict"):
                evidence_text += (
                    f'<br/><font size="7" color="#3B82F6"><b>★ Override by {e.get("reviewed_by", "reviewer")}: '
                    f'{e.get("human_note", "")[:100]}</b></font>'
                )

            detail_data.append([
                str(i),
                Paragraph(c["description"], styles["TableCell"]),
                c["criterion_type"].title(),
                "Y" if c["is_mandatory"] else "N",
                Paragraph(str(e.get("extracted_value") or "—"), styles["TableCell"]),
                Paragraph(
                    VERDICT_LABELS.get(effective_verdict, effective_verdict.upper()),
                    ParagraphStyle("vl", fontSize=7.5, textColor=colors.white,
                                   fontName="Helvetica-Bold", alignment=TA_CENTER)
                ),
                conf_pct,
                Paragraph(evidence_text or "—", styles["Evidence"]),
            ])

        dt = Table(detail_data, colWidths=[0.6 * cm, 3.5 * cm, 1.8 * cm, 0.6 * cm, 2.5 * cm, 1.8 * cm, 1.4 * cm, 5 * cm],
                   repeatRows=1)

        detail_style = [
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT_GREY]),
        ]
        for row_idx, c in enumerate(criteria, 1):
            e = eval_by_criterion.get(c["id"])
            if e:
                effective = e.get("human_verdict") or e.get("verdict", "needs_review")
                vc = VERDICT_COLORS.get(effective, C_REVIEW)
                detail_style.append(("BACKGROUND", (5, row_idx), (5, row_idx), vc))
        dt.setStyle(TableStyle(detail_style))
        story.append(dt)
        story.append(Spacer(1, 0.4 * cm))

    story.append(PageBreak())

    # -----------------------------------------------------------------------
    # SECTION 4 — AUDIT TRAIL
    # -----------------------------------------------------------------------
    story.append(Paragraph("4. Audit Trail", styles["SectionHeader"]))
    story.append(hr())
    story.append(Paragraph(
        "Every automated decision and human override is recorded below for full auditability.",
        styles["Body"]
    ))
    story.append(Spacer(1, 0.3 * cm))

    audit_data = [["Bidder", "Criterion", "AI Verdict", "Confidence", "Human Override", "Reviewer", "Timestamp"]]
    for bidder in bidders:
        bid_evals = evaluations_by_bidder.get(bidder["id"], [])
        eval_by_criterion = {e["criterion_id"]: e for e in bid_evals}
        for c in criteria:
            e = eval_by_criterion.get(c["id"])
            if not e:
                continue
            ts = e.get("reviewed_at") or e.get("evaluated_at") or "—"
            if hasattr(ts, "strftime"):
                ts = ts.strftime("%Y-%m-%d %H:%M")
            audit_data.append([
                Paragraph(bidder["name"][:25], styles["Small"]),
                Paragraph(c["description"][:40], styles["Small"]),
                VERDICT_LABELS.get(e.get("verdict", ""), "—"),
                f"{float(e.get('confidence', 0)) * 100:.0f}%",
                VERDICT_LABELS.get(e.get("human_verdict") or "", "—") if e.get("human_verdict") else "—",
                e.get("reviewed_by") or "—",
                str(ts)[:16],
            ])

    at = Table(audit_data, colWidths=[3 * cm, 4.5 * cm, 2 * cm, 1.5 * cm, 2 * cm, 2 * cm, 2.2 * cm], repeatRows=1)
    at.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT_GREY]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(at)

    # Footer note
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        f"Generated by TenderEval AI on {datetime.utcnow().strftime('%d %B %Y at %H:%M UTC')}. "
        "This report is computer-generated and must be reviewed and approved by an authorised procurement officer before use in any official decision.",
        ParagraphStyle("footer", fontSize=7, textColor=colors.HexColor("#9CA3AF"), alignment=TA_CENTER, leading=10)
    ))

    doc.build(story)
    return buf.getvalue()
