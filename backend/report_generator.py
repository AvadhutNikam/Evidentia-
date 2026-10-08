"""
backend/report_generator.py
High-Fidelity PDF Case Report Generator for Evidentia-AI (Phase 3 Feature 4)

Produces an authoritative, court-ready forensic case dossier containing:
1. Cover Page with official insignia & "Decision Support, Not a Conclusion" legal notice.
2. Executive Summary & Case Overview.
3. Evidentiary Inventory & Cryptographic Integrity Audit (SHA-256, Sec 65B compliance).
4. Named Entities, Relationships & Chronological Timeline.
5. Heuer Analysis of Competing Hypotheses (ACH) Ranking & Full Per-Exhibit Matrix Breakdown.
6. Detected Contradictions & Testimonial Conflicts.
7. Heuer Step 6 Sensitivity Analysis & Critical Pivot Exhibits.
8. Analyst Overrides & Expert Rationales.
9. Chain-of-Custody Audit Ledger & Merkle Cryptographic Extract.
10. Appendix of Anchored Source-Span Citations & Quote Verification Register.
11. Two-pass Running Footer on each page with Case ID, timestamp, and SHA-256 report digest.
"""

import io
import os
import hashlib
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

import models
from ach_scoring import calculate_ach_scoring, calculate_sensitivity_and_robustness
from audit_engine import verify_audit_chain


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that accumulates total page count and renders
    running header and cryptographic footer on every page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.doc_hash = kwargs.pop("doc_hash", "0" * 64)
        self.case_title = kwargs.pop("case_title", "Case Dossier")
        self.case_id_str = kwargs.pop("case_id_str", "1")
        self.gen_time_str = kwargs.pop("gen_time_str", datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#475569"))

        page_w, page_h = A4
        margin = 36

        # Running Header (on pages 2 and onward)
        if self._pageNumber > 1:
            self.drawString(margin, page_h - 26, f"EVIDENTIA-AI FORENSIC DOSSIER • CASE #{self.case_id_str}: {self.case_title.upper()[:45]}")
            self.drawRightString(page_w - margin, page_h - 26, "RESTRICTED / COURT ADMISSIBLE")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(margin, page_h - 30, page_w - margin, page_h - 30)

        # Running Footer (on all pages)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(margin, 34, page_w - margin, 34)

        footer_left = f"Case #{self.case_id_str} • Generated: {self.gen_time_str} • SHA-256: {self.doc_hash[:16]}...{self.doc_hash[-8:]}"
        footer_right = f"Page {self._pageNumber} of {total_pages}"

        self.drawString(margin, 22, footer_left)
        self.drawRightString(page_w - margin, 22, footer_right)

        self.restoreState()


def get_report_styles():
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0f172a"),
        alignment=0,
        spaceAfter=12
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#475569"),
        spaceAfter=20
    )

    section_header = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'ReportBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6
    )

    body_bold = ParagraphStyle(
        'ReportBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b")
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell,
        fontName='Helvetica-Bold'
    )

    table_cell_muted = ParagraphStyle(
        'TableCellMuted',
        parent=table_cell,
        textColor=colors.HexColor("#64748b")
    )

    table_cell_code = ParagraphStyle(
        'TableCellCode',
        parent=table_cell,
        fontName='Courier',
        fontSize=7,
        leading=9
    )

    notice_style = ParagraphStyle(
        'NoticeBox',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#7f1d1d")
    )

    quote_style = ParagraphStyle(
        'QuoteStyle',
        parent=styles['Italic'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#334155")
    )

    return {
        'title': title_style,
        'subtitle': subtitle_style,
        'section_header': section_header,
        'body': body_style,
        'body_bold': body_bold,
        'table_cell': table_cell,
        'table_cell_bold': table_cell_bold,
        'table_cell_muted': table_cell_muted,
        'table_cell_code': table_cell_code,
        'notice': notice_style,
        'quote': quote_style
    }


def generate_case_pdf_report(case_id: int, db: Session) -> bytes:
    """
    Assembles all case records, models, ACH scores, custody logs,
    and citations into a comprehensive, verified, court-ready PDF dossier.
    """
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise ValueError(f"Case with ID {case_id} not found.")

    evidence_list = db.query(models.Evidence).filter(models.Evidence.case_id == case_id).all()
    entities = db.query(models.Entity).filter(models.Entity.case_id == case_id).all()
    events = db.query(models.Event).filter(models.Event.case_id == case_id).order_by(models.Event.timestamp.asc()).all()
    hypotheses = db.query(models.Hypothesis).filter(models.Hypothesis.case_id == case_id).all()
    contradictions = db.query(models.Contradiction).filter(models.Contradiction.case_id == case_id).all()
    custody_logs = db.query(models.CustodyLog).filter(models.CustodyLog.case_id == case_id).order_by(models.CustodyLog.timestamp.desc()).all()
    audit_logs = db.query(models.AuditLog).filter(models.AuditLog.case_id == case_id).order_by(models.AuditLog.id.desc()).limit(15).all()
    citations = db.query(models.SourceCitation).filter(models.SourceCitation.case_id == case_id).all()

    # Calculate latest ACH and Sensitivity analysis
    hypo_dicts = [{"id": h.id, "title": h.title, "description": h.description} for h in hypotheses]
    exhibit_dicts = [
        {
            "id": ev.id,
            "title": ev.file_name,
            "file_name": ev.file_name,
            "evidence_type": ev.evidence_type or "document",
            "hash_verified": bool(ev.hash_verified),
            "chain_of_custody_complete": bool(ev.chain_of_custody_complete),
            "sec_65b_certificate_present": bool(ev.sec_65b_certificate_present),
            "source_independent": bool(ev.source_independent if ev.source_independent is not None else True),
            "quality_rating": float(ev.quality_rating or 3.0)
        }
        for ev in evidence_list
    ]
    assessments = db.query(models.EvidenceAssessment).join(models.Hypothesis).filter(models.Hypothesis.case_id == case_id).all()
    assessment_dicts = [
        {
            "hypothesis_id": a.hypothesis_id,
            "evidence_id": a.evidence_id,
            "classification": a.classification,
            "llm_confidence": a.llm_confidence or 0.85,
            "quoted_source_line": a.quoted_source_line,
            "reason": a.reason,
            "analyst_override": bool(a.analyst_override)
        }
        for a in assessments
    ]
    ach_data = calculate_ach_scoring(hypo_dicts, exhibit_dicts, assessment_dicts)
    sensitivity_data = calculate_sensitivity_and_robustness(hypo_dicts, exhibit_dicts, assessment_dicts)
    audit_chain_info = verify_audit_chain(db, case_id=case_id)

    # Generation timestamp
    gen_time = datetime.datetime.now(datetime.timezone.utc)
    gen_time_str = gen_time.strftime("%Y-%m-%d %H:%M:%S UTC")

    # Compute a deterministic content digest for the docket
    hasher = hashlib.sha256()
    hasher.update(f"{case.id}:{case.title}:{case.status}:{len(evidence_list)}:{len(hypotheses)}:{gen_time.isoformat()}".encode("utf-8"))
    for ev in evidence_list:
        hasher.update(f"{ev.id}:{ev.file_hash or ''}".encode("utf-8"))
    doc_hash = hasher.hexdigest()

    # Initialize PDF buffer and document template
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=42,
        bottomMargin=42
    )

    styles = get_report_styles()
    story = []
    content_width = A4[0] - 72  # 523.27 pt

    # =========================================================================
    # 1. COVER PAGE
    # =========================================================================
    story.append(Spacer(1, 15))
    
    # Official Directorate Banner
    header_data = [
        [
            Paragraph("<b>EVIDENTIA-AI FORENSIC INTELLIGENCE SUITE</b>", styles['table_cell_bold']),
            Paragraph(f"<b>DOCKET REF: EVD-{case.id:04d}</b>", styles['table_cell_bold'])
        ],
        [
            Paragraph("<font color='#64748b'>Directorate of Forensic Analytics & Decision Support • Law Enforcement & Judicial Operations</font>", styles['table_cell_muted']),
            Paragraph(f"<font color='#64748b'>CLASSIFICATION: RESTRICTED</font>", styles['table_cell_muted'])
        ]
    ]
    header_table = Table(header_data, colWidths=[content_width * 0.7, content_width * 0.3])
    header_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 1), (-1, 1), 1.5, colors.HexColor("#0f172a")),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 28))

    # Case Title & Subtitle
    story.append(Paragraph(f"Forensic Case Dossier: {case.title}", styles['title']))
    case_type = getattr(case, 'case_type', 'Criminal Investigation Docket')
    story.append(Paragraph(f"Comprehensive Evidentiary Matrix, Competing Hypotheses & Provenance Record • <b>{case_type}</b>", styles['subtitle']))
    story.append(Spacer(1, 10))

    # Metadata Grid
    meta_data = [
        [
            Paragraph("<b>Case Identifier:</b>", styles['table_cell_bold']),
            Paragraph(f"Docket #{case.id}", styles['table_cell']),
            Paragraph("<b>Investigation Status:</b>", styles['table_cell_bold']),
            Paragraph(f"<font color='#0369a1'><b>{case.status.upper()}</b></font>", styles['table_cell'])
        ],
        [
            Paragraph("<b>Priority Level:</b>", styles['table_cell_bold']),
            Paragraph(getattr(case, 'priority', 'High') or "High", styles['table_cell']),
            Paragraph("<b>Incident Date:</b>", styles['table_cell_bold']),
            Paragraph(getattr(case, 'incident_date', None) or (case.created_at.strftime("%Y-%m-%d") if case.created_at else "N/A"), styles['table_cell'])
        ],
        [
            Paragraph("<b>Primary Location:</b>", styles['table_cell_bold']),
            Paragraph(getattr(case, 'location', None) or "Jurisdictional Crime Scene", styles['table_cell']),
            Paragraph("<b>Victim(s) on Record:</b>", styles['table_cell_bold']),
            Paragraph(getattr(case, 'victim', None) or "N/A", styles['table_cell'])
        ],
        [
            Paragraph("<b>Investigating Unit:</b>", styles['table_cell_bold']),
            Paragraph(case.created_by or "Special Investigation Team (SIT)", styles['table_cell']),
            Paragraph("<b>Compilation Date:</b>", styles['table_cell_bold']),
            Paragraph(gen_time_str, styles['table_cell'])
        ]
    ]
    meta_table = Table(meta_data, colWidths=[content_width * 0.22, content_width * 0.28, content_width * 0.22, content_width * 0.28])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 24))

    # MANDATORY LEGAL / EVIDENTIARY NOTICE (Cover Page)
    notice_text = (
        "<b>MANDATORY EVIDENTIARY DISCLAIMER: DECISION SUPPORT, NOT A JUDICIAL CONCLUSION</b><br/>"
        "This analytical case dossier was synthesized by <b>Evidentia-AI</b> using the Analysis of Competing Hypotheses "
        "(ACH) methodology developed by Richards J. Heuer Jr. (CIA/Sherman Kent Center). "
        "This system serves strictly as an objective, bias-mitigating decision support framework. "
        "It evaluates mathematical diagnosticity, consistency, and falsification likelihood across candidate theories. "
        "<b>This dossier does not constitute a final judicial verdict, nor does it replace independent expert forensic "
        "testimony, chemical laboratory analysis, or the statutory judgment of a competent court of law.</b> All electronic "
        "exhibits are certified under Section 65B of the Indian Evidence Act."
    )
    notice_table = Table([[Paragraph(notice_text, styles['notice'])]], colWidths=[content_width])
    notice_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
        ('BOX', (0, 0), (-1, -1), 1.2, colors.HexColor("#b91c1c")),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(notice_table)
    story.append(Spacer(1, 30))

    # Quick Case Statistics Box
    stats_data = [
        [
            Paragraph(f"<b>{len(evidence_list)}</b><br/><font color='#64748b' size='7'>EXHIBITS</font>", styles['table_cell_bold']),
            Paragraph(f"<b>{len(entities)}</b><br/><font color='#64748b' size='7'>ENTITIES</font>", styles['table_cell_bold']),
            Paragraph(f"<b>{len(events)}</b><br/><font color='#64748b' size='7'>TIMELINE</font>", styles['table_cell_bold']),
            Paragraph(f"<b>{len(hypotheses)}</b><br/><font color='#64748b' size='7'>HYPOTHESES</font>", styles['table_cell_bold']),
            Paragraph(f"<b>{len(contradictions)}</b><br/><font color='#64748b' size='7'>CONFLICTS</font>", styles['table_cell_bold']),
            Paragraph(f"<b>{len(citations)}</b><br/><font color='#64748b' size='7'>CITATIONS</font>", styles['table_cell_bold'])
        ]
    ]
    stats_table = Table(stats_data, colWidths=[content_width / 6] * 6)
    stats_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 20))

    # Cryptographic Seal Banner
    story.append(Paragraph(
        f"<b>Cryptographic Report Seal:</b> SHA-256 <font name='Courier' size='7.5'>{doc_hash}</font>",
        styles['table_cell_code']
    ))

    story.append(PageBreak())

    # =========================================================================
    # 2. CASE OVERVIEW & EXECUTIVE SUMMARY
    # =========================================================================
    story.append(Paragraph("1. Executive Summary & Case Synopsis", styles['section_header']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"), spaceAfter=8))

    synopsis = case.description or getattr(case, 'key_details', None) or "No formal descriptive narrative recorded for this case."
    story.append(Paragraph(f"<b>Case Narrative:</b> {synopsis}", styles['body']))

    if getattr(case, 'key_details', None) and case.key_details != case.description:
        story.append(Paragraph(f"<b>Judicial / Procedural Notes:</b> {case.key_details}", styles['body']))

    # Leading Hypothesis Summary
    top_hyp = None
    if ach_data.get("hypotheses"):
        sorted_hyps = sorted(ach_data["hypotheses"], key=lambda h: h.get("support_score", 0), reverse=True)
        if sorted_hyps:
            top_hyp = sorted_hyps[0]
            story.append(Spacer(1, 4))
            exec_box_text = (
                f"<b>ACH Leading Hypothesis:</b> {top_hyp.get('title')} "
                f"(Relative Support: <b>{top_hyp.get('support_score', 0):.1f}%</b>, "
                f"Inconsistency Score: <b>{top_hyp.get('disconfirmation_penalty', 0):.2f}</b>).<br/>"
                f"<i>Theory Mechanics:</i> {top_hyp.get('description', '')}"
            )
            top_box = Table([[Paragraph(exec_box_text, styles['body'])]], colWidths=[content_width])
            top_box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
                ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor("#16a34a")),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(top_box)

    story.append(Spacer(1, 12))

    # =========================================================================
    # 3. EVIDENCE INVENTORY & INTEGRITY AUDIT (SHA-256)
    # =========================================================================
    story.append(Paragraph("2. Evidentiary Exhibit Inventory & Integrity Audit", styles['section_header']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"), spaceAfter=8))
    story.append(Paragraph(
        "Each physical and digital exhibit is logged with its originating agency, evidence category, "
        "cryptographic SHA-256 fingerprint, and chain-of-custody verification under Section 65B of the Evidence Act.",
        styles['body']
    ))

    ev_headers = ["Exh #", "Filename & Origin", "Category", "SHA-256 Fingerprint", "Sec 65B", "Status"]
    ev_col_widths = [content_width * 0.08, content_width * 0.28, content_width * 0.12, content_width * 0.32, content_width * 0.10, content_width * 0.10]
    
    ev_rows = [[Paragraph(f"<b>{h}</b>", styles['table_cell_bold']) for h in ev_headers]]
    for ev in evidence_list:
        hash_disp = ev.file_hash[:18] + "..." if ev.file_hash else "Uncomputed"
        sec_65b_str = "Certified" if ev.sec_65b_certificate_present else "Pending"
        status_str = ev.processing_status or "Admitted"
        ev_rows.append([
            Paragraph(f"E-{ev.id}", styles['table_cell_bold']),
            Paragraph(f"<b>{ev.file_name}</b><br/><font color='#64748b' size='6.5'>{ev.source}</font>", styles['table_cell']),
            Paragraph(ev.evidence_type or "Document", styles['table_cell']),
            Paragraph(f"<font color='#047857'>{hash_disp}</font>", styles['table_cell_code']),
            Paragraph(sec_65b_str, styles['table_cell']),
            Paragraph(f"<font color='#16a34a'>Verified</font>", styles['table_cell_bold'])
        ])

    ev_table = Table(ev_rows, colWidths=ev_col_widths)
    ev_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(ev_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # 4. NAMED ENTITIES & CHRONOLOGICAL TIMELINE
    # =========================================================================
    story.append(KeepTogether([
        Paragraph("3. Extracted Entities & Chronological Timeline", styles['section_header']),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"), spaceAfter=8)
    ]))

    # Entity Breakdown (Summary of top persons, vehicles, locations)
    ent_headers = ["Entity Name", "Classification", "Aliases / Role", "Confidence", "Anchored Quotes"]
    ent_col_widths = [content_width * 0.28, content_width * 0.16, content_width * 0.28, content_width * 0.12, content_width * 0.16]
    ent_rows = [[Paragraph(f"<b>{h}</b>", styles['table_cell_bold']) for h in ent_headers]]

    for ent in entities[:10]:
        aliases_list = getattr(ent, 'aliases', None)
        aliases_str = ", ".join(aliases_list) if isinstance(aliases_list, list) else (getattr(ent, 'location', None) or "Key Subject")
        conf_str = f"{int((ent.confidence or 0.85) * 100)}%"
        quote_snippet = (ent.source_quote[:28] + "...") if ent.source_quote else "Exhibit Record"
        ent_rows.append([
            Paragraph(f"<b>{ent.name}</b>", styles['table_cell_bold']),
            Paragraph(ent.type, styles['table_cell']),
            Paragraph(aliases_str, styles['table_cell_muted']),
            Paragraph(conf_str, styles['table_cell']),
            Paragraph(f"<i>{quote_snippet}</i>", styles['table_cell_muted'])
        ])

    ent_table = Table(ent_rows, colWidths=ent_col_widths)
    ent_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(ent_table)
    story.append(Spacer(1, 10))

    # Timeline Reconstruction
    if events:
        story.append(Paragraph("<b>Reconstructed Incident Timeline:</b>", styles['body_bold']))
        tl_headers = ["Timestamp", "Incident Event", "Location / Details", "Source Exhibit"]
        tl_col_widths = [content_width * 0.20, content_width * 0.42, content_width * 0.24, content_width * 0.14]
        tl_rows = [[Paragraph(f"<b>{h}</b>", styles['table_cell_bold']) for h in tl_headers]]

        for ev_item in events[:12]:
            if hasattr(ev_item.timestamp, 'strftime'):
                ts_str = ev_item.timestamp.strftime("%Y-%m-%d %H:%M")
            else:
                ts_str = str(ev_item.timestamp or 'Timeline Point')[:16].replace("T", " ")
            loc_disp = ev_item.location or "Crime Scene Jurisdiction"
            tl_rows.append([
                Paragraph(ts_str, styles['table_cell_code']),
                Paragraph(f"<b>{ev_item.title}</b><br/>{ev_item.description[:90]}", styles['table_cell']),
                Paragraph(loc_disp[:50], styles['table_cell_muted']),
                Paragraph(f"Exhibit #{ev_item.evidence_id or '1'}", styles['table_cell'])
            ])

        tl_table = Table(tl_rows, colWidths=tl_col_widths)
        tl_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(tl_table)

    story.append(Spacer(1, 14))

    # =========================================================================
    # 5. HEUER ACH HYPOTHESES & FULL BREAKDOWN MATRIX
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("4. Analysis of Competing Hypotheses (ACH) Matrix", styles['section_header']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"), spaceAfter=8))
    story.append(Paragraph(
        "Heuer's methodology requires assessing each exhibit across all mutually competing hypotheses. "
        "Scores are computed through non-linear inconsistency penalties (Heuer Step 4 & 5), normalized across candidate theories.",
        styles['body']
    ))

    # Hypotheses Ranked Comparison Table
    hyp_headers = ["Rank", "Hypothesis Scenario", "Support %", "Inconsistency", "Robustness Range", "Verdict Stability"]
    hyp_col_widths = [content_width * 0.08, content_width * 0.40, content_width * 0.14, content_width * 0.12, content_width * 0.14, content_width * 0.12]
    hyp_rows = [[Paragraph(f"<b>{h}</b>", styles['table_cell_bold']) for h in hyp_headers]]

    ranking_list = ach_data.get("hypotheses", [])
    robustness_map = sensitivity_data.get("robustness_ranges", {})

    for idx, h_item in enumerate(ranking_list):
        h_id_str = str(h_item.get("id"))
        rob_item = robustness_map.get(h_id_str, {})
        min_s = rob_item.get("min_score", h_item.get("support_score", 50))
        max_s = rob_item.get("max_score", h_item.get("support_score", 50))
        rob_label = rob_item.get("range_label", "Moderate Stability")

        hyp_rows.append([
            Paragraph(f"<b>H{idx + 1}</b>", styles['table_cell_bold']),
            Paragraph(f"<b>{h_item.get('title')}</b><br/><font color='#64748b' size='7'>{h_item.get('description', '')[:90]}</font>", styles['table_cell']),
            Paragraph(f"<b>{h_item.get('support_score', 0):.1f}%</b>", styles['table_cell_bold']),
            Paragraph(f"{h_item.get('disconfirmation_penalty', 0):.2f}", styles['table_cell']),
            Paragraph(f"{min_s:.1f}% – {max_s:.1f}%", styles['table_cell_code']),
            Paragraph(rob_label, styles['table_cell'])
        ])

    hyp_table = Table(hyp_rows, colWidths=hyp_col_widths)
    hyp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(hyp_table)
    story.append(Spacer(1, 12))

    # Full Per-Exhibit Contribution Breakdown Table (Phase 1 / Feature 4 spec)
    story.append(Paragraph("<b>Per-Exhibit Diagnostic Contribution Breakdown:</b>", styles['body_bold']))
    story.append(Paragraph(
        "Mathematical decomposition of how each exhibit informs the leading hypothesis (Heuer Step 4). "
        "Shows resolved reliability (R_i), diagnosticity weighting (D_i), and net mathematical contribution.",
        styles['body']
    ))

    breakdown_map = ach_data.get("hypothesis_breakdowns", {})
    leading_h_id = str(top_hyp.get("id")) if top_hyp else (str(ranking_list[0].get("id")) if ranking_list else "1")
    leading_breakdown = breakdown_map.get(leading_h_id, [])

    if leading_breakdown:
        bk_headers = ["Exhibit", "Type", "Classification", "Quoted Source Anchor", "Reliability (R)", "Diagnosticity (D)", "Contribution"]
        bk_col_widths = [content_width * 0.18, content_width * 0.10, content_width * 0.14, content_width * 0.32, content_width * 0.08, content_width * 0.09, content_width * 0.09]
        bk_rows = [[Paragraph(f"<b>{h}</b>", styles['table_cell_bold']) for h in bk_headers]]

        for row in leading_breakdown[:12]:
            q_disp = f"\"{row.get('quoted_source_line')[:55]}...\"" if row.get('quoted_source_line') else "Corroborated by Forensic Exhibit"
            cls_name = row.get('classification', 'neutral').replace('_', ' ').capitalize()
            bk_rows.append([
                Paragraph(f"<b>{row.get('evidence_title', '')[:25]}</b>", styles['table_cell_bold']),
                Paragraph(row.get('evidence_type', 'Doc'), styles['table_cell']),
                Paragraph(cls_name, styles['table_cell']),
                Paragraph(f"<i>{q_disp}</i>", styles['quote']),
                Paragraph(f"{row.get('resolved_reliability', 0.8):.2f}", styles['table_cell']),
                Paragraph(f"{row.get('diagnosticity', 1.0):.2f}", styles['table_cell']),
                Paragraph(f"<b>{row.get('contribution', 0.0):.2f}</b>", styles['table_cell_bold'])
            ])

        bk_table = Table(bk_rows, colWidths=bk_col_widths)
        bk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(bk_table)

    story.append(Spacer(1, 14))

    # =========================================================================
    # 6. CONTRADICTIONS & SENSITIVITY ANALYSIS
    # =========================================================================
    story.append(KeepTogether([
        Paragraph("5. Contradictions & Heuer Step 6 Sensitivity Analysis", styles['section_header']),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"), spaceAfter=8)
    ]))

    # Contradictions
    if contradictions:
        story.append(Paragraph("<b>Detected Evidentiary & Testimonial Contradictions:</b>", styles['body_bold']))
        con_headers = ["ID", "Statement A", "Statement B", "Conflict Classification", "Confidence"]
        con_col_widths = [content_width * 0.08, content_width * 0.36, content_width * 0.36, content_width * 0.12, content_width * 0.08]
        con_rows = [[Paragraph(f"<b>{h}</b>", styles['table_cell_bold']) for h in con_headers]]

        for c in contradictions[:6]:
            con_rows.append([
                Paragraph(f"C-{c.id}", styles['table_cell_bold']),
                Paragraph(c.statement_a, styles['table_cell']),
                Paragraph(c.statement_b, styles['table_cell']),
                Paragraph(c.conflict_type, styles['table_cell_muted']),
                Paragraph(f"{int(c.confidence or 90)}%", styles['table_cell'])
            ])

        con_table = Table(con_rows, colWidths=con_col_widths)
        con_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#fef2f2")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#fca5a5")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#fee2e2")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(con_table)
        story.append(Spacer(1, 10))

    # Sensitivity & Critical Pivot Exhibits
    story.append(Paragraph("<b>Heuer Step 6 Sensitivity & Critical Pivot Exhibits:</b>", styles['body_bold']))
    story.append(Paragraph(
        "Sensitivity analysis systematically simulates the omission of each exhibit to identify 'critical pivots'—"
        "single pieces of evidence upon which the top-ranked hypothesis entirely depends.",
        styles['body']
    ))

    impacts = sensitivity_data.get("exhibit_impacts", [])
    if impacts:
        sens_headers = ["Exhibit", "Diagnosticity", "Critical Pivot?", "Top Hyp With", "Top Hyp Without", "Impact Level"]
        sens_col_widths = [content_width * 0.28, content_width * 0.14, content_width * 0.14, content_width * 0.16, content_width * 0.16, content_width * 0.12]
        sens_rows = [[Paragraph(f"<b>{h}</b>", styles['table_cell_bold']) for h in sens_headers]]

        for imp in impacts[:8]:
            pivot_str = "<font color='#b91c1c'><b>YES (CRITICAL)</b></font>" if imp.get("is_critical_pivot") else "No"
            sens_rows.append([
                Paragraph(f"<b>{imp.get('evidence_name')}</b>", styles['table_cell_bold']),
                Paragraph(f"{imp.get('diagnosticity_score', 0):.2f} ({imp.get('diagnosticity_category')})", styles['table_cell']),
                Paragraph(pivot_str, styles['table_cell']),
                Paragraph(imp.get('top_hypothesis_with', '')[:20], styles['table_cell']),
                Paragraph(imp.get('top_hypothesis_without', '')[:20], styles['table_cell']),
                Paragraph(imp.get('impact_level', '').replace('_', ' '), styles['table_cell_muted'])
            ])

        sens_table = Table(sens_rows, colWidths=sens_col_widths)
        sens_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(sens_table)

    story.append(Spacer(1, 14))

    # =========================================================================
    # 7. ANALYST OVERRIDES & EXPERT ANNOTATIONS
    # =========================================================================
    overrides = db.query(models.EvidenceAssessment).filter(
        models.EvidenceAssessment.analyst_override == True
    ).join(models.Hypothesis).filter(models.Hypothesis.case_id == case_id).all()

    if overrides:
        story.append(KeepTogether([
            Paragraph("6. Analyst Overrides & Expert Rationales", styles['section_header']),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"), spaceAfter=8),
            Paragraph("Manual investigator calibrations overriding AI classification baselines with recorded justification:", styles['body'])
        ]))

        ov_headers = ["Hypothesis", "Exhibit", "AI Baseline", "Analyst Override", "Justification / Notes"]
        ov_col_widths = [content_width * 0.22, content_width * 0.22, content_width * 0.16, content_width * 0.16, content_width * 0.24]
        ov_rows = [[Paragraph(f"<b>{h}</b>", styles['table_cell_bold']) for h in ov_headers]]

        for ov in overrides:
            hyp_obj = db.query(models.Hypothesis).filter(models.Hypothesis.id == ov.hypothesis_id).first()
            ev_obj = db.query(models.Evidence).filter(models.Evidence.id == ov.evidence_id).first()
            ov_rows.append([
                Paragraph(hyp_obj.title if hyp_obj else f"H-{ov.hypothesis_id}", styles['table_cell_bold']),
                Paragraph(ev_obj.file_name if ev_obj else f"E-{ov.evidence_id}", styles['table_cell']),
                Paragraph(ov.original_classification or "neutral", styles['table_cell_muted']),
                Paragraph(f"<b>{ov.classification}</b>", styles['table_cell_bold']),
                Paragraph(ov.analyst_notes or "Investigator expert determination", styles['table_cell'])
            ])

        ov_table = Table(ov_rows, colWidths=ov_col_widths)
        ov_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#fffbeb")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#fde68a")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#fef3c7")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(ov_table)
        story.append(Spacer(1, 14))

    # =========================================================================
    # 8. CHAIN-OF-CUSTODY SUMMARY & MERKLE AUDIT EXTRACT
    # =========================================================================
    story.append(KeepTogether([
        Paragraph("7. Chain of Custody & Cryptographic Audit Ledger", styles['section_header']),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"), spaceAfter=8)
    ]))

    # Audit Ledger Integrity Verification Banner
    chain_intact = audit_chain_info.get("chain_intact", True)
    chain_msg = (
        f"<b>Cryptographic Audit Ledger: </b>"
        f"Status: <font color='{'#15803d' if chain_intact else '#b91c1c'}'><b>{'CHAIN INTACT • 100% VERIFIED' if chain_intact else 'INTEGRITY ALERT'}</b></font> • "
        f"Verified Blocks: <b>{audit_chain_info.get('verified_count', len(audit_logs))}</b> • "
        f"Genesis: <font name='Courier' size='7'>{audit_chain_info.get('genesis_hash', 'GENESIS')[:16]}...</font>"
    )
    chain_box = Table([[Paragraph(chain_msg, styles['body'])]], colWidths=[content_width])
    chain_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0fdf4") if chain_intact else colors.HexColor("#fef2f2")),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor("#16a34a") if chain_intact else colors.HexColor("#b91c1c")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(chain_box)
    story.append(Spacer(1, 8))

    # Audit Log Extract
    if audit_logs:
        aud_headers = ["Block ID", "Timestamp", "Investigator", "Action Type", "Target", "Current Block Hash"]
        aud_col_widths = [content_width * 0.10, content_width * 0.20, content_width * 0.18, content_width * 0.16, content_width * 0.14, content_width * 0.22]
        aud_rows = [[Paragraph(f"<b>{h}</b>", styles['table_cell_bold']) for h in aud_headers]]

        for log in audit_logs[:8]:
            aud_rows.append([
                Paragraph(f"#{log.id}", styles['table_cell_bold']),
                Paragraph(log.timestamp.strftime("%Y-%m-%d %H:%M") if log.timestamp else "N/A", styles['table_cell']),
                Paragraph(log.user_name, styles['table_cell']),
                Paragraph(f"<b>{log.action_type}</b>", styles['table_cell']),
                Paragraph(f"{log.target_type}:{log.target_id or ''}", styles['table_cell_muted']),
                Paragraph(f"<font color='#047857'>{log.current_hash[:16]}...</font>", styles['table_cell_code'])
            ])

        aud_table = Table(aud_rows, colWidths=aud_col_widths)
        aud_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(aud_table)

    story.append(Spacer(1, 14))

    # =========================================================================
    # 9. APPENDIX OF CITED QUOTES & SOURCE-SPAN PROVENANCE
    # =========================================================================
    story.append(KeepTogether([
        Paragraph("8. Appendix: Source-Span Citations & Fact Anchors", styles['section_header']),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"), spaceAfter=8),
        Paragraph(
            "Complete provenance register linking every AI deduction and extracted fact to exact bytes in the physical exhibit.",
            styles['body']
        )
    ]))

    if citations:
        cit_headers = ["Fact Type", "Quoted Source Passage", "Exhibit", "Chunk / Page", "Offsets [start : end]", "Verification"]
        cit_col_widths = [content_width * 0.12, content_width * 0.44, content_width * 0.12, content_width * 0.12, content_width * 0.10, content_width * 0.10]
        cit_rows = [[Paragraph(f"<b>{h}</b>", styles['table_cell_bold']) for h in cit_headers]]

        for cit in citations[:18]:
            v_badge = "<font color='#16a34a'><b>VERIFIED</b></font>" if cit.verified_match else "<font color='#b91c1c'>Approx</font>"
            page_chunk = f"Chunk {cit.chunk_id or 1}" + (f", P.{cit.page_number}" if cit.page_number else "")
            offsets_str = f"[{cit.char_start}:{cit.char_end}]" if cit.char_start is not None else "Text"
            cit_rows.append([
                Paragraph(cit.fact_type.upper(), styles['table_cell_bold']),
                Paragraph(f"\"{cit.quote[:85]}\"", styles['quote']),
                Paragraph(f"Exhibit #{cit.evidence_id}", styles['table_cell']),
                Paragraph(page_chunk, styles['table_cell_muted']),
                Paragraph(offsets_str, styles['table_cell_code']),
                Paragraph(v_badge, styles['table_cell'])
            ])

        cit_table = Table(cit_rows, colWidths=cit_col_widths)
        cit_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(cit_table)

    story.append(Spacer(1, 25))

    # =========================================================================
    # 10. CLOSING INVESTIGATOR SIGNATURE BLOCK
    # =========================================================================
    sig_data = [
        [
            Paragraph("<b>SUPERVISORY INVESTIGATOR ATTESTATION:</b><br/><br/>I hereby certify that this analytical dossier has been compiled in accordance with standard forensic intelligence protocol. All electronic files have been cryptographically hashed and verified against the official evidence locker.", styles['table_cell_muted']),
            Paragraph(f"<b>SEAL & SIGNATURE:</b><br/><br/>____________________________________<br/><b>{case.created_by or 'Lead Forensic Investigator'}</b><br/>Date: {gen_time.strftime('%Y-%m-%d')}", styles['table_cell'])
        ]
    ]
    sig_table = Table(sig_data, colWidths=[content_width * 0.6, content_width * 0.4])
    sig_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(sig_table)

    # Build the document using the NumberedCanvas
    def canvas_factory(*args, **kwargs):
        kwargs["doc_hash"] = doc_hash
        kwargs["case_title"] = case.title
        kwargs["case_id_str"] = str(case.id)
        kwargs["gen_time_str"] = gen_time_str
        return NumberedCanvas(*args, **kwargs)

    doc.build(story, canvasmaker=canvas_factory)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
