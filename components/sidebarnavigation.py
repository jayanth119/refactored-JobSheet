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
from components.utils.session import check_session_timeout
def sidebar_navigation():
    user = st.session_state.user
    
    # Header
    st.sidebar.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 10px; margin-bottom: 1rem;">
            <h2 style="color: white; margin: 0;">🔧 RepairPro</h2>
            <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 0.9rem;">{user['store_name']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # User info
    st.sidebar.markdown(f"""
        <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
            <div style="color: white; font-weight: 600;">{user['full_name']}</div>
            <div style="color: rgba(255,255,255,0.7); font-size: 0.8rem; text-transform: uppercase;">{user['role']}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Session info
    session_duration = check_session_timeout(st)
    remaining_time = 3600 - session_duration
    hours = int(remaining_time // 3600)
    minutes = int((remaining_time % 3600) // 60)
    
    st.sidebar.markdown(f"""
        <div class="session-info">
            ⏰ Session expires in: {hours:02d}:{minutes:02d}
        </div>
    """, unsafe_allow_html=True)
    
    # Quick stats
    db = DatabaseManager()
    conn = db.get_connection()
    
    if user['role'] == 'admin':
        total_jobs = pd.read_sql("SELECT COUNT(*) as count FROM jobs", conn).iloc[0]['count']
        ongoing_jobs = pd.read_sql("SELECT COUNT(*) as count FROM jobs WHERE status = 'In Progress'", conn).iloc[0]['count']
        total_stores = pd.read_sql("SELECT COUNT(*) as count FROM stores", conn).iloc[0]['count']
    else:
        total_jobs = pd.read_sql("SELECT COUNT(*) as count FROM jobs WHERE store_id = ?", conn, params=[user['store_id']]).iloc[0]['count']
        ongoing_jobs = pd.read_sql("SELECT COUNT(*) as count FROM jobs WHERE status = 'In Progress' AND store_id = ?", conn, params=[user['store_id']]).iloc[0]['count']
        total_stores = 1
    
    conn.close()
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("Jobs", total_jobs)
        st.metric("Ongoing", ongoing_jobs)
    with col2:
        if user['role'] == 'admin':
            st.metric("Stores", total_stores)
        st.metric("", "")
    
    st.sidebar.markdown("---")
    
    # Navigation menu
    if user['role'] == 'admin':
        menu_items = {
            "🏠 Dashboard": "dashboard",
            "📋 All Jobs": "jobs",
            "👥 All Customers": "customers",
            "🏪 Store Management": "stores",
            "📊 Reports": "reports",
            "👤 User Management": "users",
            "⚙️ Settings": "settings"
        }
    else:
        menu_items = {
            "🏠 Dashboard": "dashboard",
            "📋 Jobs": "jobs",
            "👥 Customers": "customers",
            "📊 Reports": "reports",
            "⚙️ Settings": "settings"
        }
    
    selected = st.sidebar.radio("Navigation", list(menu_items.keys()))
    
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
    
    return menu_items[selected]