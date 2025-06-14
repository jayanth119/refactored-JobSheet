import sys 
import os 
import pandas as pd 
import streamlit as st
import plotly.express as px
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.css.css import Style
from components.datamanager.databasemanger import DatabaseManager
from components.utils.auth import hash_password , verify_password,authenticate_user , create_user
from pages.screens.loginpage import login_signup_page
from pages.screens.admindashboard import admin_dashboard
from components.sidebarnavigation import sidebar_navigation
def staff_dashboard():
    user = st.session_state.user
    
    # Header
    st.markdown(f'''
        <div class="main-header">
            <h1>🏠 Dashboard</h1>
            <p>Welcome back, {user['full_name']} | {user['store_name']}</p>
        </div>
    ''', unsafe_allow_html=True)
    
    # Get data from database for specific store
    db = DatabaseManager()
    conn = db.get_connection()
    
    # Metrics for current store only
    col1, col2, col3, col4 = st.columns(4)
    total_jobs = pd.read_sql("SELECT COUNT(*) as count FROM jobs WHERE store_id = ?", conn, params=[user['store_id']]).iloc[0]['count']
    ongoing_jobs = pd.read_sql("SELECT COUNT(*) as count FROM jobs WHERE status = 'In Progress' AND store_id = ?", conn, params=[user['store_id']]).iloc[0]['count']
    completed_today = pd.read_sql("SELECT COUNT(*) as count FROM jobs WHERE status = 'Completed' AND DATE(completed_at) = DATE('now') AND store_id = ?", conn, params=[user['store_id']]).iloc[0]['count']
    total_revenue = pd.read_sql("SELECT COALESCE(SUM(actual_cost), 0) as revenue FROM jobs WHERE status = 'Completed' AND store_id = ?", conn, params=[user['store_id']]).iloc[0]['revenue']
    
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
    
    # Current Store Performance
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"### 📊 {user['store_name']} - Performance Overview")
        
        # Jobs by status for current store
        status_data = pd.read_sql("""
            SELECT status, COUNT(*) as count
            FROM jobs 
            WHERE store_id = ?
            GROUP BY status
            ORDER BY count DESC
        """, conn, params=[user['store_id']])
        
        if not status_data.empty:
            fig = px.bar(status_data, x='status', y='count', 
                        title=f"Jobs by Status - {user['store_name']}",
                        color='status',
                        color_discrete_map={
                            'New': '#ffc107',
                            'In Progress': '#17a2b8', 
                            'Completed': '#28a745',
                            'Pending': '#dc3545'
                        })
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No job data available for your store")
    
    with col2:
        st.markdown("### 📈 Monthly Revenue Trend")
        
        monthly_revenue = pd.read_sql("""
            SELECT strftime('%Y-%m', completed_at) as month,
                   SUM(actual_cost) as revenue
            FROM jobs 
            WHERE status = 'Completed' AND store_id = ? AND completed_at IS NOT NULL
            GROUP BY strftime('%Y-%m', completed_at)
            ORDER BY month DESC
            LIMIT 6
        """, conn, params=[user['store_id']])
        
        if not monthly_revenue.empty:
            fig = px.line(monthly_revenue, x='month', y='revenue',
                         title="Revenue Trend",
                         markers=True)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No revenue data available")
    
    # Recent Jobs for Current Store
    st.markdown(f"### 📋 Recent Jobs - {user['store_name']}")
    
    recent_jobs = pd.read_sql("""
        SELECT id, customer_name, device_type, device_model, 
               problem_description, status, technician, created_at
        FROM jobs 
        WHERE store_id = ?
        ORDER BY created_at DESC 
        LIMIT 8
    """, conn, params=[user['store_id']])
    
    if not recent_jobs.empty:
        for _, job in recent_jobs.iterrows():
            status_class = f"status-{job['status'].lower().replace(' ', '-').replace('_', '-')}"
            technician_info = f"👨‍🔧 {job['technician']}" if job['technician'] else "👤 Unassigned"
            st.markdown(f'''
                <div class="job-card">
                    <div class="job-title">#{job['id']} - {job['customer_name']}</div>
                    <div class="job-details">{job['device_type']} - {job['device_model']}</div>
                    <div class="job-details">{job['problem_description']}</div>
                    <div class="job-details">{technician_info} | 📅 {job['created_at'][:10]}</div>
                    <span class="{status_class}">{job['status']}</span>
                </div>
            ''', unsafe_allow_html=True)
    else:
        st.info("No recent jobs found for your store")
    
    conn.close()