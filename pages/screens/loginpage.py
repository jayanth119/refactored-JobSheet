import sys
import os 
import json 
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.css.css import Style
from components.datamanager.databasemanger import DatabaseManager
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
import streamlit as st
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager
from components.utils.auth import hash_password , verify_password,authenticate_user , create_user
def login_signup_page():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # Header
    st.markdown("""
        <div class="login-header">
            <h1>🔧 RepairPro</h1>
            <p>Professional Repair Shop Management System</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Login/Signup tabs
    tab1, tab2 = st.tabs(["🔐 Sign In", "📝 Sign Up"])
    
    with tab1:
        st.markdown("### Welcome Back")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit_button = st.form_submit_button("Sign In", use_container_width=True)
            
            if submit_button:
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.user = user
                        st.session_state.authenticated = True
                        st.session_state.login_time = time.time()

                        # Generate and store token
                        token = hashlib.sha256(f"{username}-{time.time()}".encode()).hexdigest()
                        st.query_params.update({"token": token})

                        # Save to file
                        if os.path.exists("tokens.json"):
                            with open("tokens.json", "r") as f:
                                token_map = json.load(f)
                        else:
                            token_map = {}

                        token_map[token] = user
                        with open("tokens.json", "w") as f:
                            json.dump(token_map, f)

                        st.success(f"Welcome back, {user['full_name']}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
       
        # Demo credentials
        st.markdown("---")
        st.info("""
        **Demo Credentials:**
        - **Admin:** admin / admin123
        - **Staff 1:** staff1 / staff123  
        - **Staff 2:** staff2 / staff123
        """)
    
    with tab2:
        st.markdown("### Create New Account")
        with st.form("signup_form"):
            # Get available stores for selection
            db = DatabaseManager()
            conn = db.get_connection()
            stores = pd.read_sql("SELECT id, name FROM stores", conn)
            conn.close()
            
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username*", placeholder="Choose a username")
                new_full_name = st.text_input("Full Name*", placeholder="Enter your full name")
                new_email = st.text_input("Email*", placeholder="Enter your email")
            
            with col2:
                new_password = st.text_input("Password*", type="password", placeholder="Choose a password")
                new_role = st.selectbox("Role*", ["staff", "admin"])
                if new_role == "staff":
                    store_options = dict(zip(stores['name'], stores['id']))
                    selected_store = st.selectbox("Assign to Store*", list(store_options.keys()))
                    new_store_id = store_options[selected_store]
                else:
                    new_store_id = None
            
            signup_button = st.form_submit_button("Create Account", use_container_width=True)
            
            if signup_button:
                if new_username and new_password and new_full_name and new_email:
                    if len(new_password) < 6:
                        st.error("⚠️ Password must be at least 6 characters long")
                    else:
                        success = create_user(new_username, new_password, new_role, new_store_id, new_full_name, new_email)
                        if success:
                            st.success("✅ Account created successfully! You can now sign in.")
                        else:
                            st.error("❌ Username already exists. Please choose a different username.")
                else:
                    st.error("⚠️ Please fill in all required fields")
    
    st.markdown("</div>", unsafe_allow_html=True)
