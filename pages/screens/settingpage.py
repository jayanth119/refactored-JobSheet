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
def settings_page():
    user = st.session_state.user
    
    st.markdown(f'''
        <div class="main-header">
            <h1>⚙️ Settings</h1>
            <p>Manage your account and system preferences</p>
        </div>
    ''', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["👤 Account Settings", "🔒 Change Password"])
    
    db = DatabaseManager()
    conn = db.get_connection()
    
    with tab1:
        st.markdown("### Your Account Information")
        
        # Get current user data
        user_data = pd.read_sql("""
            SELECT u.username, u.full_name, u.email, u.last_login, s.name as store_name
            FROM users u
            LEFT JOIN stores s ON u.store_id = s.id
            WHERE u.id = ?
        """, conn, params=[user['id']]).iloc[0]
        
        with st.form("update_account_form"):
            new_full_name = st.text_input("Full Name", value=user_data['full_name'])
            new_email = st.text_input("Email", value=user_data['email'])
            
            update_button = st.form_submit_button("💾 Save Changes", use_container_width=True)
            
            if update_button:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE users 
                        SET full_name = ?, email = ?
                        WHERE id = ?
                    """, (new_full_name, new_email, user['id']))
                    conn.commit()
                    
                    # Update session state
                    st.session_state.user['full_name'] = new_full_name
                    st.session_state.user['email'] = new_email
                    
                    st.success("✅ Account information updated successfully!")
                except Exception as e:
                    st.error(f"❌ Error updating account: {str(e)}")
        
        st.markdown("---")
        st.markdown("**Account Details**")
        st.write(f"**Username:** {user_data['username']}")
        st.write(f"**Store:** {user_data['store_name']}")
        st.write(f"**Last Login:** {user_data['last_login'][:19] if user_data['last_login'] else 'Never'}")
    
    with tab2:
        st.markdown("### Change Password")
        
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            change_button = st.form_submit_button("🔒 Change Password", use_container_width=True)
            
            if change_button:
                if current_password and new_password and confirm_password:
                    # Verify current password
                    cursor = conn.cursor()
                    cursor.execute("SELECT password FROM users WHERE id = ?", (user['id'],))
                    stored_hash = cursor.fetchone()[0]
                    
                    if verify_password(current_password, stored_hash):
                        if new_password == confirm_password:
                            if len(new_password) >= 6:
                                try:
                                    new_hash = hash_password(new_password)
                                    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_hash, user['id']))
                                    conn.commit()
                                    st.success("✅ Password changed successfully!")
                                except Exception as e:
                                    st.error(f"❌ Error changing password: {str(e)}")
                            else:
                                st.error("⚠️ New password must be at least 6 characters long")
                        else:
                            st.error("⚠️ New passwords don't match")
                    else:
                        st.error("❌ Current password is incorrect")
                else:
                    st.error("⚠️ Please fill in all fields")
    
    conn.close()