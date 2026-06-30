"""
JARVIS — PDF Generator Utility
Compiles structured text and Markdown into publication-grade PDF documents using ReportLab.
"""

import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

def create_edtech_pdf(title: str, content: str, filename: str) -> str:
    """
    Generates a professional PDF document for lesson plans, exam papers, or report cards.
    Saves the file to frontend/public/exports/ and returns the web-accessible URL path.
    """
    # Ensure export directory exists
    export_dir = os.path.join("frontend", "public", "exports")
    os.makedirs(export_dir, exist_ok=True)
    
    clean_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', filename.lower()) + ".pdf"
    file_path = os.path.join(export_dir, clean_filename)
    
    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1e293b'),
        alignment=TA_CENTER,
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'DocH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0284c7'),
        spaceBefore=12,
        spaceAfter=6
    )
    
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=8,
        spaceAfter=4
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'DocBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        leftIndent=15,
        spaceAfter=3
    )

    story = []
    
    # Header Banner
    story.append(Paragraph(title, title_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284c7'), spaceAfter=15))
    
    # Parse markdown line by line
    lines = content.split('\n')
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
            
        if line_str.startswith('# '):
            story.append(Paragraph(line_str[2:].strip(), h1_style))
        elif line_str.startswith('## '):
            story.append(Paragraph(line_str[3:].strip(), h1_style))
        elif line_str.startswith('### '):
            story.append(Paragraph(line_str[4:].strip(), h2_style))
        elif line_str.startswith('* ') or line_str.startswith('- ') or line_str.startswith('🔹'):
            clean_text = line_str.lstrip('*-🔹 ').strip()
            # Replace bold markdown **text** with ReportLab <b>text</b>
            clean_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean_text)
            story.append(Paragraph(f"• {clean_text}", bullet_style))
        else:
            clean_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line_str)
            story.append(Paragraph(clean_text, body_style))
            
    doc.build(story)
    return f"/exports/{clean_filename}"
