import streamlit as st
import pandas as pd
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.jobdetailmodal import show_job_details_modal
from components.datamanager.databasemanger import DatabaseManager
from components.updatestatusmodal import show_update_status_modal
from components.utils.pdf import generate_invoice_pdf_stream
from components.conformation_reopen import show_reopen_confirmation_modal

# Database connection manager
db = DatabaseManager()
conn = db.get_connection()

def view_jobs_tab(conn, user):
    """Enhanced Jobs Management with Status-based Tabs, Payment Section and Role-based Access"""

    # Search functionality at the top
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input("🔍 Search jobs (customer name, email, phone, job ID, device, problem)", placeholder="Type to search...")
    with col2:
        device_filter = st.selectbox("Device Type", ["All", "Smartphone", "Tablet", "Laptop", "Desktop", "Watch", "Other"])
    
    # Create tabs for different status types including payment section
    tab1, tab2, tab3, tab4 = st.tabs(["🆕 New Jobs", "⚙️ In Progress", "✅ Completed", "💰 Payment"])
    
    # Helper function to get jobs by status with role-based filtering
    def get_jobs_by_status(status, payment_filter=None):
        base_query = '''
        SELECT 
            j.id,
            j.created_at,
            c.name AS customer_name,
            c.phone AS customer_phone,
            c.email AS customer_email,
            j.device_type,
            j.device_model,
            j.problem_description,
            j.status,
            j.deposit_cost,
            j.raw_cost,
            j.estimate_cost,
            j.actual_cost,
            j.payment_status,
            j.payment_method,
            u.full_name AS technician,
            s.name AS store_name,
            s.location AS store_location,
            j.completed_at
        FROM jobs j
        JOIN customers c ON j.customer_id = c.id
        LEFT JOIN stores s ON j.store_id = s.id
        LEFT JOIN assignment_jobs aj ON aj.job_id = j.id
        LEFT JOIN technician_assignments ta ON ta.id = aj.assignment_id AND ta.status = 'active'
        LEFT JOIN users u ON u.id = ta.technician_id
        WHERE j.status = ?
        '''

        params = [status]

        # Add payment filter
        if payment_filter:
            if payment_filter == "completed":
                base_query += " AND j.payment_status = 'Completed'"
            elif payment_filter == "pending":
                base_query += " AND j.payment_status != 'Completed'"

        # Role-based filtering
        if user['role'] == 'admin':
            pass
        elif user['role'] in ['manager', 'staff']:
            if user.get('store_id'):
                base_query += " AND j.store_id = ?"
                params.append(user['store_id'])
        elif user['role'] == 'technician':
            base_query += " AND ta.technician_id = ?"
            params.append(user['id'])

        # Enhanced search filter
        if search_term:
            base_query += '''
            AND (
                c.name LIKE ? OR
                c.email LIKE ? OR
                c.phone LIKE ? OR
                j.device_type LIKE ? OR
                j.problem_description LIKE ? OR
                CAST(j.id AS TEXT) LIKE ?
            )
            '''
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern]*6)

        # Optional device filter
        if device_filter != "All":
            base_query += " AND j.device_type = ?"
            params.append(device_filter)

        base_query += " ORDER BY j.created_at DESC"

        return pd.read_sql(base_query, conn, params=params)
    
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
    def display_job_card(jobs_df, tab_status, payment_section=False):
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

    # Check for active modals
    active_modal = None
    active_job_id = None
    
    for key, value in st.session_state.items():
        if key.startswith("show_details_") and value:
            active_modal = "details"
            active_job_id = int(key.replace("show_details_", ""))
            break
        elif key.startswith("show_update_") and value:
            active_modal = "update"
            active_job_id = int(key.replace("show_update_", ""))
            break
        elif key.startswith("show_reopen_confirm_") and value:
            active_modal = "reopen_confirm"
            active_job_id = int(key.replace("show_reopen_confirm_", ""))
            break
    
    # Tab 1: New Jobs
    with tab1:
        new_jobs = get_jobs_by_status("New")
        st.markdown(f"**Total New Jobs: {len(new_jobs)}**")
        display_job_card(new_jobs, "New")
    
    # Tab 2: In Progress Jobs  
    with tab2:
        progress_jobs = get_jobs_by_status("In Progress")
        st.markdown(f"**Total In Progress: {len(progress_jobs)}**")
        display_job_card(progress_jobs, "In Progress")
    
    # Tab 3: Completed Jobs
    with tab3:
        completed_jobs = get_jobs_by_status("Completed")
        st.markdown(f"**Total Completed: {len(completed_jobs)}**")
        display_job_card(completed_jobs, "Completed")
    
    # Tab 4: Payment Section
    with tab4:
        st.markdown("### 💰 Payment  Process")
        
        # Create sub-tabs for payment status
        payment_tab1, payment_tab2 = st.tabs(["🔴 Payment Pending", "🟢 Payment Completed"])
        
        with payment_tab1:
            payment_pending_jobs = get_jobs_by_status("Completed", payment_filter="pending")
            st.markdown(f"**Total Payment Pending: {len(payment_pending_jobs)}**")
            display_job_card(payment_pending_jobs, "Payment Pending", payment_section=True)
        
        with payment_tab2:
            payment_completed_jobs = get_jobs_by_status("Completed", payment_filter="completed")
            st.markdown(f"**Total Payment Completed: {len(payment_completed_jobs)}**")
            display_job_card(payment_completed_jobs, "Payment Completed", payment_section=True)
    
    # Handle modals outside of tabs
    if active_modal == "details" and active_job_id:
        show_job_details_modal(conn, active_job_id, editable=(user['role'] in ['admin', 'manager']))
    elif active_modal == "update" and active_job_id:
        status_to_update = st.session_state[f"show_update_{active_job_id}"]
        show_update_status_modal(conn, active_job_id, status_to_update)
    elif active_modal == "reopen_confirm" and active_job_id:
        # Show reopen confirmation modal
        show_reopen_confirmation_modal(conn, active_job_id)