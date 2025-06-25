import sys
import os 
import json 
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import hashlib
import time 
import streamlit as st
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager
from components.utils.auth import  authenticate_user, create_user
from components.jobstatusinfo import display_job_info

def fetch_job_details(job_id):
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT j.id, j.device_model, j.problem_description, j.actual_cost, j.status, 
                   c.name AS customer_name, c.phone AS customer_phone,
                   s.name AS store_name, s.phone AS store_phone
            FROM jobs j
            LEFT JOIN customers c ON j.customer_id = c.id
            LEFT JOIN stores s ON j.store_id = s.id
            WHERE j.id = ?
        ''', (job_id,))
        result = cursor.fetchone()

        return result

    except Exception as e:
        st.error("❌ Failed to retrieve job details.")
        print("Database error:", e)
        return None



def login_signup_page():

    
    # Header
    st.markdown("""
        <div class="login-header">
            <h1>🔧 RepairPro</h1>
            <p>Professional Repair Shop Management System</p>
        </div>
    """, unsafe_allow_html=True)
    hide_sidebar_style = """
    <style>
        /* Hide the sidebar completely */
        [data-testid="stSidebar"] {
            display: none !important;
        }

        /* Hide the sidebar toggle (arrow) */
        [data-testid="collapsedControl"] {
            display: none !important;
        }

        /* Hide Streamlit header and footer */
        header, footer, [data-testid="stHeader"] {
            visibility: hidden;
        }

        /* Prevent white space where sidebar was */
        .block-container {
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
    </style>
"""

    st.markdown(hide_sidebar_style, unsafe_allow_html=True)
    
    # Only show login tab initially
    tab1 , tab2 = st.tabs(["🔐 Sign In", "🔧Repair Status"])
    
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
                else:
                    st.error("⚠️ Please enter both username and password")
    with tab2 :
        st.markdown("### 📝 Enter Job ID to Track Repair")
        manual_job_id = st.text_input("Job ID", placeholder="Enter your Job ID")

        if st.button("🔍 Check Status"):
            if manual_job_id.isdigit():
                data = fetch_job_details(int(manual_job_id))
                if data:
                    display_job_info(data)
                else:
                    st.error("❌ No repair job found for the entered ID.")
            else:
                st.error("⚠️ Please enter a valid numeric Job ID.")
        
    
    # Only show signup option if admin is logged in
    if st.session_state.get('authenticated') and st.session_state.user.get('role') == 'admin':
        tab2 = st.tabs(["📝 Create New User"])[0]
        
        with tab2:
            st.markdown("### Create New User Account")
            with st.form("signup_form"):
                # Get available stores for selection
                db = DatabaseManager()
                conn = db.get_connection()
                stores = pd.read_sql("SELECT id, name FROM stores", conn)
                conn.close()
                
                col1, col2 = st.columns(2)
                with col1:
                    new_username = st.text_input("Username*", placeholder="Choose a username")
                    new_full_name = st.text_input("Full Name*", placeholder="Enter full name")
                    new_email = st.text_input("Email*", placeholder="Enter email")
                
                with col2:
                    new_password = st.text_input("Password*", type="password", placeholder="Set password")
                    new_role = st.selectbox("Role*", ["admin", "manager", "staff", "technician"])
                    store_options = dict(zip(stores['name'], stores['id']))
                    selected_store = st.selectbox("Assign to Store*", list(store_options.keys()))
                    new_store_id = store_options[selected_store]
                
                signup_button = st.form_submit_button("Create User Account", use_container_width=True)
                
                if signup_button:
                    if all([new_username, new_password, new_full_name, new_email]):
                        if len(new_password) < 6:
                            st.error("⚠️ Password must be at least 6 characters long")
                        else:
                            success = create_user(
                                username=new_username,
                                password=new_password,
                                role=new_role,
                                store_id=new_store_id,
                                full_name=new_full_name,
                                email=new_email
                            )
                            if success:
                                st.success("✅ User account created successfully!")
                                st.rerun()
                            else:
                                st.error("❌ Username already exists. Please choose a different username.")
                    else:
                        st.error("⚠️ Please fill in all required fields")
    
    # Demo credentials (only shown when no one is logged in)
    if not st.session_state.get('authenticated'):
        st.markdown("---")
        st.info("""
        **System Access:**
        - Please contact your administrator for login credentials
        - Initial admin account must be created through database setup
        """)
    
    st.markdown("</div>", unsafe_allow_html=True)