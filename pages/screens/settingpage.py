import streamlit as st
import pandas as pd
import sys
import os 
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager
from components.utils.auth import hash_password, verify_password, create_user

def settings_page():
    user = st.session_state.user
    
    st.markdown(f'''
        <div class="main-header">
            <h1>⚙️ Settings</h1>
            <p>Manage your account and system preferences</p>
        </div>
    ''', unsafe_allow_html=True)
    
    # Create different tabs based on user role
    if user['role'] in ['admin', 'manager']:
        tabs = ["👤 Account Settings", "🔒 Change Password", "👥 User Management"]
        tab1, tab2, tab3 = st.tabs(tabs)
    else:
        tabs = ["👤 Account Settings", "🔒 Change Password"]
        tab1, tab2 = st.tabs(tabs)
    
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
        
        # Handle last_login display
        if user_data['last_login']:
            try:
                if isinstance(user_data['last_login'], str):
                    last_login = datetime.strptime(user_data['last_login'], '%Y-%m-%d %H:%M:%S')
                else:
                    last_login = user_data['last_login']
                st.write(f"**Last Login:** {last_login.strftime('%Y-%m-%d %H:%M')}")
            except:
                st.write(f"**Last Login:** {str(user_data['last_login'])[:19]}")
        else:
            st.write("**Last Login:** Never")
    
    with tab2:
        st.markdown("### Change Password")
        
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            change_button = st.form_submit_button("🔒 Change Password", use_container_width=True)
            
            if change_button:
                if not all([current_password, new_password, confirm_password]):
                    st.error("⚠️ Please fill in all fields")
                else:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("SELECT password FROM users WHERE id = ?", (user['id'],))
                        result = cursor.fetchone()
                        
                        if result and verify_password(current_password, result[0]):
                            if new_password == confirm_password:
                                if len(new_password) >= 6:
                                    new_hash = hash_password(new_password)
                                    cursor.execute("UPDATE users SET password = ? WHERE id = ?", 
                                                (new_hash, user['id']))
                                    conn.commit()
                                    st.success("✅ Password changed successfully!")
                                else:
                                    st.error("⚠️ New password must be at least 6 characters long")
                            else:
                                st.error("⚠️ New passwords don't match")
                        else:
                            st.error("❌ Current password is incorrect")
                    except Exception as e:
                        st.error(f"❌ Error changing password: {str(e)}")
    
    # User Management tab (only for admin and manager)
    if user['role'] in ['admin', 'manager']:
        with tab3:
            st.markdown("### 👥 User Management")
            
            # Different permissions for admin vs manager
            if user['role'] == 'admin':
                allowed_roles = ['admin', 'manager', 'staff', 'technician']
                stores = pd.read_sql("SELECT id, name FROM stores", conn)
            else:  # manager
                allowed_roles = ['staff', 'technician']
                stores = pd.read_sql("SELECT id, name FROM stores WHERE id = ?", 
                                   conn, params=[user['store_id']])
            
            # Create new user form
            with st.expander("➕ Create New User", expanded=False):
                with st.form("create_user_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        new_username = st.text_input("Username*")
                        new_full_name = st.text_input("Full Name*")
                        new_email = st.text_input("Email")
                    
                    with col2:
                        new_role = st.selectbox("Role*", allowed_roles)
                        new_password = st.text_input("Password*", type="password")
                        if user['role'] == 'admin':
                            new_store = st.selectbox("Store", stores['name'], index=0)
                        else:
                            new_store = stores.iloc[0]['name']
                    
                    create_button = st.form_submit_button("👤 Create User", use_container_width=True)
                    
                    if create_button:
                        if not all([new_username, new_full_name, new_password]):
                            st.error("⚠️ Please fill all required fields (*)")
                        else:
                            try:
                                store_id = stores[stores['name'] == new_store].iloc[0]['id']
                                create_user(
                                    conn=conn,
                                    username=new_username,
                                    password=new_password,
                                    role=new_role,
                                    full_name=new_full_name,
                                    email=new_email,
                                    store_id=store_id
                                )
                                st.success(f"✅ User {new_username} created successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error creating user: {str(e)}")
            
            st.markdown("---")
            st.markdown("### User List")
            
            # Get users based on role permissions
            if user['role'] == 'admin':
                users_query = """
                    SELECT u.id, u.username, u.full_name, u.role, u.email, 
                           s.name as store_name, u.last_login
                    FROM users u
                    LEFT JOIN stores s ON u.store_id = s.id
                    ORDER BY u.role, u.username
                """
                users_df = pd.read_sql(users_query, conn)
            else:  # manager
                users_query = """
                    SELECT u.id, u.username, u.full_name, u.role, u.email, 
                           s.name as store_name, u.last_login
                    FROM users u
                    LEFT JOIN stores s ON u.store_id = s.id
                    WHERE u.store_id = ? AND u.role IN ('staff', 'technician')
                    ORDER BY u.role, u.username
                """
                users_df = pd.read_sql(users_query, conn, params=[user['store_id']])
            
            if not users_df.empty:
                # Convert last_login to datetime if it's a string
                if users_df['last_login'].dtype == 'object':
                    users_df['last_login'] = pd.to_datetime(users_df['last_login'])
                
                # Create a copy without last_login for editing
                editable_columns = ['id', 'username', 'full_name', 'role', 'email', 'store_name']
                editable_df = users_df[editable_columns].copy()
                
                # Display users in an editable dataframe
                edited_df = st.data_editor(
                    editable_df,
                    column_config={
                        "id": None,
                        "role": st.column_config.SelectboxColumn(
                            "Role",
                            options=allowed_roles,
                            required=True
                        ),
                        "store_name": st.column_config.TextColumn(
                            "Store",
                            disabled=True
                        ),
                        "username": st.column_config.TextColumn(
                            "Username",
                            disabled=True
                        )
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                # Save changes button
                if st.button("💾 Save Changes", use_container_width=True):
                    try:
                        cursor = conn.cursor()
                        for _, row in edited_df.iterrows():
                            cursor.execute("""
                                UPDATE users
                                SET full_name = ?, email = ?, role = ?
                                WHERE id = ?
                            """, (row['full_name'], row['email'], row['role'], row['id']))
                        conn.commit()
                        st.success("✅ User information updated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error updating users: {str(e)}")
                
                # Delete user functionality (only for admin)
                if user['role'] == 'admin':
                    st.markdown("---")
                    st.markdown("### 🗑️ Delete User")
                    user_to_delete = st.selectbox(
                        "Select user to delete",
                        users_df['username'],
                        index=None,
                        placeholder="Select user..."
                    )
                    
                    if st.button("⚠️ Delete User", type="primary", use_container_width=True):
                        if not user_to_delete:
                            st.error("Please select a user to delete")
                        elif st.session_state.user['username'] == user_to_delete:
                            st.error("❌ You cannot delete your own account!")
                        else:
                            confirm = st.checkbox(f"I confirm I want to permanently delete {user_to_delete}")
                            if confirm:
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM users WHERE username = ?", (user_to_delete,))
                                    conn.commit()
                                    st.success(f"✅ User {user_to_delete} deleted successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error deleting user: {str(e)}")
            else:
                st.info("No users found matching your permissions.")
    
    conn.close()