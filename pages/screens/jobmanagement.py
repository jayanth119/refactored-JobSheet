import sys 
import os 
import pandas as pd 
import streamlit as st
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.css.css import Style
from components.datamanager.databasemanger import DatabaseManager
from components.utils.auth import hash_password , verify_password,authenticate_user , create_user
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
    
    # Tabs for different job operations
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
                    "Gaming Console", "TV", "Other Electronics"
                ])
                device_model = st.text_input("Device Model", placeholder="e.g., iPhone 13, MacBook Pro")
                estimated_cost = st.number_input("Estimated Cost ($)", min_value=0.0, value=0.0, step=0.01)
            
            with col2:
                problem_description = st.text_area("Problem Description*", 
                                                 placeholder="Describe the issue in detail",
                                                 height=100)
                
                # Get technicians for current store (or all for admin)
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
                        store_id = user['store_id'] if user['role'] == 'staff' else 1  # Default to first store for admin
                        tech_name = technician if technician != "Unassigned" else None
                        
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO jobs (customer_name, device_type, device_model, 
                                            problem_description, estimated_cost, status, 
                                            technician, store_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (customer_name, device_type, device_model, problem_description,
                             estimated_cost, status, tech_name, store_id))
                        
                        job_id = cursor.lastrowid
                        conn.commit()
                        
                        st.success(f"✅ Job #{job_id} created successfully!")
                        
                    except Exception as e:
                        st.error(f"❌ Error creating job: {str(e)}")
                else:
                    st.error("⚠️ Please fill in all required fields")
    
    with tab2:
        st.markdown("### Current Jobs")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Filter by Status", ["All", "New", "In Progress", "Completed", "Pending"])
        with col2:
            device_filter = st.selectbox("Filter by Device", ["All", "Smartphone", "Laptop", "Desktop", "Tablet", "Other"])
        with col3:
            sort_by = st.selectbox("Sort by", ["Recent First", "Oldest First", "Customer Name", "Status"])
        
        # Build query based on user role and filters
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
        
        # Add sorting
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
            # Display jobs in a more interactive way
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
                    
                    # Quick action buttons
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        if st.button(f"✏️ Edit", key=f"edit_{job['id']}"):
                            st.session_state[f"edit_job_{job['id']}"] = True
                    with col2:
                        if st.button(f"🔄 Update Status", key=f"status_{job['id']}"):
                            st.session_state[f"update_status_{job['id']}"] = True
                    with col3:
                        if st.button(f"💰 Update Cost", key=f"cost_{job['id']}"):
                            st.session_state[f"update_cost_{job['id']}"] = True
                    with col4:
                        if st.button(f"🗑️ Delete", key=f"delete_{job['id']}"):
                            if st.session_state.get(f"confirm_delete_{job['id']}", False):
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM jobs WHERE id = ?", (job['id'],))
                                conn.commit()
                                st.success(f"Job #{job['id']} deleted successfully!")
                                st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{job['id']}"] = True
                                st.warning("Click delete again to confirm")
        else:
            st.info("No jobs found matching your criteria")
    
    with tab3:
        st.markdown("### Search Jobs")
        
        search_term = st.text_input("🔍 Search by customer name, device, or problem description")
        
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
                    status_class = f"status-{job['status'].lower().replace(' ', '-')}"
                    store_info = f" | 🏪 {job['store_name']}" if user['role'] == 'admin' else ""
                    
                    st.markdown(f'''
                        <div class="job-card">
                            <div class="job-title">#{job['id']} - {job['customer_name']}{store_info}</div>
                            <div class="job-details">{job['device_type']} - {job['device_model']}</div>
                            <div class="job-details">{job['problem_description']}</div>
                            <div class="job-details">👨‍🔧 {job['technician'] or 'Unassigned'} | 📅 {job['created_at'][:10]}</div>
                            <span class="{status_class}">{job['status']}</span>
                        </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info("No jobs found matching your search term")
    
    conn.close()