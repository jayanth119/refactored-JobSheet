import streamlit as st
import pandas as pd
import sys
import os 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager
from pages.screens.createjob import create_job_tab 

def admin_dashboard(st):
    user = st.session_state.user
    
    st.markdown(f'''
        <div class="main-header">
            <h1>🏠 Admin Dashboard</h1>
            <p>Welcome back, {user['full_name']} | Managing {"All Stores" if user['role'] == 'admin' else "Store"}</p>
        </div>
    ''', unsafe_allow_html=True)
    
    db = DatabaseManager()
    conn = db.get_connection()

    # Get store_ids admin has access to
    if user['role'] == 'admin':
        store_ids_query = "SELECT store_id FROM user_stores WHERE user_id = ?"
        store_ids = [row['store_id'] for row in pd.read_sql(store_ids_query, conn, params=[user['id']]).to_dict('records')]
    else:
        store_ids = [user['store_id']]

    # === Total Jobs ===
    query = "SELECT COUNT(*) as count FROM jobs"
    params = []
    if store_ids:
        query += f" WHERE store_id IN ({','.join(['?'] * len(store_ids))})"
        params = store_ids
    total_jobs = pd.read_sql(query, conn, params=params).iloc[0]['count']

    # === Ongoing Jobs ===
    query = "SELECT COUNT(*) as count FROM jobs"
    where_clauses = ["status = 'In Progress'"]
    params = []
    if store_ids:
        where_clauses.insert(0, f"store_id IN ({','.join(['?'] * len(store_ids))})")
        params = store_ids
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    ongoing_jobs = pd.read_sql(query, conn, params=params).iloc[0]['count']

    # === Completed Today ===
    query = "SELECT COUNT(*) as count FROM jobs"
    where_clauses = ["status = 'Completed'", "DATE(completed_at) = DATE('now')"]
    params = []
    if store_ids:
        where_clauses.insert(0, f"store_id IN ({','.join(['?'] * len(store_ids))})")
        params = store_ids
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    completed_today = pd.read_sql(query, conn, params=params).iloc[0]['count']

    # === Total Revenue ===
    query = "SELECT COALESCE(SUM(actual_cost), 0) as revenue FROM jobs"
    where_clauses = ["status = 'Completed'"]
    params = []
    if store_ids:
        where_clauses.insert(0, f"store_id IN ({','.join(['?'] * len(store_ids))})")
        params = store_ids
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    total_revenue = pd.read_sql(query, conn, params=params).iloc[0]['revenue']

    # === Display Metrics ===
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'''<div class="metric-card"><div class="metric-number">{total_jobs}</div><div class="metric-label">Total Jobs</div></div>''', unsafe_allow_html=True)
    with col2:
        st.markdown(f'''<div class="metric-card"><div class="metric-number">{ongoing_jobs}</div><div class="metric-label">Ongoing Jobs</div></div>''', unsafe_allow_html=True)
    with col3:
        st.markdown(f'''<div class="metric-card"><div class="metric-number">{completed_today}</div><div class="metric-label">Completed Today</div></div>''', unsafe_allow_html=True)
    with col4:
        st.markdown(f'''<div class="metric-card"><div class="metric-number">${total_revenue:.0f}</div><div class="metric-label">Total Revenue</div></div>''', unsafe_allow_html=True)

    st.markdown("---")

    # === Search ===
    st.markdown("### Search Jobs")
    search_term = st.text_input("🔍 Search by customer name, device, or problem description", label_visibility="visible")

    if search_term:
        search_query = f"""
            SELECT 
                j.id, 
                c.name AS customer_name, 
                j.device_type, 
                j.device_model,
                j.problem_description, 
                j.status, 
                u.full_name AS technician, 
                j.created_at, 
                s.name AS store_name
            FROM jobs j
            LEFT JOIN customers c ON j.customer_id = c.id
            LEFT JOIN stores s ON j.store_id = s.id
            LEFT JOIN assignment_jobs aj ON j.id = aj.job_id
            LEFT JOIN technician_assignments ta ON aj.assignment_id = ta.id
            LEFT JOIN users u ON ta.technician_id = u.id
            WHERE (
                c.name LIKE ? OR 
                j.device_type LIKE ? OR 
                j.device_model LIKE ? OR 
                j.problem_description LIKE ?
            )
        """
        params = [f"%{search_term}%"] * 4

        if store_ids:
            placeholders = ",".join(["?"] * len(store_ids))
            search_query += f" AND j.store_id IN ({placeholders})"
            params.extend(store_ids)

        search_query += " ORDER BY j.created_at DESC LIMIT 20"
        search_results = pd.read_sql(search_query, conn, params=params)

        if not search_results.empty:
            st.write(f"Found {len(search_results)} results:")
            for _, job in search_results.iterrows():
                st.markdown(f'''
                    <div class="job-card">
                        <div class="job-title">#{job['id']} - {job['customer_name']} {f"| 🏪 {job['store_name']}" if user['role'] == 'admin' else ""}</div>
                        <div class="job-details">{job['device_type']} - {job['device_model']}</div>
                        <div class="job-details">{job['problem_description']}</div>
                        <div class="job-details">👨‍🔧 {job['technician'] or 'Unassigned'} | 🗓️ {job['created_at'][:10]}</div>
                        <span class="status-{job['status'].lower().replace(' ', '-')}">{job['status']}</span>
                    </div>
                ''', unsafe_allow_html=True)
        else:
            st.info("No jobs found matching your search term.")

    # === Store Performance ===
    col1, col2 = st.columns([6, 1])
    with col1:
        create_job_tab(conn, user, db)
        st.markdown("### 🏪 Store Performance Overview")

        if store_ids:
            placeholders = ",".join(["?"] * len(store_ids))
            query = f"""
                SELECT s.name, s.location,
                       COUNT(j.id) as total_jobs,
                       SUM(CASE WHEN j.status = 'Completed' THEN 1 ELSE 0 END) as completed_jobs,
                       COALESCE(SUM(CASE WHEN j.status = 'Completed' THEN j.actual_cost ELSE 0 END), 0) as revenue
                FROM stores s
                LEFT JOIN jobs j ON s.id = j.store_id
                WHERE s.id IN ({placeholders})
                GROUP BY s.id, s.name, s.location
                ORDER BY revenue DESC
            """
            store_performance = pd.read_sql(query, conn, params=store_ids)
            if not store_performance.empty:
                st.dataframe(store_performance, use_container_width=True)
            else:
                st.info("No store performance data available.")
        else:
            st.warning("No store access assigned to this admin.")

    conn.close()