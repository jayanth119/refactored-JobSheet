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
from components.datamanager.databasemanger import DatabaseManager
from components.utils.auth import hash_password , verify_password,authenticate_user , create_user
def user_management():
    """Only accessible by admin users"""
    user = st.session_state.user
    
    if user['role'] != 'admin':
        st.error("❌ Access Denied: Admin privileges required")
        return
    
    st.markdown('''
        <div class="main-header">
            <h1>👤 User Management</h1>
            <p>Manage system users and their permissions</p>
        </div>
    ''', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["👥 View Users", "➕ Add User"])
    
    db = DatabaseManager()
    conn = db.get_connection()
    
    with tab1:
        st.markdown("### System Users")
        
        users_query = """
            SELECT u.id, u.username, u.role, u.full_name, u.email, 
                   u.last_login, s.name as store_name
            FROM users u
            LEFT JOIN stores s ON u.store_id = s.id
            ORDER BY u.role, u.full_name
        """
        
        users_df = pd.read_sql(users_query, conn)
        
        if not users_df.empty:
            for _, user_data in users_df.iterrows():
                with st.expander(f"👤 {user_data['full_name']} ({user_data['role']})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Username:** {user_data['username']}")
                        st.write(f"**Email:** {user_data['email']}")
                        st.write(f"**Store:** {user_data['store_name'] or 'N/A'}")
                    
                    with col2:
                        st.write(f"**Role:** {user_data['role']}")
                        last_login = user_data['last_login'][:19] if user_data['last_login'] else 'Never'
                        st.write(f"**Last Login:** {last_login}")
                    
                    # User actions
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button(f"✏️ Edit", key=f"edit_user_{user_data['id']}"):
                            st.session_state[f"edit_user_{user_data['id']}"] = True
                    with col2:
                        if st.button(f"🔄 Reset Password", key=f"reset_{user_data['id']}"):
                            st.session_state[f"reset_pw_{user_data['id']}"] = True
                    with col3:
                        if user_data['username'] != 'admin':  # Prevent deleting admin
                            if st.button(f"🗑️ Delete", key=f"delete_user_{user_data['id']}"):
                                if st.session_state.get(f"confirm_delete_user_{user_data['id']}", False):
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM users WHERE id = ?", (user_data['id'],))
                                    conn.commit()
                                    st.success(f"User {user_data['username']} deleted successfully!")
                                    st.rerun()
                                else:
                                    st.session_state[f"confirm_delete_user_{user_data['id']}"] = True
                                    st.warning("Click delete again to confirm")
        else:
            st.info("No users found")
    
    with tab2:
        st.markdown("### Add New User")
        
        with st.form("new_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Username*", placeholder="Enter unique username")
                new_full_name = st.text_input("Full Name*", placeholder="Enter user's full name")
                new_email = st.text_input("Email*", placeholder="Enter user's email")
            
            with col2:
                new_password = st.text_input("Password*", type="password", placeholder="Set a password")
                new_role = st.selectbox("Role*", ["staff", "admin"])
                
                # Get stores for staff assignment
                stores = pd.read_sql("SELECT id, name FROM stores", conn)
                store_options = dict(zip(stores['name'], stores['id']))
                
                if new_role == "staff":
                    selected_store = st.selectbox("Assign to Store*", list(store_options.keys()))
                    new_store_id = store_options[selected_store]
                else:
                    new_store_id = None
            
            submit_user = st.form_submit_button("👤 Create User", use_container_width=True)
            
            if submit_user:
                if new_username and new_password and new_full_name and new_email:
                    if len(new_password) < 6:
                        st.error("⚠️ Password must be at least 6 characters long")
                    else:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO users (username, password, role, store_id, full_name, email)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (new_username, hash_password(new_password), new_role, new_store_id, new_full_name, new_email))
                            
                            user_id = cursor.lastrowid
                            conn.commit()
                            
                            st.success(f"✅ User '{new_username}' created successfully!")
                            
                        except sqlite3.IntegrityError:
                            st.error("❌ Username already exists. Please choose a different username.")
                        except Exception as e:
                            st.error(f"❌ Error creating user: {str(e)}")
                else:
                    st.error("⚠️ Please fill in all required fields")
    
    conn.close()
