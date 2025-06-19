import streamlit as st
import pandas as pd
import os 
import sys 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.jobdetailmodal import show_job_details_modal
from components.datamanager.databasemanger import DatabaseManager
from components.updatestatusmodal import show_update_status_modal
# Database connection manager
db = DatabaseManager()
conn = db.get_connection()

def view_jobs_tab(conn, user):
    """Enhanced Jobs Management with Status-based Tabs"""

    
    # Search functionality at the top
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input("🔍 Search jobs (customer name, device, problem)", placeholder="Type to search...")
    with col2:
        device_filter = st.selectbox("Device Type", ["All", "Smartphone", "Tablet", "Laptop", "Desktop", "Watch", "Other"])
    
    # Create tabs for different status types
    tab1, tab2, tab3 = st.tabs(["🆕 New Jobs", "⚙️ In Progress", "✅ Completed"])
    
    # Helper function to get jobs by status
    def get_jobs_by_status(status):
        query = '''
        SELECT 
            j.id,
            j.created_at,
            c.name AS customer_name,
            c.phone AS customer_phone,
            j.device_type,
            j.device_model,
            j.problem_description,
            j.status,
            j.estimated_cost,
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
        
        # Add store filter if user has store_id
        if user.get('store_id'):
            query += " AND j.store_id = ?"
            params.append(user['store_id'])
        
        # Add search filter
        if search_term:
            query += " AND (c.name LIKE ? OR j.device_type LIKE ? OR j.problem_description LIKE ?)"
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        # Add device filter
        if device_filter != "All":
            query += " AND j.device_type = ?"
            params.append(device_filter)
        
        query += " ORDER BY j.created_at DESC"
        
        return pd.read_sql(query, conn, params=params)
    
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
                            - Estimated: ${job['estimated_cost'] or 0:.2f}  
                            - Raw: ${job['raw_cost'] or 0:.2f}  
                            - Final: ${job['actual_cost'] or 0:.2f}  
                            - <strong style="color:{profit_color}">Profit: ${profit:.2f}</strong>
                            """, unsafe_allow_html=True)
                        
                        st.markdown(f"**📅 Created:** {pd.to_datetime(job['created_at']).strftime('%Y-%m-%d %H:%M')}")
                        if job['technician']:
                            st.markdown(f"**👨‍🔧 Tech:** {job['technician']}")
                    
                    with col3:
                        # View Details button
                        if st.button(f"👁️ View", key=f"view_{job['id']}"):
                            st.session_state[f"show_details_{job['id']}"] = True
                        
                        # Status change buttons based on current status
                        if tab_status == "New":
                            if st.button(f"▶️ Start", key=f"start_{job['id']}", type="primary"):
                                st.session_state[f"show_update_{job['id']}"] = "In Progress"
                                st.rerun()
                        
                        elif tab_status == "In Progress":
                            if st.button(f"✅ Complete", key=f"complete_{job['id']}", type="primary"):
                                st.session_state[f"show_update_{job['id']}"] = "Completed"
                                st.rerun()
        else:
            st.info(f"No {tab_status.lower()} jobs found.")
    
    # Tab 1: New Jobs
    with tab1:
        new_jobs = get_jobs_by_status("New")
        st.markdown(f"**Total New Jobs: {len(new_jobs)}**")
        display_job_card(new_jobs, "New")
        
        # Check for modals in New Jobs tab
        for idx, job in new_jobs.iterrows():
            if st.session_state.get(f"show_details_{job['id']}", False):
                show_job_details_modal(conn, job['id'])
            if st.session_state.get(f"show_update_{job['id']}", False):
                show_update_status_modal(conn, job['id'], st.session_state[f"show_update_{job['id']}"])
    
    # Tab 2: In Progress Jobs  
    with tab2:
        progress_jobs = get_jobs_by_status("In Progress")
        st.markdown(f"**Total In Progress: {len(progress_jobs)}**")
        display_job_card(progress_jobs, "In Progress")
        
        # Check for modals in In Progress tab
        for idx, job in progress_jobs.iterrows():
            if st.session_state.get(f"show_details_{job['id']}", False):
                show_job_details_modal(conn, job['id'])
            if st.session_state.get(f"show_update_{job['id']}", False):
                show_update_status_modal(conn, job['id'], st.session_state[f"show_update_{job['id']}"])
    
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
        
        # Check for modals in Completed tab
        for idx, job in completed_jobs.iterrows():
            if st.session_state.get(f"show_details_{job['id']}", False):
                show_job_details_modal(conn, job['id'], editable=False)

