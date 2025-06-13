
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
import streamlit as st
def customers_management():
    user = st.session_state.user
    
    st.markdown(f'''
        <div class="main-header">
            <h1>👥 Customer Management</h1>
            <p>Manage customers for {user['store_name'] if user['role'] == 'staff' else 'all stores'}</p>
        </div>
    ''', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["➕ Add Customer", "👥 View Customers", "🔍 Search Customers"])
    
    db = DatabaseManager()
    conn = db.get_connection()
    
    with tab1:
        st.markdown("### Add New Customer")
        with st.form("new_customer_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Customer Name*", placeholder="Enter full name")
                phone = st.text_input("Phone Number*", placeholder="Enter phone number")
            
            with col2:
                email = st.text_input("Email", placeholder="Enter email address")
                address = st.text_area("Address", placeholder="Enter customer address", height=100)
            
            submit_customer = st.form_submit_button("👤 Add Customer", use_container_width=True)
            
            if submit_customer:
                if name and phone:
                    try:
                        store_id = user['store_id'] if user['role'] == 'staff' else 1
                        
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO customers (name, phone, email, address, store_id)
                            VALUES (?, ?, ?, ?, ?)
                        """, (name, phone, email, address, store_id))
                        
                        customer_id = cursor.lastrowid
                        conn.commit()
                        
                        st.success(f"✅ Customer '{name}' added successfully! (ID: {customer_id})")
                        
                    except Exception as e:
                        st.error(f"❌ Error adding customer: {str(e)}")
                else:
                    st.error("⚠️ Please fill in required fields (Name and Phone)")
    
    with tab2:
        st.markdown("### Customer Directory")
        
        # Build query based on user role
        if user['role'] == 'admin':
            customers_query = """
                SELECT c.id, c.name, c.phone, c.email, c.address, 
                       c.created_at, s.name as store_name,
                       COUNT(j.id) as total_jobs
                FROM customers c
                LEFT JOIN stores s ON c.store_id = s.id
                LEFT JOIN jobs j ON c.id = j.customer_id
                GROUP BY c.id, c.name, c.phone, c.email, c.address, c.created_at, s.name
                ORDER BY c.created_at DESC
            """
            customers_df = pd.read_sql(customers_query, conn)
        else:
            customers_query = """
                SELECT c.id, c.name, c.phone, c.email, c.address, 
                       c.created_at, COUNT(j.id) as total_jobs
                FROM customers c
                LEFT JOIN jobs j ON c.id = j.customer_id
                WHERE c.store_id = ?
                GROUP BY c.id, c.name, c.phone, c.email, c.address, c.created_at
                ORDER BY c.created_at DESC
            """
            customers_df = pd.read_sql(customers_query, conn, params=[user['store_id']])
        
        if not customers_df.empty:
            st.write(f"**Total Customers:** {len(customers_df)}")
            
            # Display customers in expandable cards
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
                    
                    # Customer's job history
                    if customer['total_jobs'] > 0:
                        st.markdown("**Recent Jobs:**")
                        job_history = pd.read_sql("""
                            SELECT id, device_type, device_model, status, created_at
                            FROM jobs 
                            WHERE customer_id = ?
                            ORDER BY created_at DESC
                            LIMIT 5
                        """, conn, params=[customer['id']])
                        
                        for _, job in job_history.iterrows():
                            status_class = f"status-{job['status'].lower().replace(' ', '-')}"
                            st.markdown(f'''
                                <div style="background: #f8f9fa; padding: 0.5rem; border-radius: 5px; margin: 0.2rem 0;">
                                    <small>#{job['id']} - {job['device_type']} {job['device_model']} | {job['created_at'][:10]} | 
                                    <span class="{status_class}">{job['status']}</span></small>
                                </div>
                            ''', unsafe_allow_html=True)
        else:
            st.info("No customers found for your store")
    
    with tab3:
        st.markdown("### Search Customers")
        
        search_customer = st.text_input("🔍 Search by name, phone, or email")
        
        if search_customer:
            search_query = """
                SELECT c.id, c.name, c.phone, c.email, c.address, 
                       c.created_at, COUNT(j.id) as total_jobs
                FROM customers c
                LEFT JOIN jobs j ON c.id = j.customer_id
                WHERE (c.name LIKE ? OR c.phone LIKE ? OR c.email LIKE ?)
            """
            
            params = [f"%{search_customer}%"] * 3
            
            if user['role'] == 'staff':
                search_query += " AND c.store_id = ?"
                params.append(user['store_id'])
            
            search_query += """
                GROUP BY c.id, c.name, c.phone, c.email, c.address, c.created_at
                ORDER BY c.name ASC
                LIMIT 10
            """
            
            search_results = pd.read_sql(search_query, conn, params=params)
            
            if not search_results.empty:
                st.write(f"Found {len(search_results)} customers:")
                
                for _, customer in search_results.iterrows():
                    st.markdown(f'''
                        <div class="job-card">
                            <div class="job-title">👤 {customer['name']}</div>
                            <div class="job-details">📞 {customer['phone']} | ✉️ {customer['email'] or 'No email'}</div>
                            <div class="job-details">📍 {customer['address'] or 'No address'}</div>
                            <div class="job-details">📅 Customer since: {customer['created_at'][:10]} | 🔧 Total jobs: {customer['total_jobs']}</div>
                        </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info("No customers found matching your search")
    
    conn.close()