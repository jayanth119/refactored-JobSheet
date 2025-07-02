import streamlit as st
import pandas as pd
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager
from components.utils.pdf import generate_invoice_pdf_stream
db = DatabaseManager()
conn = db.get_connection()
# Helper function to update payment information
def update_payment_info(job_id, payment_method, payment_status):
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE jobs 
            SET payment_method = ?, payment_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (payment_method, payment_status, job_id))
        conn.commit()
        st.success("Payment information updated successfully!")
        st.rerun()
    
    # Helper function to update raw cost (admin only)
def update_raw_cost(job_id, raw_cost):
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE jobs 
            SET raw_cost = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (raw_cost, job_id))
        conn.commit()
        st.success("Raw cost updated successfully!")
        st.rerun()
 # Helper function to display job card with action buttons
def display_job_card(jobs_df, tab_status, payment_section=False, user = None):
        if len(jobs_df) > 0:
            for idx, job in jobs_df.iterrows():
                with st.container():
                    st.markdown("---")
                    
                    if payment_section:
                        # Payment section layout
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                        
                        with col1:
                            st.markdown(f"""
                            **#{job['id']} - {job['customer_name']}**  
                            📱 {job['device_type']} {job['device_model'] if pd.notna(job['device_model']) else ''}  
                            📞 {job['customer_phone']}  
                            🔧 {job['problem_description'][:60]}{'...' if len(str(job['problem_description'])) > 60 else ''}
                            """)
                        
                        with col2:
                            st.markdown(f"**💰 Costs:**")
                            st.markdown(f"Deposit: ₹{job['deposit_cost'] or 0}")
                            st.markdown(f"Actual: ₹{job['actual_cost'] or 0}")
                            if job['raw_cost']:
                                st.markdown(f"Raw: ₹{job['raw_cost']}")
                        
                        with col3:
                            st.markdown(f"**📊 Payment:**")
                            status_color = "🟢" if job['payment_status'] == 'Completed' else "🔴"
                            st.markdown(f"{status_color} {job['payment_status']}")
                            if job['payment_method']:
                                st.markdown(f"Method: {job['payment_method']}")
                        
                        with col4:
                            # Payment action buttons
                            if job['payment_status'] != 'Completed':
                                # Show payment form
                                with st.form(f"payment_form_{job['id']}"):
                                    payment_method = st.selectbox(
                                        "Payment Method",
                                        ["Cash", "Card", "UPI", "Bank Transfer", "Other"],
                                        key=f"payment_method_{job['id']}"
                                    )
                                    
                                    if st.form_submit_button("Mark as Paid", type="primary"):
                                        update_payment_info(job['id'], payment_method, "Completed")
                            
                            # Admin can update raw cost
                            if user['role'] == 'admin':
                                with st.form(f"raw_cost_form_{job['id']}"):
                                    raw_cost = st.number_input(
                                        "Raw Cost",
                                        min_value=0.0,
                                        value=float(job['raw_cost'] or 0),
                                        step=0.01,
                                        key=f"raw_cost_{job['id']}"
                                    )
                                    
                                    if st.form_submit_button("Update Raw Cost"):
                                        update_raw_cost(job['id'], raw_cost)
                            
                            # View details button
                            if st.button(f"👁️ View", key=f"view_{job['id']}_{tab_status}"):
                                for key in list(st.session_state.keys()):
                                    if key.startswith("show_details_"):
                                        del st.session_state[key]
                                st.session_state[f"show_details_{job['id']}"] = True
                                st.rerun()
                                
                            # Download invoice if payment completed
                            if job['payment_status'] == 'Completed':
                                try:
                                    pdf_bytes = generate_invoice_pdf_stream(job['id'], status="Completed")
                                    st.download_button(
                                        "📥 Invoice", 
                                        data=pdf_bytes, 
                                        file_name=f"invoice_job_{job['id']}.pdf", 
                                        mime="application/pdf",
                                        key=f"download_invoice_{job['id']}"
                                    )
                                except Exception as e:
                                    st.error(f"Error generating invoice: {str(e)}")
                    
                    else:
                        # Regular job card layout
                        col1, col2, col3 = st.columns([3, 2, 1])
                        
                        with col1:
                            st.markdown(f"""
                            **#{job['id']} - {job['customer_name']}**  
                            📱 {job['device_type']} {job['device_model'] if pd.notna(job['device_model']) else ''}  
                            📞 {job['customer_phone']}  
                            🔧 {job['problem_description'][:80]}{'...' if len(str(job['problem_description'])) > 80 else ''}
                            """)
                        
                        with col2:
                            st.markdown(f"**📅 Created:** {pd.to_datetime(job['created_at']).strftime('%Y-%m-%d %H:%M')}")
                            if job['technician']:
                                st.markdown(f"**👨‍🔧 Tech:** {job['technician']}")
                        
                        with col3:
                            # View Details button
                            if st.button(f"👁️ View", key=f"view_{job['id']}_{tab_status}"):
                                for key in list(st.session_state.keys()):
                                    if key.startswith("show_details_") or key.startswith("show_update_") or key.startswith("show_preview_"):
                                        del st.session_state[key]
                                st.session_state[f"show_details_{job['id']}"] = True
                                st.rerun()
                                          
                            # Download invoice button for completed jobs only
                            if tab_status == "Completed":
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute("SELECT id FROM jobs WHERE id = ?", (job['id'],))
                                    if cursor.fetchone():
                                        pdf_bytes = generate_invoice_pdf_stream(job['id'], status=tab_status)
                                        st.download_button(
                                            "📥 Download Invoice", 
                                            data=pdf_bytes, 
                                            file_name=f"invoice_job_{job['id']}.pdf", 
                                            mime="application/pdf",
                                            key=f"download_{job['id']}_{tab_status}"
                                        )
                                    else:
                                        st.error("Job not found")
                                except Exception as e:
                                    st.error(f"Error generating invoice: {str(e)}")
                            
                            # Download Job Sheet button for new and in progress jobs only
                            if tab_status in ["New", "In Progress"]:
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute("SELECT id FROM jobs WHERE id = ?", (job['id'],))
                                    if cursor.fetchone():
                                        pdf_bytes = generate_invoice_pdf_stream(job['id'], status=tab_status)
                                        st.download_button(
                                            "📥 Download JobSheet", 
                                            data=pdf_bytes, 
                                            file_name=f"jobsheet_{job['id']}.pdf", 
                                            mime="application/pdf",
                                            key=f"download_{job['id']}_{tab_status}"
                                        )
                                    else:
                                        st.error("Job not found")
                                except Exception as e:
                                    st.error(f"Error generating invoice: {str(e)}")
                            
                            # Status change buttons
                            if user['role'] in ['admin', 'manager', 'technician']:
                                if tab_status == "New":
                                    if st.button(f"▶️ Start", key=f"start_{job['id']}_{tab_status}", type="primary"):
                                        st.session_state[f"show_update_{job['id']}"] = "In Progress"
                                        st.rerun()
                                
                                elif tab_status == "In Progress":
                                    if st.button(f"✅ Complete", key=f"complete_{job['id']}_{tab_status}", type="primary"):
                                        st.session_state[f"show_update_{job['id']}"] = "Completed"
                                        st.rerun()
                                
                                elif tab_status == "Completed":
                                    # Add Reopen button for completed jobs
                                    if st.button(f"🔄 Reopen", key=f"reopen_{job['id']}_{tab_status}", type="secondary"):
                                        # Show confirmation dialog
                                        st.session_state[f"show_reopen_confirm_{job['id']}"] = True
                                        st.rerun()

        else:
            section_name = "payment pending" if tab_status == "Payment Pending" else "payment completed" if tab_status == "Payment Completed" else tab_status.lower()
            st.info(f"No {section_name} jobs found.")