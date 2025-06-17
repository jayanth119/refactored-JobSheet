import sys
import os
import io
import pandas as pd
import streamlit as st
from datetime import datetime, date
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
def generate_enhanced_job_sheet_pdf(job_id, job_data, schema_df):
    """Generate PDF job sheet based on current schema configuration"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(100, height - 50, "REPAIR PRO - JOB SHEET")
    c.setFont("Helvetica", 14)
    c.drawString(450, height - 50, f"Job #: {job_id}")
    c.drawString(450, height - 70, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    
    # Draw a line
    c.line(100, height - 80, width - 100, height - 80)
    
    y_position = height - 110
    
    # Process fields according to schema
    for _, field in schema_df.iterrows():
        if y_position < 100:  # Start new page if needed
            c.showPage()
            y_position = height - 50
        
        field_name = field['field_name']
        field_label = field['field_label']
        field_value = job_data.get(field_name, 'N/A')
        
        # Format field value based on type
        if field['field_type'] == 'password':
            display_value = '*' * len(str(field_value)) if field_value != 'N/A' else 'N/A'
        elif field['field_type'] == 'checkbox':
            display_value = 'Yes' if field_value else 'No'
        elif field['field_type'] == 'multiselect':
            display_value = ', '.join(field_value) if isinstance(field_value, list) else str(field_value)
        elif field['field_type'] == 'number':
            if 'cost' in field_name.lower():
                display_value = f"${float(field_value):.2f}" if field_value != 'N/A' else 'N/A'
            else:
                display_value = str(field_value)
        else:
            display_value = str(field_value)
        
        # Draw field
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, y_position, f"{field_label}:")
        c.setFont("Helvetica", 11)
        
        # Handle long text
        if len(display_value) > 50:
            lines = [display_value[i:i+70] for i in range(0, len(display_value), 70)]
            for i, line in enumerate(lines):
                c.drawString(300, y_position - (i * 15), line)
            y_position -= (len(lines) * 15) + 5
        else:
            c.drawString(300, y_position, display_value)
            y_position -= 20
    
    # Terms and Conditions
    if y_position < 200:
        c.showPage()
        y_position = height - 50
    
    y_position -= 20
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, y_position, "Terms and Conditions:")
    y_position -= 20
    
    c.setFont("Helvetica", 10)
    terms = [
        "1. All repairs are subject to inspection and may require additional approval.",
        "2. Estimated costs are subject to change based on final diagnosis.",
        "3. Devices unclaimed after 30 days may be disposed of.",
        "4. We are not responsible for data loss during repairs.",
        "5. Deposit may be required for expensive repairs."
    ]
    y_pos = 220
    for term in terms:
        c.drawString(100, y_pos, term)
        y_pos -= 20
    
    c.drawString(100, 100, "Customer Signature: __________________________")
    c.drawString(400, 100, "Staff Signature: __________________________")
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()