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
                   u.last_login, s.name as store_name, u.store_id
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
                        pass 
                        # if st.button(f"✏️ Edit", key=f"edit_user_{user_data['id']}"):
                        #     st.session_state[f"edit_user_{user_data['id']}"] = True
                    with col2:
                        if st.button(f"🔄 Reset Password", key=f"reset_{user_data['id']}"):
                            st.session_state[f"reset_pw_{user_data['id']}"] = True
                    with col3:
                        if user_data['username'] != 'admin':  # Prevent deleting admin
                            if st.button(f"🗑️ Delete", key=f"delete_user_{user_data['id']}"):
                                if st.session_state.get(f"confirm_delete_user_{user_data['id']}", False):
                                    delete_user(conn, user_data['id'])
                                    st.success(f"User {user_data['username']} deleted successfully!")
                                    st.rerun()
                                else:
                                    st.session_state[f"confirm_delete_user_{user_data['id']}"] = True
                                    st.warning("Click delete again to confirm")
                    
                    # Edit User Form
                    if st.session_state.get(f"edit_user_{user_data['id']}", False):
                        st.markdown("---")
                        st.markdown("### Edit User")
                        edit_user_form(conn, user_data, user['role'])
                    
                    # Reset Password Form
                    if st.session_state.get(f"reset_pw_{user_data['id']}", False):
                        st.markdown("---")
                        st.markdown("### Reset Password")
                        reset_password_form(conn, user_data)
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
                if(user['role'] == 'admin'):
                    roles = ["staff", "admin", "manager", "technician"]
                elif (user['role'] == 'manager'):
                    roles = ["staff", "technician"]
                
                new_role = st.selectbox("Role*", roles)
                
                # Get stores for assignment
                stores = pd.read_sql("SELECT id, name FROM stores", conn)
                store_options = {row['name']: row['id'] for _, row in stores.iterrows()}
                
                selected_store = None
                new_store_id = None
                
                if new_role in ["staff", "technician"]:
                    selected_store = st.selectbox("Assign to Store*", list(store_options.keys()))
                    new_store_id = store_options[selected_store]
                elif new_role == "manager":
                    selected_store = st.selectbox("Primary Store (Optional)", ["None"] + list(store_options.keys()))
                    if selected_store != "None":
                        new_store_id = store_options[selected_store]
            
            submit_user = st.form_submit_button("👤 Create User", use_container_width=True)
            
            if submit_user:
                if new_username and new_password and new_full_name and new_email:
                    if len(new_password) < 6:
                        st.error("⚠️ Password must be at least 6 characters long")
                    else:
                        success = create_new_user(conn, new_username, new_password, new_role, 
                                                new_store_id, new_full_name, new_email)
                        if success:
                            st.success(f"✅ User '{new_username}' created successfully!")
                            st.rerun()
                else:
                    st.error("⚠️ Please fill in all required fields")
    
    conn.close()

