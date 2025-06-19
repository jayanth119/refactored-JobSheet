import streamlit as st
import pandas as pd
import os 
import sys 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.jobdetailmodal import show_job_details_modal
from components.datamanager.databasemanger import DatabaseManager
from components.updatestatusmodal import show_update_status_modal
from components.utils.pdf import generate_invoice_pdf_stream 

# Database connection manager
db = DatabaseManager()
conn = db.get_connection()

def view_jobs_tab(conn, user):
    """Enhanced Jobs Management with Status-based Tabs and Role-based Access"""

    # Search functionality at the top
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input("🔍 Search jobs (customer name, device, problem)", placeholder="Type to search...")
    with col2:
        device_filter = st.selectbox("Device Type", ["All", "Smartphone", "Tablet", "Laptop", "Desktop", "Watch", "Other"])
    
    # Create tabs for different status types
    tab1, tab2, tab3 = st.tabs(["🆕 New Jobs", "⚙️ In Progress", "✅ Completed"])
    
    # Helper function to get jobs by status with role-based filtering
    def get_jobs_by_status(status):
        base_query = '''
        SELECT 
            j.id,
            j.created_at,
            c.name AS customer_name,
            c.phone AS customer_phone,
            j.device_type,
            j.device_model,
            j.problem_description,
            j.status,
            j.deposit_cost,
            j.raw_cost,
            j.actual_cost,
            u.full_name AS technician,
            s.name AS store_name
        FROM jobs j
        JOIN customers c ON j.customer_id = c.id
        LEFT JOIN stores s ON j.store_id = s.id
        LEFT JOIN assignment_jobs aj ON aj.job_id = j.id
        LEFT JOIN technician_assignments ta ON ta.id = aj.assignment_id AND ta.status = 'active'
        LEFT JOIN users u ON u.id = ta.technician_id
        WHERE j.status = ?
        '''
        
        params = [status]
        
        # Role-based filtering
        if user['role'] == 'admin':
            # Admins can see all jobs
            pass
        elif user['role'] in ['manager', 'staff']:
            # Managers and staff can only see jobs from their store(s)
            if user.get('store_id'):
                base_query += " AND j.store_id = ?"
                params.append(user['store_id'])
        elif user['role'] == 'technician':
            # Technicians can only see jobs assigned to them
            base_query += " AND ta.technician_id = ?"
            params.append(user['id'])
        
        # Add search filter
        if search_term:
            base_query += " AND (c.name LIKE ? OR j.device_type LIKE ? OR j.problem_description LIKE ?)"
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        # Add device filter
        if device_filter != "All":
            base_query += " AND j.device_type = ?"
            params.append(device_filter)
        
        base_query += " ORDER BY j.created_at DESC"
        
        return pd.read_sql(base_query, conn, params=params)
    
    # Helper function to display job card with action buttons
    def display_job_card(jobs_df, tab_status):
        if len(jobs_df) > 0:
            for idx, job in jobs_df.iterrows():
                with st.container():
                    st.markdown("---")
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"""
                        **#{job['id']} - {job['customer_name']}**  
                        📱 {job['device_type']} {job['device_model'] if pd.notna(job['device_model']) else ''}  
                        📞 {job['customer_phone']}  
                        🔧 {job['problem_description'][:80]}{'...' if len(str(job['problem_description'])) > 80 else ''}
                        """)
                    
                    with col2:
                        profit = (job['actual_cost'] or 0) - (job['raw_cost'] or 0)
                        profit_color = "green" if profit > 0 else "red" if profit < 0 else "gray"
                        
                        st.markdown(f"""
                            **💰 Costs:**  
                            - Deposit: ${job['deposit_cost'] or 0:.2f}  
                            - Raw: ${job['raw_cost'] or 0:.2f}  
                            - Final: ${job['actual_cost'] or 0:.2f}  
                            - <strong style="color:{profit_color}">Profit: ${profit:.2f}</strong>
                            """, unsafe_allow_html=True)
                        
                        st.markdown(f"**📅 Created:** {pd.to_datetime(job['created_at']).strftime('%Y-%m-%d %H:%M')}")
                        if job['technician']:
                            st.markdown(f"**👨‍🔧 Tech:** {job['technician']}")
                    
                    with col3:
                        # View Details button
                        if st.button(f"👁️ View", key=f"view_{job['id']}_{tab_status}"):
                            # Clear other modal states
                            for key in list(st.session_state.keys()):
                                if key.startswith("show_details_") or key.startswith("show_update_"):
                                    del st.session_state[key]
                            st.session_state[f"show_details_{job['id']}"] = True
                            st.rerun()
                        
                        # Download invoice button for completed jobs only
                        if tab_status == "Completed":
                            try:
                                # Verify job exists before generating PDF
                                cursor = conn.cursor()
                                cursor.execute("SELECT id FROM jobs WHERE id = ?", (job['id'],))
                                if cursor.fetchone():
                                    pdf_bytes = generate_invoice_pdf_stream(job['id'])
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
                        
                        # Status change buttons based on current status and user role
                        if user['role'] in ['admin', 'manager', 'technician']:
                            if tab_status == "New":
                                if st.button(f"▶️ Start", key=f"start_{job['id']}_{tab_status}", type="primary"):
                                    # Clear other modal states
                                    for key in list(st.session_state.keys()):
                                        if key.startswith("show_details_") or key.startswith("show_update_"):
                                            del st.session_state[key]
                                    st.session_state[f"show_update_{job['id']}"] = "In Progress"
                                    st.rerun()
                            
                            elif tab_status == "In Progress":
                                if st.button(f"✅ Complete", key=f"complete_{job['id']}_{tab_status}", type="primary"):
                                    # Clear other modal states
                                    for key in list(st.session_state.keys()):
                                        if key.startswith("show_details_") or key.startswith("show_update_"):
                                            del st.session_state[key]
                                    st.session_state[f"show_update_{job['id']}"] = "Completed"
                                    st.rerun()
        else:
            st.info(f"No {tab_status.lower()} jobs found.")

    # Check for active modals (only one at a time)
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
        
        if len(completed_jobs) > 0:
            # Show profit summary for completed jobs
            total_profit = (completed_jobs['actual_cost'].fillna(0) - completed_jobs['raw_cost'].fillna(0)).sum()
            avg_profit = total_profit / len(completed_jobs) if len(completed_jobs) > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Profit", f"${total_profit:.2f}")
            with col2:
                st.metric("Average Profit", f"${avg_profit:.2f}")
            with col3:
                st.metric("Jobs Completed", len(completed_jobs))
        
        display_job_card(completed_jobs, "Completed")
    
    # Handle modals outside of tabs to avoid conflicts
    if active_modal == "details" and active_job_id:
        show_job_details_modal(conn, active_job_id, editable=(user['role'] in ['admin', 'manager']))
    elif active_modal == "update" and active_job_id:
        status_to_update = st.session_state[f"show_update_{active_job_id}"]
        show_update_status_modal(conn, active_job_id, status_to_update)