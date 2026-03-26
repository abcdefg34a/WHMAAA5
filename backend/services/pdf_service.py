"""
PDF Generation Service
Handles all PDF generation logic for job invoices
"""

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import cm
from datetime import datetime, timezone
import base64
from PIL import Image as PILImage


async def generate_job_pdf(job: dict, db):
    """
    Generate PDF invoice for a job
    
    Args:
        job: Job document from database
        db: Database instance
        
    Returns:
        StreamingResponse with PDF content
    """
    
    # NEW: Track PDF generation timestamp (for freeze logic)
    # PDF is frozen after 10 days - we won't reset pdf_generated_at unless user explicitly requests it
    pdf_generated_at = job.get("pdf_generated_at")
    
    # Get service info
    service = None
    if job.get("assigned_service_id"):
        service = await db.users.find_one({"id": job["assigned_service_id"]}, {"_id": 0, "password": 0})
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=8,
        alignment=1,  # Center
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#334155'),
        spaceBefore=14,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#1e293b'),
        leading=14
    )
    
    def wrap_text(text, max_chars=50):
        """Helper to wrap long text"""
        if not text or len(text) <= max_chars:
            return text
        words = text.split()
        lines = []
        current = []
        current_len = 0
        for word in words:
            if current_len + len(word) + 1 <= max_chars:
                current.append(word)
                current_len += len(word) + 1
            else:
                if current:
                    lines.append(' '.join(current))
                current = [word]
                current_len = len(word)
        if current:
            lines.append(' '.join(current))
        return '<br/>'.join(lines)
    
    # Header Section - Compact
    story.append(Paragraph("Rechnung", title_style))
    story.append(Spacer(1, 8))
    
    # Job Number and Date - Compact
    job_header_data = [
        [Paragraph(f"<b>Auftragsnummer:</b> {job['job_number']}", cell_style)],
        [Paragraph(f"<b>Erstellt am:</b> {datetime.fromisoformat(job['created_at'].replace('Z', '+00:00')).strftime('%d.%m.%Y %H:%M')} Uhr", cell_style)],
    ]
    job_header_table = Table(job_header_data, colWidths=[17*cm])
    job_header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
    ]))
    story.append(job_header_table)
    
    # ===== FAHRZEUGDATEN =====
    story.append(Paragraph("Fahrzeugdaten", heading_style))
    vehicle_data = [
        [Paragraph("<b>Kennzeichen</b>", cell_style), Paragraph(job.get('license_plate') or '-', cell_style)],
        [Paragraph("<b>FIN</b>", cell_style), Paragraph(job.get('vin') or '-', cell_style)],
        [Paragraph("<b>Marke/Modell</b>", cell_style), Paragraph(job.get('vehicle_make_model') or '-', cell_style)],
        [Paragraph("<b>Farbe</b>", cell_style), Paragraph(job.get('vehicle_color') or '-', cell_style)],
    ]
    vehicle_table = Table(vehicle_data, colWidths=[4.5*cm, 12.5*cm])
    vehicle_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(vehicle_table)
    
    # ===== AUFTRAGSDATEN =====
    story.append(Paragraph("Auftragsdaten", heading_style))
    tow_reason_text = {
        'parked_illegally': 'Falschparker',
        'blocking_traffic': 'Verkehrsbehinderung',
        'abandoned': 'Verlassen',
        'accident': 'Unfall',
        'other': 'Sonstiges'
    }.get(job.get('tow_reason'), job.get('tow_reason') or '-')
    
    order_data = [
        [Paragraph("<b>Abschleppgrund</b>", cell_style), Paragraph(tow_reason_text, cell_style)],
        [Paragraph("<b>Standort</b>", cell_style), Paragraph(wrap_text(job.get('location_address') or '-', 55), cell_style)],
    ]
    if job.get('notes'):
        order_data.append([Paragraph("<b>Bemerkungen</b>", cell_style), Paragraph(wrap_text(job.get('notes') or '-', 55), cell_style)])
    
    order_table = Table(order_data, colWidths=[4.5*cm, 12.5*cm])
    order_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(order_table)
    
    # ===== ZEITVERLAUF =====
    story.append(Paragraph("Zeitverlauf", heading_style))
    timeline_data = [
        [Paragraph("<b>Ereignis</b>", cell_style), Paragraph("<b>Zeitpunkt</b>", cell_style)],
        [Paragraph("Auftrag erstellt", cell_style), Paragraph(datetime.fromisoformat(job['created_at'].replace('Z', '+00:00')).strftime('%d.%m.%Y %H:%M'), cell_style)],
    ]
    if job.get('accepted_at'):
        timeline_data.append([Paragraph("Abschleppdienst zugewiesen", cell_style), Paragraph(datetime.fromisoformat(job['accepted_at'].replace('Z', '+00:00')).strftime('%d.%m.%Y %H:%M'), cell_style)])
    if job.get('picked_up_at'):
        timeline_data.append([Paragraph("Fahrzeug abgeschleppt", cell_style), Paragraph(datetime.fromisoformat(job['picked_up_at'].replace('Z', '+00:00')).strftime('%d.%m.%Y %H:%M'), cell_style)])
    if job.get('in_yard_at'):
        timeline_data.append([Paragraph("Im Hof angekommen", cell_style), Paragraph(datetime.fromisoformat(job['in_yard_at'].replace('Z', '+00:00')).strftime('%d.%m.%Y %H:%M'), cell_style)])
    if job.get('delivered_to_authority_at'):
        timeline_data.append([Paragraph("An Behörde übergeben", cell_style), Paragraph(datetime.fromisoformat(job['delivered_to_authority_at'].replace('Z', '+00:00')).strftime('%d.%m.%Y %H:%M'), cell_style)])
    if job.get('released_at'):
        timeline_data.append([Paragraph("Fahrzeug freigegeben", cell_style), Paragraph(datetime.fromisoformat(job['released_at'].replace('Z', '+00:00')).strftime('%d.%m.%Y %H:%M'), cell_style)])
    
    timeline_table = Table(timeline_data, colWidths=[8.5*cm, 8.5*cm])
    timeline_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    story.append(timeline_table)
    
    # ===== HALTERDATEN (if released) =====
    if job.get('owner_first_name'):
        story.append(Paragraph("Halterdaten", heading_style))
        owner_name = f"{job.get('owner_first_name') or ''} {job.get('owner_last_name') or ''}".strip() or '-'
        owner_data = [
            [Paragraph("<b>Name</b>", cell_style), Paragraph(owner_name, cell_style)],
            [Paragraph("<b>Adresse</b>", cell_style), Paragraph(wrap_text(job.get('owner_address') or '-', 55), cell_style)],
        ]
        owner_table = Table(owner_data, colWidths=[4.5*cm, 12.5*cm])
        owner_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(owner_table)
    
    # ===== GET PRICES_INCLUDE_VAT SETTING (for both Kostenaufstellung and Zahlungsinformationen) =====
    # This needs to be determined ONCE and used consistently
    prices_include_vat = True  # Default
    issuer_settings = None
    
    # Determine who owns the job and use their price setting
    if job.get('target_yard') == 'authority_yard' or (job.get('authority_id') and not job.get('assigned_service_id')):
        # Authority job
        if job.get('authority_id'):
            issuer_settings = await db.users.find_one(
                {"id": job.get('authority_id')},
                {"_id": 0, "prices_include_vat": 1}
            )
    elif job.get('assigned_service_id'):
        # Service yard job
        issuer_settings = await db.users.find_one(
            {"id": job.get('assigned_service_id')},
            {"_id": 0, "prices_include_vat": 1}
        )
    
    # Set prices_include_vat based on issuer settings
    if issuer_settings and 'prices_include_vat' in issuer_settings:
        prices_include_vat = issuer_settings['prices_include_vat']
    else:
        prices_include_vat = True  # Default for old jobs
    
    # ===== VEREINFACHTE KOSTENAUFSTELLUNG =====
    if job.get('released_at') and job.get('payment_amount') and job.get('payment_amount') > 0:
        story.append(Paragraph("Kostenaufstellung", heading_style))
        
        # Get payment amount from job (this is the BASE amount, interpretation depends on prices_include_vat)
        base_amount = job.get('payment_amount', 0)
        
        # Build simplified cost table
        cost_table_data = []
        
        if prices_include_vat:
            # Preise inkl. MwSt → base_amount IST bereits BRUTTO
            # Zeige nur Gesamtbetrag
            cost_table_data.append([
                Paragraph("<b>Gesamtbetrag (Brutto inkl. 19% MwSt.)</b>", ParagraphStyle('Bold', parent=cell_style, fontSize=11)),
                Paragraph(f"<b>{base_amount:.2f} €</b>", ParagraphStyle('BoldRight', parent=cell_style, fontSize=11, alignment=2))
            ])
        else:
            # Preise sind NETTO → base_amount IST NETTO, MwSt DRAUFRECHNEN
            vat_rate = 0.19
            net_total = base_amount  # Das ist der Netto-Betrag
            vat_amount = net_total * vat_rate  # 19% MwSt auf Netto
            brutto_total = net_total + vat_amount  # Brutto = Netto + MwSt
            
            cost_table_data.append([
                Paragraph("Netto-Summe", cell_style),
                Paragraph(f"{net_total:.2f} €", ParagraphStyle('RightAlign', parent=cell_style, alignment=2))
            ])
            cost_table_data.append([
                Paragraph(f"zzgl. {int(vat_rate * 100)}% MwSt.", cell_style),
                Paragraph(f"{vat_amount:.2f} €", ParagraphStyle('RightAlign', parent=cell_style, alignment=2))
            ])
            
            # Spacer
            spacer_style = ParagraphStyle('Spacer', parent=cell_style, fontSize=4, leading=6)
            cost_table_data.append([Paragraph(" ", spacer_style), Paragraph(" ", spacer_style)])
            
            cost_table_data.append([
                Paragraph("<b>Gesamtbetrag (Brutto)</b>", ParagraphStyle('Bold', parent=cell_style, fontSize=11)),
                Paragraph(f"<b>{brutto_total:.2f} €</b>", ParagraphStyle('BoldRight', parent=cell_style, fontSize=11, alignment=2))
            ])
        
        cost_table = Table(cost_table_data, colWidths=[12*cm, 5*cm])
        cost_table.setStyle(TableStyle([
            # No backgrounds, no borders - clean look
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(cost_table)
        story.append(Spacer(1, 10))
        
        # Payment terms
        terms_style = ParagraphStyle(
            'Terms',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=10
        )
        story.append(Paragraph("<b>Zahlungsbedingungen:</b> Zahlbar sofort ohne Abzug", terms_style))
    
    # ===== ZAHLUNGSINFORMATIONEN =====
    has_payment = job.get('payment_method') and not (job.get('is_empty_trip') and job.get('payment_amount', 0) == 0)
    if has_payment:
        story.append(Paragraph("Zahlungsinformationen", heading_style))
        payment_method_text = "Bar" if job['payment_method'] == 'cash' else "Kartenzahlung"
        
        # Calculate correct payment amount based on prices_include_vat setting
        payment_display_amount = job.get('payment_amount', 0)
        if not prices_include_vat and payment_display_amount > 0:
            # If prices are NETTO, calculate BRUTTO for display
            vat_rate = 0.19
            payment_display_amount = payment_display_amount * (1 + vat_rate)
        
        payment_data = [
            [Paragraph("<b>Zahlungsart</b>", cell_style), Paragraph(payment_method_text, cell_style)],
            [Paragraph("<b>Betrag</b>", cell_style), Paragraph(f"{payment_display_amount:.2f} €", cell_style)],
        ]
        payment_table = Table(payment_data, colWidths=[4.5*cm, 12.5*cm])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
            ('BACKGROUND', (1, 1), (1, 1), colors.HexColor('#dcfce7')),  # Green background for amount
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(payment_table)
    
    # ===== ABSCHLEPPHOF (depends on target_yard) =====
    is_authority_yard = job.get("target_yard") == "authority_yard"
    
    if is_authority_yard:
        # Authority yard - show authority info
        story.append(Paragraph("Verwahrort (Behörden-Hof)", heading_style))
        yard_data = [
            [Paragraph("<b>Hof</b>", cell_style), Paragraph(job.get('authority_yard_name') or 'Behörden-Hof', cell_style)],
            [Paragraph("<b>Adresse</b>", cell_style), Paragraph(wrap_text(job.get('authority_yard_address') or '-', 55), cell_style)],
            [Paragraph("<b>Telefon</b>", cell_style), Paragraph(job.get('authority_yard_phone') or '-', cell_style)],
        ]
        # Add authority name
        if job.get('created_by_authority'):
            yard_data.insert(0, [
                Paragraph("<b>Behörde</b>", cell_style), 
                Paragraph(job.get('created_by_authority') or '-', cell_style)
            ])
        yard_table = Table(yard_data, colWidths=[4.5*cm, 12.5*cm])
        yard_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(yard_table)
    else:
        # Service yard - show towing service info
        if service:
            story.append(Paragraph("Verwahrort (Abschleppdienst-Hof)", heading_style))
            service_yard_data = [
                [Paragraph("<b>Abschleppdienst</b>", cell_style), Paragraph(service.get('company_name') or service.get('name') or '-', cell_style)],
                [Paragraph("<b>Hof-Adresse</b>", cell_style), Paragraph(wrap_text(service.get('yard_address') or '-', 55), cell_style)],
            ]
            if service.get('phone'):
                service_yard_data.append([Paragraph("<b>Telefon</b>", cell_style), Paragraph(service.get('phone') or '-', cell_style)])
            
            service_yard_table = Table(service_yard_data, colWidths=[4.5*cm, 12.5*cm])
            service_yard_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ]))
            story.append(service_yard_table)
    
    # ===== PHOTOS (if any) =====
    if job.get('photos') and len(job['photos']) > 0:
        story.append(Paragraph("Fotos", heading_style))
        
        photo_elements = []
        for i, photo_url in enumerate(job['photos'][:6], 1):  # Max 6 photos
            try:
                if photo_url.startswith('data:image'):
                    img_data = base64.b64decode(photo_url.split(',')[1])
                    img_buffer = BytesIO(img_data)
                    pil_img = PILImage.open(img_buffer)
                    pil_img.thumbnail((200, 200))
                    thumb_buffer = BytesIO()
                    pil_img.save(thumb_buffer, format='PNG')
                    thumb_buffer.seek(0)
                    img = Image(thumb_buffer, width=4*cm, height=3*cm)
                    photo_elements.append([img, Paragraph(f"Foto {i}", cell_style)])
            except:
                continue
        
        if photo_elements:
            photo_table = Table(photo_elements, colWidths=[5*cm, 12*cm])
            photo_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(photo_table)
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#64748b'),
        alignment=1  # Center
    )
    story.append(Spacer(1, 15))
    story.append(Paragraph(f"Erstellt am: {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')} UTC", footer_style))
    
    doc.build(story)
    buffer.seek(0)
    
    # NEW: Save PDF generation timestamp (for freeze logic)
    if not pdf_generated_at:
        # Only set timestamp on first generation
        await db.jobs.update_one(
            {"id": job["id"]},
            {"$set": {"pdf_generated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Rechnung_{job['job_number']}.pdf"}
    )