def create_new_user(conn, username, password, role, store_id, full_name, email):
    """Create a new user with proper table relationships"""
    try:
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # Insert user
        cursor.execute("""
            INSERT INTO users (username, password, role, store_id, full_name, email)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, hash_password(password), role, store_id, full_name, email))
        
        user_id = cursor.lastrowid
        
        # Handle store relationships based on role
        if role == "staff" and store_id:
            # Add to user_stores table for staff
            cursor.execute("""
                INSERT INTO user_stores (user_id, store_id, is_primary)
                VALUES (?, ?, 1)
            """, (user_id, store_id))
            
        elif role == "technician" and store_id:
            # Add to user_stores table
            cursor.execute("""
                INSERT INTO user_stores (user_id, store_id, is_primary)
                VALUES (?, ?, 1)
            """, (user_id, store_id))
            
            # Add to store_technicians table
            cursor.execute("""
                INSERT INTO store_technicians (store_id, technician_id, is_active)
                VALUES (?, ?, 1)
            """, (store_id, user_id))
            
        elif role == "manager" and store_id:
            # Add to user_stores table for manager
            cursor.execute("""
                INSERT INTO user_stores (user_id, store_id, is_primary)
                VALUES (?, ?, 1)
            """, (user_id, store_id))
        
        # Commit transaction
        cursor.execute("COMMIT")
        return True
        
    except sqlite3.IntegrityError as e:
        cursor.execute("ROLLBACK")
        if "username" in str(e).lower():
            st.error("❌ Username already exists. Please choose a different username.")
        else:
            st.error(f"❌ Database constraint error: {str(e)}")
        return False
    except Exception as e:
        cursor.execute("ROLLBACK")
        st.error(f"❌ Error creating user: {str(e)}")
        return False

def edit_user_form(conn, user_data, current_user_role):
    """Form to edit user details"""
    with st.form(f"edit_form_{user_data['id']}"):
        col1, col2 = st.columns(2)
        
        with col1:
            edit_username = st.text_input("Username", value=user_data['username'])
            edit_full_name = st.text_input("Full Name", value=user_data['full_name'] or '')
            edit_email = st.text_input("Email", value=user_data['email'] or '')
        
        with col2:
            # Role selection based on current user's role
            if current_user_role == 'admin':
                roles = ["staff", "admin", "manager", "technician"]
            elif current_user_role == 'manager':
                roles = ["staff", "technician"]
            
            current_role_index = roles.index(user_data['role']) if user_data['role'] in roles else 0
            edit_role = st.selectbox("Role", roles, index=current_role_index)
            
            # Store selection
            stores = pd.read_sql("SELECT id, name FROM stores", conn)
            store_options = {row['name']: row['id'] for _, row in stores.iterrows()}
            
            if edit_role in ["staff", "technician", "manager"]:
                store_names = list(store_options.keys())
                current_store_index = 0
                
                if user_data['store_id']:
                    current_store_name = pd.read_sql(
                        "SELECT name FROM stores WHERE id = ?", 
                        conn, params=[user_data['store_id']]
                    )
                    if not current_store_name.empty:
                        try:
                            current_store_index = store_names.index(current_store_name.iloc[0]['name'])
                        except ValueError:
                            current_store_index = 0
                
                edit_store = st.selectbox("Store", store_names, index=current_store_index)
                edit_store_id = store_options[edit_store]
            else:
                edit_store_id = None
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Save Changes", use_container_width=True):
                update_user(conn, user_data['id'], edit_username, edit_full_name, 
                           edit_email, edit_role, edit_store_id, user_data['role'])
        with col2:
            if st.form_submit_button("❌ Cancel", use_container_width=True):
                st.session_state[f"edit_user_{user_data['id']}"] = False
                st.rerun()

def update_user(conn, user_id, username, full_name, email, role, store_id, old_role):
    """Update user with proper relationship handling"""
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        
        # Update user table
        cursor.execute("""
            UPDATE users 
            SET username = ?, full_name = ?, email = ?, role = ?, store_id = ?
            WHERE id = ?
        """, (username, full_name, email, role, store_id, user_id))
        
        # Clean up existing relationships
        cursor.execute("DELETE FROM user_stores WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM store_technicians WHERE technician_id = ?", (user_id,))
        
        # Add new relationships based on role
        if role == "staff" and store_id:
            cursor.execute("""
                INSERT INTO user_stores (user_id, store_id, is_primary)
                VALUES (?, ?, 1)
            """, (user_id, store_id))
            
        elif role == "technician" and store_id:
            cursor.execute("""
                INSERT INTO user_stores (user_id, store_id, is_primary)
                VALUES (?, ?, 1)
            """, (user_id, store_id))
            
            cursor.execute("""
                INSERT INTO store_technicians (store_id, technician_id, is_active)
                VALUES (?, ?, 1)
            """, (store_id, user_id))
            
        elif role == "manager" and store_id:
            cursor.execute("""
                INSERT INTO user_stores (user_id, store_id, is_primary)
                VALUES (?, ?, 1)
            """, (user_id, store_id))
        
        cursor.execute("COMMIT")
        st.success("✅ User updated successfully!")
        st.session_state[f"edit_user_{user_id}"] = False
        st.rerun()
        
    except sqlite3.IntegrityError as e:
        cursor.execute("ROLLBACK")
        if "username" in str(e).lower():
            st.error("❌ Username already exists. Please choose a different username.")
        else:
            st.error(f"❌ Database constraint error: {str(e)}")
    except Exception as e:
        cursor.execute("ROLLBACK")
        st.error(f"❌ Error updating user: {str(e)}")

def reset_password_form(conn, user_data):
    """Form to reset user password"""
    with st.form(f"reset_form_{user_data['id']}"):
        new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm new password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("🔄 Reset Password", use_container_width=True):
                if new_password and confirm_password:
                    if len(new_password) < 6:
                        st.error("⚠️ Password must be at least 6 characters long")
                    elif new_password != confirm_password:
                        st.error("⚠️ Passwords do not match")
                    else:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE users SET password = ? WHERE id = ?
                            """, (hash_password(new_password), user_data['id']))
                            conn.commit()
                            st.success("✅ Password reset successfully!")
                            st.session_state[f"reset_pw_{user_data['id']}"] = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error resetting password: {str(e)}")
                else:
                    st.error("⚠️ Please fill in both password fields")
        
        with col2:
            if st.form_submit_button("❌ Cancel", use_container_width=True):
                st.session_state[f"reset_pw_{user_data['id']}"] = False
                st.rerun()

def delete_user(conn, user_id):
    """Delete user and clean up relationships"""
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        
        # Delete related records first
        cursor.execute("DELETE FROM user_stores WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM store_technicians WHERE technician_id = ?", (user_id,))
        cursor.execute("DELETE FROM technician_assignments WHERE technician_id = ?", (user_id,))
        
        # Delete user
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        cursor.execute("COMMIT")
        
    except Exception as e:
        cursor.execute("ROLLBACK")
        st.error(f"❌ Error deleting user: {str(e)}")