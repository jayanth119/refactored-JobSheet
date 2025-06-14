import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import hashlib
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import time
import sys
import os 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.css.css import Style
from components.datamanager.databasemanger import DatabaseManager
from components.utils.auth import hash_password , verify_password,authenticate_user , create_user
from pages.screens.loginpage import login_signup_page
def admin_dashboard(st):
    user = st.session_state.user
    
    # Header
    st.markdown(f'''
        <div class="main-header">
            <h1>🏠 Admin Dashboard</h1>
            <p>Welcome back, {user['full_name']} | Managing All Stores</p>
        </div>
    ''', unsafe_allow_html=True)
    
    # Get data from database
    db = DatabaseManager()
    conn = db.get_connection()
    
    # Metrics for all stores
    col1, col2, col3, col4 = st.columns(4)
    
    total_jobs = pd.read_sql("SELECT COUNT(*) as count FROM jobs", conn).iloc[0]['count']
    ongoing_jobs = pd.read_sql("SELECT COUNT(*) as count FROM jobs WHERE status = 'In Progress'", conn).iloc[0]['count']
    completed_today = pd.read_sql("SELECT COUNT(*) as count FROM jobs WHERE status = 'Completed' AND DATE(completed_at) = DATE('now')", conn).iloc[0]['count']
    total_revenue = pd.read_sql("SELECT COALESCE(SUM(actual_cost), 0) as revenue FROM jobs WHERE status = 'Completed'", conn).iloc[0]['revenue']
    
    with col1:
        st.markdown(f'''
            <div class="metric-card">
                <div class="metric-number">{total_jobs}</div>
                <div class="metric-label">Total Jobs (All Stores)</div>
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
                <div class="metric-label">Total Revenue</div>
            </div>
        ''', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Store Performance Overview
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🏪 Store Performance Overview")
        
        store_performance = pd.read_sql("""
            SELECT s.name, s.location,
                   COUNT(j.id) as total_jobs,
                   SUM(CASE WHEN j.status = 'Completed' THEN 1 ELSE 0 END) as completed_jobs,
                   COALESCE(SUM(CASE WHEN j.status = 'Completed' THEN j.actual_cost ELSE 0 END), 0) as revenue
            FROM stores s
            LEFT JOIN jobs j ON s.id = j.store_id
            GROUP BY s.id, s.name, s.location
            ORDER BY revenue DESC
        """, conn)
        
        if not store_performance.empty:
            st.dataframe(store_performance, use_container_width=True)
        else:
            st.info("No store performance data available")
    
    with col2:
        st.markdown("### 📊 Revenue by Store")
        
        if not store_performance.empty and store_performance['revenue'].sum() > 0:
            fig = px.pie(store_performance, values='revenue', names='name', 
                        title="Revenue Distribution",
                        color_discrete_sequence=['#667eea', '#764ba2', '#f093fb', '#f5576c'])
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No revenue data to display")
    
    # Recent Jobs Across All Stores
    st.markdown("### 📋 Recent Jobs (All Stores)")
    
    recent_jobs = pd.read_sql("""
        SELECT j.id, j.customer_name, j.device_type, j.device_model, 
               j.problem_description, j.status, j.created_at, s.name as store_name
        FROM jobs j
        LEFT JOIN stores s ON j.store_id = s.id
        ORDER BY j.created_at DESC 
        LIMIT 5
    """, conn)
    
    if not recent_jobs.empty:
        for _, job in recent_jobs.iterrows():
            status_class = f"status-{job['status'].lower().replace(' ', '-').replace('_', '-')}"
            st.markdown(f'''
                <div class="job-card">
                    <div class="job-title">#{job['id']} - {job['customer_name']} | {job['store_name'] or 'Unknown Store'}</div>
                    <div class="job-details">{job['device_type']} - {job['device_model']}</div>
                    <div class="job-details">{job['problem_description']}</div>
                    <span class="{status_class}">{job['status']}</span>
                </div>
            ''', unsafe_allow_html=True)
    else:
        st.info("No recent jobs found")
    
    conn.close()