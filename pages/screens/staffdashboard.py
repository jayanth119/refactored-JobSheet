import sys
import os
import pandas as pd
import streamlit as st
import plotly.express as px

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager


def staff_dashboard():
    user = st.session_state.user

    # Header
    st.markdown(f'''
        <div class="main-header">
            <h1>🏠 Dashboard</h1>
            <p>Welcome back, {user['full_name']} | {user['store_name']}</p>
        </div>
    ''', unsafe_allow_html=True)

    # Database
    db = DatabaseManager()
    conn = db.get_connection()

    # === Metrics ===
    col1, col2, col3, col4 = st.columns(4)

    total_jobs = pd.read_sql(
        "SELECT COUNT(*) as count FROM jobs WHERE store_id = ?", conn, params=[user['store_id']]
    ).iloc[0]['count']

    ongoing_jobs = pd.read_sql(
        "SELECT COUNT(*) as count FROM jobs WHERE status = 'In Progress' AND store_id = ?", conn, params=[user['store_id']]
    ).iloc[0]['count']

    completed_today = pd.read_sql(
        "SELECT COUNT(*) as count FROM jobs WHERE status = 'Completed' AND DATE(completed_at) = DATE('now') AND store_id = ?",
        conn, params=[user['store_id']]
    ).iloc[0]['count']

    total_revenue = pd.read_sql(
        "SELECT COALESCE(SUM(actual_cost), 0) as revenue FROM jobs WHERE status = 'Completed' AND store_id = ?",
        conn, params=[user['store_id']]
    ).iloc[0]['revenue']

    with col1:
        st.markdown(f'''
            <div class="metric-card">
                <div class="metric-number">{total_jobs}</div>
                <div class="metric-label">Total Jobs</div>
            </div>
        ''', unsafe_allow_html=True)

    with col2:
        st.markdown(f'''
            <div class="metric-card">
                <div class="metric-number">{ongoing_jobs}</div>
                <div class="metric-label">Ongoing Jobs</div>
            </div>
        ''', unsafe_allow_html=True)

    with col3:
        st.markdown(f'''
            <div class="metric-card">
                <div class="metric-number">{completed_today}</div>
                <div class="metric-label">Completed Today</div>
            </div>
        ''', unsafe_allow_html=True)

    with col4:
        st.markdown(f'''
            <div class="metric-card">
                <div class="metric-number">${total_revenue:.0f}</div>
                <div class="metric-label">Store Revenue</div>
            </div>
        ''', unsafe_allow_html=True)
    st.markdown("---")
    conn.close()