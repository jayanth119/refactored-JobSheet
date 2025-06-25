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

    # === Get Store IDs for current user ===
    if user['role'] == 'admin':
        store_ids_df = pd.read_sql(
            "SELECT store_id FROM user_stores WHERE user_id = ?", conn, params=[user['id']]
        )
        store_ids = store_ids_df['store_id'].tolist()
    else:
        store_ids = [user['store_id']]

    # === Dashboard Metrics ===
    def count_query(base_condition, extra_where=""):
        query = f"SELECT COUNT(*) as count FROM jobs"
        params = []
        where_clauses = []

        if store_ids:
            where_clauses.append(f"store_id IN ({','.join(['?']*len(store_ids))})")
            params.extend(store_ids)

        if extra_where:
            where_clauses.append(extra_where)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        return pd.read_sql(query, conn, params=params).iloc[0]['count']

    total_jobs = count_query("all")
    ongoing_jobs = count_query("status = 'In Progress'")
    completed_today = count_query("status = 'Completed'", "DATE(completed_at) = DATE('now')")
    completed_jobs = count_query("status = 'Completed'")

    # === Display Metrics ===
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'''<div class="metric-card"><div class="metric-number">{total_jobs}</div><div class="metric-label">Total Jobs</div></div>''', unsafe_allow_html=True)
    with col2:
        st.markdown(f'''<div class="metric-card"><div class="metric-number">{ongoing_jobs}</div><div class="metric-label">Ongoing Jobs</div></div>''', unsafe_allow_html=True)
    with col3:
        st.markdown(f'''<div class="metric-card"><div class="metric-number">{completed_today}</div><div class="metric-label">Completed Today</div></div>''', unsafe_allow_html=True)
    with col4:
        st.markdown(f'''<div class="metric-card"><div class="metric-number">{completed_jobs}</div><div class="metric-label">Completed Jobs</div></div>''', unsafe_allow_html=True)

    st.markdown("---")

    # === Search ===
    st.markdown("### 🔍 Search Jobs")
    search_term = st.text_input("Search by customer name, phone number, or email", label_visibility="visible")

    if search_term:
        search_query = """
            SELECT 
                j.id, 
                c.name AS customer_name, 
                c.email AS customer_email,
                c.phone AS customer_phone,
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
                c.email LIKE ? OR 
                c.phone LIKE ?
            )
        """
        params = [f"%{search_term}%"] * 3

        if store_ids:
            placeholders = ",".join(["?"] * len(store_ids))
            search_query += f" AND j.store_id IN ({placeholders})"
            params.extend(store_ids)

        search_query += " ORDER BY j.created_at DESC LIMIT 20"
        search_results = pd.read_sql(search_query, conn, params=params)

        if not search_results.empty:
            st.success(f"Found {len(search_results)} matching job(s):")
            for _, job in search_results.iterrows():
                st.markdown(f'''
                    <div class="job-card">
                        <div class="job-title">#{job['id']} - {job['customer_name']} {f"| 🏪 {job['store_name']}" if user['role'] == 'admin' else ""}</div>
                        <div class="job-details">📱 {job['device_type']} - {job['device_model']}</div>
                        <div class="job-details">📝 {job['problem_description']}</div>
                        <div class="job-details">📧 {job['customer_email']} | 📞 {job['customer_phone']}</div>
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

        assigned_stores = pd.read_sql("""
            SELECT s.id, s.name, s.location
            FROM user_stores us
            JOIN stores s ON us.store_id = s.id
            WHERE us.user_id = ?
        """, conn, params=[user["id"]])

        if not assigned_stores.empty:
            store_ids = assigned_stores["id"].tolist()
            placeholders = ",".join(["?"] * len(store_ids))

            performance_query = f"""
                SELECT 
                    s.name, 
                    s.location,
                    COUNT(j.id) AS total_jobs,
                    SUM(CASE WHEN j.status = 'Completed' THEN 1 ELSE 0 END) AS completed_jobs,
                    COALESCE(SUM(CASE WHEN j.status = 'Completed' THEN j.actual_cost ELSE 0 END), 0) AS revenue
                FROM stores s
                LEFT JOIN jobs j ON s.id = j.store_id
                WHERE s.id IN ({placeholders})
                GROUP BY s.id, s.name, s.location
                ORDER BY revenue DESC
            """

            store_performance = pd.read_sql(performance_query, conn, params=store_ids)

            if not store_performance.empty:
                st.dataframe(store_performance, use_container_width=True)
            else:
                st.info("No performance data found for your stores.")
        else:
            st.warning("🚫 No stores are assigned to you.")

    conn.close()
