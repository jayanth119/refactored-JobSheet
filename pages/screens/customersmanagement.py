import pandas as pd
import sys
import os
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager
from components.jobdetailmodal import show_job_details_modal


def customers_management():
    user = st.session_state.user

    st.markdown(f'''
        <div class="main-header">
            <h1>👥 Customer Management</h1>
            <p>Manage customers for {user['store_name'] if user['role'] == 'staff' else 'all stores'}</p>
        </div>
    ''', unsafe_allow_html=True)

    tabs = st.tabs(["👥 View Customers"])
    db = DatabaseManager()
    conn = db.get_connection()

    with tabs[0]:
        st.markdown("### Customer Directory")

        search_term = st.text_input("🔍 Search by Customer Name", "")

        if user['role'] == 'admin':
            query = f"""
                SELECT c.id, c.name, c.phone, c.email, c.address, 
                       c.created_at, s.name as store_name,
                       COUNT(j.id) as total_jobs
                FROM customers c
                LEFT JOIN stores s ON c.store_id = s.id
                LEFT JOIN jobs j ON c.id = j.customer_id
                {"WHERE c.name LIKE ?" if search_term else ""}
                GROUP BY c.id, c.name, c.phone, c.email, c.address, c.created_at, s.name
                ORDER BY c.created_at DESC
            """
            params = [f"%{search_term}%"] if search_term else []
        else:
            query = f"""
                SELECT c.id, c.name, c.phone, c.email, c.address, 
                       c.created_at, COUNT(j.id) as total_jobs
                FROM customers c
                LEFT JOIN jobs j ON c.id = j.customer_id
                WHERE c.store_id = ?
                {"AND c.name LIKE ?" if search_term else ""}
                GROUP BY c.id, c.name, c.phone, c.email, c.address, c.created_at
                ORDER BY c.created_at DESC
            """
            params = [user['store_id']]
            if search_term:
                params.append(f"%{search_term}%")

        customers_df = pd.read_sql(query, conn, params=params)

        if not customers_df.empty:
            st.write(f"**Total Customers:** {len(customers_df)}")

            for _, customer in customers_df.iterrows():
                with st.expander(f"👤 {customer['name']} | 📞 {customer['phone']} | Jobs: {customer['total_jobs']}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Name:** {customer['name']}")
                        st.write(f"**Phone:** {customer['phone']}")
                        st.write(f"**Email:** {customer['email'] or 'Not provided'}")
                        st.write(f"**Address:** {customer['address'] or 'Not provided'}")

                    with col2:
                        st.write(f"**Customer Since:** {customer['created_at'][:10]}")
                        st.write(f"**Total Jobs:** {customer['total_jobs']}")
                        if user['role'] == 'admin':
                            st.write(f"**Store:** {customer['store_name']}")

                    if customer['total_jobs'] > 0:
                        st.markdown("**📝 Recent Jobs:**")

                        job_history = pd.read_sql("""
                            SELECT id, device_type, device_model, status, created_at
                            FROM jobs 
                            WHERE customer_id = ?
                            ORDER BY created_at DESC
                            LIMIT 5
                        """, conn, params=[customer['id']])

                        for _, job in job_history.iterrows():
                            job_id = job['id']
                            status_class = f"status-{job['status'].lower().replace(' ', '-')}"
                            st.markdown(f'''
                                <div style="background: black; padding: 0.5rem; border-radius: 5px; margin: 0.2rem 0;">
                                    <small>#{job_id} - {job['device_type']} {job['device_model']} | {job['created_at'][:10]} | 
                                    <span class="{status_class}">{job['status']}</span></small>
                                </div>
                            ''', unsafe_allow_html=True)

                            if st.button(f"View Details #{job_id}", key=f"view_{job_id}"):
                                st.session_state[f"show_details_{job_id}"] = True

                            if st.session_state.get(f"show_details_{job_id}", False):
                                show_job_details_modal(conn, job_id, editable=False)

        else:
            st.info("No customers found for your store.")

    conn.close()
