import sys
import os
import pandas as pd
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.css.css import Style
from components.datamanager.databasemanger import DatabaseManager
from components.utils.auth import (
    hash_password, verify_password, authenticate_user, create_user
)
from pages.screens.loginpage import login_signup_page
from pages.screens.admindashboard import admin_dashboard
from components.sidebarnavigation import sidebar_navigation

def jobs_management():
    user = st.session_state.user

    st.markdown(f'''
        <div class="main-header">
            <h1>📋 Jobs Management</h1>
            <p>Manage repair jobs for {user['store_name'] if user['role'] == 'staff' else 'all stores'}</p>
        </div>
    ''', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📝 Add New Job", "📋 View Jobs", "🔍 Search Jobs"])

    db = DatabaseManager()
    conn = db.get_connection()

    with tab1:
        st.markdown("### Create New Repair Job")
        with st.form("new_job_form"):
            col1, col2 = st.columns(2)

            with col1:
                customer_name = st.text_input("Customer Name*", placeholder="Enter customer name")
                device_type = st.selectbox("Device Type*", [
                    "Smartphone", "Laptop", "Desktop", "Tablet", "Smart Watch", 
                    "Gaming Console", "TV", "Other Electronics"])
                device_model = st.text_input("Device Model", placeholder="e.g., iPhone 13, MacBook Pro")
                estimated_cost = st.number_input("Estimated Cost ($)", min_value=0.0, value=0.0, step=0.01)

            with col2:
                problem_description = st.text_area("Problem Description*", 
                    placeholder="Describe the issue in detail", height=100)
                if user['role'] == 'admin':
                    technicians = pd.read_sql("""
                        SELECT DISTINCT u.full_name, s.name as store_name
                        FROM users u
                        LEFT JOIN stores s ON u.store_id = s.id
                        WHERE u.role = 'staff'
                        ORDER BY u.full_name
                    """, conn)
                    tech_options = [f"{row['full_name']} ({row['store_name']})" for _, row in technicians.iterrows()]
                else:
                    technicians = pd.read_sql("""
                        SELECT full_name FROM users 
                        WHERE role = 'staff' AND store_id = ?
                        ORDER BY full_name
                    """, conn, params=[user['store_id']])
                    tech_options = technicians['full_name'].tolist()
                technician = st.selectbox("Assign Technician", ["Unassigned"] + tech_options)
                status = st.selectbox("Initial Status", ["New", "In Progress", "Pending"])

            submit_job = st.form_submit_button("🔧 Create Job", use_container_width=True)

            if submit_job:
                if customer_name and device_type and problem_description:
                    try:
                        store_id = user['store_id'] if user['role'] == 'staff' else 1
                        tech_name = technician if technician != "Unassigned" else None
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO jobs (customer_name, device_type, device_model, 
                                              problem_description, estimated_cost, status, 
                                              technician, store_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (customer_name, device_type, device_model, problem_description,
                              estimated_cost, status, tech_name, store_id))
                        conn.commit()
                        st.success(f"✅ Job #{cursor.lastrowid} created successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error creating job: {str(e)}")
                else:
                    st.error("⚠️ Please fill in all required fields")

    with tab2:
        st.markdown("### Current Jobs")
        col1, col2, col3 = st.columns(3)

        with col1:
            status_filter = st.selectbox("Filter by Status", ["All", "New", "In Progress", "Completed", "Pending"])
        with col2:
            device_filter = st.selectbox("Filter by Device", ["All", "Smartphone", "Laptop", "Desktop", "Tablet", "Other"])
        with col3:
            sort_by = st.selectbox("Sort by", ["Recent First", "Oldest First", "Customer Name", "Status"])

        base_query = """
            SELECT j.id, j.customer_name, j.device_type, j.device_model,
                   j.problem_description, j.estimated_cost, j.actual_cost,
                   j.status, j.technician, j.created_at, j.updated_at,
                   s.name as store_name
            FROM jobs j
            LEFT JOIN stores s ON j.store_id = s.id
        """

        conditions = []
        params = []

        if user['role'] == 'staff':
            conditions.append("j.store_id = ?")
            params.append(user['store_id'])

        if status_filter != "All":
            conditions.append("j.status = ?")
            params.append(status_filter)

        if device_filter != "All":
            conditions.append("j.device_type = ?")
            params.append(device_filter)

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        if sort_by == "Recent First":
            base_query += " ORDER BY j.created_at DESC"
        elif sort_by == "Oldest First":
            base_query += " ORDER BY j.created_at ASC"
        elif sort_by == "Customer Name":
            base_query += " ORDER BY j.customer_name ASC"
        elif sort_by == "Status":
            base_query += " ORDER BY j.status ASC"

        jobs_df = pd.read_sql(base_query, conn, params=params)

        if not jobs_df.empty:
            for _, job in jobs_df.iterrows():
                with st.expander(f"#{job['id']} - {job['customer_name']} | {job['device_type']} - {job['status']}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Device:** {job['device_type']} - {job['device_model']}")
                        st.write(f"**Problem:** {job['problem_description']}")
                        st.write(f"**Technician:** {job['technician'] or 'Unassigned'}")
                        if user['role'] == 'admin':
                            st.write(f"**Store:** {job['store_name']}")

                    with col2:
                        st.write(f"**Status:** {job['status']}")
                        st.write(f"**Estimated Cost:** ${job['estimated_cost']:.2f}")
                        st.write(f"**Actual Cost:** ${job['actual_cost']:.2f}")
                        st.write(f"**Created:** {job['created_at'][:10]}")

                    col1, col2, col3, col4 = st.columns(4)
                    
                    # Edit Job Button
                    with col1:
                        if st.button("✏️ Edit", key=f"edit_{job['id']}", help="Edit job details"):
                            st.session_state[f"edit_mode_{job['id']}"] = True
                            st.rerun()
                    
                    # Update Status Button
                    with col2:
                        if st.button("🔄 Update Status", key=f"status_{job['id']}", help="Update job status"):
                            st.session_state[f"status_mode_{job['id']}"] = True
                            st.rerun()
                    
                    # Update Cost Button
                    with col3:
                        if st.button("💰 Update Cost", key=f"cost_{job['id']}", help="Update job cost"):
                            st.session_state[f"cost_mode_{job['id']}"] = True
                            st.rerun()
                    
                    # Delete Button
                    with col4:
                        if st.button("🗑️ Delete", key=f"delete_{job['id']}"):
                            if st.session_state.get(f"confirm_delete_{job['id']}", False):
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM jobs WHERE id = ?", (job['id'],))
                                conn.commit()
                                st.success(f"Job #{job['id']} deleted successfully!")
                                # Clear the confirmation state
                                if f"confirm_delete_{job['id']}" in st.session_state:
                                    del st.session_state[f"confirm_delete_{job['id']}"]
                                st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{job['id']}"] = True
                                st.warning("Click delete again to confirm")

                    # Edit Mode Form
                    if st.session_state.get(f"edit_mode_{job['id']}", False):
                        st.markdown("---")
                        st.markdown("### Edit Job Details")
                        with st.form(f"edit_form_{job['id']}"):
                            edit_col1, edit_col2 = st.columns(2)
                            
                            with edit_col1:
                                new_customer_name = st.text_input("Customer Name", value=job['customer_name'], label_visibility="visible")
                                new_device_type = st.selectbox("Device Type", 
                                    ["Smartphone", "Laptop", "Desktop", "Tablet", "Smart Watch", "Gaming Console", "TV", "Other Electronics"],
                                    index=["Smartphone", "Laptop", "Desktop", "Tablet", "Smart Watch", "Gaming Console", "TV", "Other Electronics"].index(job['device_type']) if job['device_type'] in ["Smartphone", "Laptop", "Desktop", "Tablet", "Smart Watch", "Gaming Console", "TV", "Other Electronics"] else 0)
                                new_device_model = st.text_input("Device Model", value=job['device_model'] or "", label_visibility="visible")
                            
                            with edit_col2:
                                new_problem_description = st.text_area("Problem Description", value=job['problem_description'], label_visibility="visible")
                                new_estimated_cost = st.number_input("Estimated Cost ($)", value=float(job['estimated_cost']), min_value=0.0, step=0.01)
                            
                            submit_col1, submit_col2 = st.columns(2)
                            with submit_col1:
                                if st.form_submit_button("💾 Save Changes", use_container_width=True):
                                    try:
                                        cursor = conn.cursor()
                                        cursor.execute("""
                                            UPDATE jobs SET customer_name = ?, device_type = ?, device_model = ?, 
                                                           problem_description = ?, estimated_cost = ?, updated_at = CURRENT_TIMESTAMP
                                            WHERE id = ?
                                        """, (new_customer_name, new_device_type, new_device_model, 
                                              new_problem_description, new_estimated_cost, job['id']))
                                        conn.commit()
                                        st.success(f"✅ Job #{job['id']} updated successfully!")
                                        st.session_state[f"edit_mode_{job['id']}"] = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Error updating job: {str(e)}")
                            
                            with submit_col2:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    st.session_state[f"edit_mode_{job['id']}"] = False
                                    st.rerun()

                    # Status Update Mode
                    if st.session_state.get(f"status_mode_{job['id']}", False):
                        st.markdown("---")
                        st.markdown("### Update Job Status")
                        with st.form(f"status_form_{job['id']}"):
                            new_status = st.selectbox("New Status", 
                                ["New", "In Progress", "Completed", "Pending", "Cancelled"],
                                index=["New", "In Progress", "Completed", "Pending", "Cancelled"].index(job['status']) if job['status'] in ["New", "In Progress", "Completed", "Pending", "Cancelled"] else 0)
                            
                            status_notes = st.text_area("Status Update Notes (Optional)", placeholder="Add any notes about this status change...")
                            
                            submit_col1, submit_col2 = st.columns(2)
                            with submit_col1:
                                if st.form_submit_button("🔄 Update Status", use_container_width=True):
                                    try:
                                        cursor = conn.cursor()
                                        # If status is being changed to "Completed", also update completed_at
                                        if new_status == "Completed":
                                            cursor.execute("""
                                                UPDATE jobs SET status = ?, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                                                WHERE id = ?
                                            """, (new_status, job['id']))
                                        else:
                                            # For other statuses, just update status and updated_at
                                            cursor.execute("""
                                                UPDATE jobs SET status = ?, updated_at = CURRENT_TIMESTAMP
                                                WHERE id = ?
                                            """, (new_status, job['id']))
                                        conn.commit()
                                        st.success(f"✅ Job #{job['id']} status updated to {new_status}!")
                                        st.session_state[f"status_mode_{job['id']}"] = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Error updating status: {str(e)}")
                            
                            with submit_col2:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    st.session_state[f"status_mode_{job['id']}"] = False
                                    st.rerun()

                    # Cost Update Mode
                    if st.session_state.get(f"cost_mode_{job['id']}", False):
                        st.markdown("---")
                        st.markdown("### Update Job Cost")
                        with st.form(f"cost_form_{job['id']}"):
                            cost_col1, cost_col2 = st.columns(2)
                            
                            with cost_col1:
                                new_estimated_cost = st.number_input("Estimated Cost ($)", 
                                    value=float(job['estimated_cost']), min_value=0.0, step=0.01)
                            
                            with cost_col2:
                                new_actual_cost = st.number_input("Actual Cost ($)", 
                                    value=float(job['actual_cost']) if job['actual_cost'] else 0.0, min_value=0.0, step=0.01)
                            
                            cost_notes = st.text_area("Cost Update Notes (Optional)", placeholder="Add any notes about cost changes...")
                            
                            submit_col1, submit_col2 = st.columns(2)
                            with submit_col1:
                                if st.form_submit_button("💰 Update Cost", use_container_width=True):
                                    try:
                                        cursor = conn.cursor()
                                        cursor.execute("""
                                            UPDATE jobs SET estimated_cost = ?, actual_cost = ?, updated_at = CURRENT_TIMESTAMP
                                            WHERE id = ?
                                        """, (new_estimated_cost, new_actual_cost, job['id']))
                                        conn.commit()
                                        st.success(f"✅ Job #{job['id']} cost updated successfully!")
                                        st.session_state[f"cost_mode_{job['id']}"] = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Error updating cost: {str(e)}")
                            
                            with submit_col2:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    st.session_state[f"cost_mode_{job['id']}"] = False
                                    st.rerun()

        else:
            st.info("No jobs found matching your criteria")

    with tab3:
        st.markdown("### Search Jobs")
        search_term = st.text_input("🔍 Search by customer name, device, or problem description", label_visibility="visible")

        if search_term:
            search_query = """
                SELECT j.id, j.customer_name, j.device_type, j.device_model,
                       j.problem_description, j.status, j.technician, 
                       j.created_at, s.name as store_name
                FROM jobs j
                LEFT JOIN stores s ON j.store_id = s.id
                WHERE (j.customer_name LIKE ? OR j.device_type LIKE ? OR 
                       j.device_model LIKE ? OR j.problem_description LIKE ?)
            """
            params = [f"%{search_term}%"] * 4

            if user['role'] == 'staff':
                search_query += " AND j.store_id = ?"
                params.append(user['store_id'])

            search_query += " ORDER BY j.created_at DESC LIMIT 20"
            search_results = pd.read_sql(search_query, conn, params=params)

            if not search_results.empty:
                st.write(f"Found {len(search_results)} results:")
                for _, job in search_results.iterrows():
                    st.markdown(f'''
                        <div class="job-card">
                            <div class="job-title">#{job['id']} - {job['customer_name']}{f" | 🏪 {job['store_name']}" if user['role'] == 'admin' else ""}</div>
                            <div class="job-details">{job['device_type']} - {job['device_model']}</div>
                            <div class="job-details">{job['problem_description']}</div>
                            <div class="job-details">👨‍🔧 {job['technician'] or 'Unassigned'} | 🗓️ {job['created_at'][:10]}</div>
                            <span class="status-{job['status'].lower().replace(' ', '-')}">{job['status']}</span>
                        </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info("No jobs found matching your search term")

    conn.close()