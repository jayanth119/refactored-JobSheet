import streamlit as st
import pandas as pd
import os
import sys
import qrcode
import io
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.jobdetailmodal import show_job_details_modal
from components.datamanager.databasemanger import DatabaseManager
from components.updatestatusmodal import show_update_status_modal
from components.utils.pdf import generate_invoice_pdf_stream

# Database connection manager
db = DatabaseManager()
conn = db.get_connection()

def display_bill_preview(conn, job_id, customer_name, customer_phone, device_type, device_model, problem_description, deposit_cost, actual_cost, status):
    """Display the bill preview in a structured dialog format matching the screenshot"""
    
    # Main container with styling
    st.markdown(f"""
    <div style="
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        background-color: #ffffff;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    ">
    <h2 style="border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 20px;">
        Job Details - #{job_id}
    </h2>
    """, unsafe_allow_html=True)
    
    # Customer Information Section
    st.markdown("## Customer Information")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Name:** {customer_name}")
        st.markdown(f"**Phone:** {customer_phone}")
    with col2:
        # Get store information from database
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.name, s.location 
            FROM jobs j
            JOIN stores s ON j.store_id = s.id
            WHERE j.id = ?
        """, (job_id,))
        store_info = cursor.fetchone()
        
        if store_info:
            st.markdown(f"**Store:** {store_info[0]}")
            st.markdown(f"**Location:** {store_info[1]}")
    
    st.markdown("---")
    
    # Device Information Section
    st.markdown("### Device Information")
    st.markdown(f"- **Device Type:** {device_type}")
    st.markdown(f"- **Model:** {device_model}")
    
    # Get technician information
    cursor.execute("""
        SELECT u.full_name 
        FROM users u
        JOIN technician_assignments ta ON u.id = ta.technician_id
        JOIN assignment_jobs aj ON ta.id = aj.assignment_id
        WHERE aj.job_id = ? AND ta.status = 'active'
    """, (job_id,))
    technician = cursor.fetchone()
    
    if technician:
        st.markdown(f"- **Technician:** {technician[0]}")
    
    st.markdown("---")
    
    # Problem Description Section
    st.markdown("### Problem Description")
    st.markdown(f"- {problem_description}")
    
    st.markdown("---")
    
    # Cost Information Section
    st.markdown("### Cost Summary")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Deposit Paid:** ${deposit_cost:.2f}")
    with col2:
        st.markdown(f"**Estimated Cost:** ${actual_cost:.2f}")
    
    st.markdown("---")
    
    # Action Buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📋 Bill Preview", key=f"preview_{job_id}"):
            pass  # Already in preview mode
    
    with col2:
        if status == "New":
            if st.button("▶️ Start", key=f"start_{job_id}"):
                st.session_state[f"show_update_{job_id}"] = "In Progress"
                st.rerun()
    
    with col3:
        if st.button("👁️ View", key=f"view_{job_id}"):
            st.session_state[f"show_details_{job_id}"] = True
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Generate QR code for status tracking
    st.markdown("---")
    st.markdown("#### Status QR Code")
    try:
        qr_url = f"https://jayanth119-refactored-jobsheet-main-vtllnj.streamlit.app//repair_status?job_id={job_id}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        
        st.image(img_bytes, width=150)
        st.caption("Scan to track repair status")
    except Exception as e:
        st.error(f"Failed to generate QR code: {str(e)}")
