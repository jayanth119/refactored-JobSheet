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

from components.css import CSS
from components.datamanager.databasemanger import DatabaseManager


# Configure Streamlit page
st.set_page_config(
    page_title="RepairPro - Management System",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS styling
st.markdown(CSS, unsafe_allow_html=True)



def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def authenticate_user(username, password):
    db = DatabaseManager()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT u.id, u.username, u.role, u.store_id, u.full_name, u.email, s.name as store_name
        FROM users u
        LEFT JOIN stores s ON u.store_id = s.id
        WHERE u.username = ? AND u.password = ?
    """, (username, hash_password(password)))
    
    user = cursor.fetchone()
    
    if user:
        # Update last login
        cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user[0],))
        conn.commit()
        
        user_data = {
            "id": user[0],
            "username": user[1],
            "role": user[2],
            "store_id": user[3],
            "full_name": user[4],
            "email": user[5],
            "store_name": user[6] if user[6] else "All Stores"
        }
        conn.close()
        return user_data
    
    conn.close()
    return None

def create_user(username, password, role, store_id, full_name, email):
    db = DatabaseManager()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (username, password, role, store_id, full_name, email) VALUES (?, ?, ?, ?, ?, ?)",
            (username, hash_password(password), role, store_id, full_name, email)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def check_session_timeout():
    if 'login_time' in st.session_state:
        session_duration = time.time() - st.session_state.login_time
        if session_duration > 3600:  # 1 hour timeout
            st.session_state.clear()
            st.rerun()
        return session_duration
    return 0

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
                        st.success(f"Welcome back, {user['full_name']}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
                else:
                    st.error("⚠️ Please enter both username and password")
        
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
    session_duration = check_session_timeout()
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
        st.rerun()
    
    return menu_items[selected]

def admin_dashboard():
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
        LIMIT 10
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

def jobs_management():
    user = st.session_state.user
    
    st.markdown(f'''
        <div class="main-header">
            <h1>📋 Jobs Management</h1>
            <p>Manage repair jobs for {user['store_name'] if user['role'] == 'staff' else 'all stores'}</p>
        </div>
    ''', unsafe_allow_html=True)
    
    # Tabs for different job operations
    tab1, tab2, tab3 = st.tabs(["📝 Add New Job", "📋 View Jobs", "🔍 Search Jobs"])
    
    db = DatabaseManager()
    conn = db.get_connection()
    
    with tab1:
        st.markdown("### Create New Repair Job")
        with st.form("new_job_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                customer_name = st.text_input("Customer Name*", placeholder="Enter customer name")
                device_type = st.selectbox("Device Type*", [
                    "Smartphone", "Laptop", "Desktop", "Tablet", "Smart Watch", 
                    "Gaming Console", "TV", "Other Electronics"
                ])
                device_model = st.text_input("Device Model", placeholder="e.g., iPhone 13, MacBook Pro")
                estimated_cost = st.number_input("Estimated Cost ($)", min_value=0.0, value=0.0, step=0.01)
            
            with col2:
                problem_description = st.text_area("Problem Description*", 
                                                 placeholder="Describe the issue in detail",
                                                 height=100)
                
                # Get technicians for current store (or all for admin)
                if user['role'] == 'admin':
                    technicians = pd.read_sql("""
                        SELECT DISTINCT u.full_name, s.name as store_name
                        FROM users u
                        LEFT JOIN stores s ON u.store_id = s.id
                        WHERE u.role = 'staff'
                        ORDER BY u.full_name
                    """, conn)
                    tech_options = [f"{row['full_name']} ({row['store_name']})" for _, row in technicians.iterrows()]
                else:
                    technicians = pd.read_sql("""
                        SELECT full_name FROM users 
                        WHERE role = 'staff' AND store_id = ?
                        ORDER BY full_name
                    """, conn, params=[user['store_id']])
                    tech_options = technicians['full_name'].tolist()
                
                technician = st.selectbox("Assign Technician", ["Unassigned"] + tech_options)
                
                status = st.selectbox("Initial Status", ["New", "In Progress", "Pending"])
            
            submit_job = st.form_submit_button("🔧 Create Job", use_container_width=True)
            
            if submit_job:
                if customer_name and device_type and problem_description:
                    try:
                        store_id = user['store_id'] if user['role'] == 'staff' else 1  # Default to first store for admin
                        tech_name = technician if technician != "Unassigned" else None
                        
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO jobs (customer_name, device_type, device_model, 
                                            problem_description, estimated_cost, status, 
                                            technician, store_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (customer_name, device_type, device_model, problem_description,
                             estimated_cost, status, tech_name, store_id))
                        
                        job_id = cursor.lastrowid
                        conn.commit()
                        
                        st.success(f"✅ Job #{job_id} created successfully!")
                        
                    except Exception as e:
                        st.error(f"❌ Error creating job: {str(e)}")
                else:
                    st.error("⚠️ Please fill in all required fields")
    
    with tab2:
        st.markdown("### Current Jobs")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Filter by Status", ["All", "New", "In Progress", "Completed", "Pending"])
        with col2:
            device_filter = st.selectbox("Filter by Device", ["All", "Smartphone", "Laptop", "Desktop", "Tablet", "Other"])
        with col3:
            sort_by = st.selectbox("Sort by", ["Recent First", "Oldest First", "Customer Name", "Status"])
        
        # Build query based on user role and filters
        base_query = """
            SELECT j.id, j.customer_name, j.device_type, j.device_model,
                   j.problem_description, j.estimated_cost, j.actual_cost,
                   j.status, j.technician, j.created_at, j.updated_at,
                   s.name as store_name
            FROM jobs j
            LEFT JOIN stores s ON j.store_id = s.id
        """
        
        conditions = []
        params = []
        
        if user['role'] == 'staff':
            conditions.append("j.store_id = ?")
            params.append(user['store_id'])
        
        if status_filter != "All":
            conditions.append("j.status = ?")
            params.append(status_filter)
        
        if device_filter != "All":
            conditions.append("j.device_type = ?")
            params.append(device_filter)
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        
        # Add sorting
        if sort_by == "Recent First":
            base_query += " ORDER BY j.created_at DESC"
        elif sort_by == "Oldest First":
            base_query += " ORDER BY j.created_at ASC"
        elif sort_by == "Customer Name":
            base_query += " ORDER BY j.customer_name ASC"
        elif sort_by == "Status":
            base_query += " ORDER BY j.status ASC"
        
        jobs_df = pd.read_sql(base_query, conn, params=params)
        
        if not jobs_df.empty:
            # Display jobs in a more interactive way
            for _, job in jobs_df.iterrows():
                with st.expander(f"#{job['id']} - {job['customer_name']} | {job['device_type']} - {job['status']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Device:** {job['device_type']} - {job['device_model']}")
                        st.write(f"**Problem:** {job['problem_description']}")
                        st.write(f"**Technician:** {job['technician'] or 'Unassigned'}")
                        if user['role'] == 'admin':
                            st.write(f"**Store:** {job['store_name']}")
                    
                    with col2:
                        st.write(f"**Status:** {job['status']}")
                        st.write(f"**Estimated Cost:** ${job['estimated_cost']:.2f}")
                        st.write(f"**Actual Cost:** ${job['actual_cost']:.2f}")
                        st.write(f"**Created:** {job['created_at'][:10]}")
                    
                    # Quick action buttons
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        if st.button(f"✏️ Edit", key=f"edit_{job['id']}"):
                            st.session_state[f"edit_job_{job['id']}"] = True
                    with col2:
                        if st.button(f"🔄 Update Status", key=f"status_{job['id']}"):
                            st.session_state[f"update_status_{job['id']}"] = True
                    with col3:
                        if st.button(f"💰 Update Cost", key=f"cost_{job['id']}"):
                            st.session_state[f"update_cost_{job['id']}"] = True
                    with col4:
                        if st.button(f"🗑️ Delete", key=f"delete_{job['id']}"):
                            if st.session_state.get(f"confirm_delete_{job['id']}", False):
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM jobs WHERE id = ?", (job['id'],))
                                conn.commit()
                                st.success(f"Job #{job['id']} deleted successfully!")
                                st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{job['id']}"] = True
                                st.warning("Click delete again to confirm")
        else:
            st.info("No jobs found matching your criteria")
    
    with tab3:
        st.markdown("### Search Jobs")
        
        search_term = st.text_input("🔍 Search by customer name, device, or problem description")
        
        if search_term:
            search_query = """
                SELECT j.id, j.customer_name, j.device_type, j.device_model,
                       j.problem_description, j.status, j.technician, 
                       j.created_at, s.name as store_name
                FROM jobs j
                LEFT JOIN stores s ON j.store_id = s.id
                WHERE (j.customer_name LIKE ? OR j.device_type LIKE ? OR 
                       j.device_model LIKE ? OR j.problem_description LIKE ?)
            """
            
            params = [f"%{search_term}%"] * 4
            
            if user['role'] == 'staff':
                search_query += " AND j.store_id = ?"
                params.append(user['store_id'])
            
            search_query += " ORDER BY j.created_at DESC LIMIT 20"
            
            search_results = pd.read_sql(search_query, conn, params=params)
            
            if not search_results.empty:
                st.write(f"Found {len(search_results)} results:")
                
                for _, job in search_results.iterrows():
                    status_class = f"status-{job['status'].lower().replace(' ', '-')}"
                    store_info = f" | 🏪 {job['store_name']}" if user['role'] == 'admin' else ""
                    
                    st.markdown(f'''
                        <div class="job-card">
                            <div class="job-title">#{job['id']} - {job['customer_name']}{store_info}</div>
                            <div class="job-details">{job['device_type']} - {job['device_model']}</div>
                            <div class="job-details">{job['problem_description']}</div>
                            <div class="job-details">👨‍🔧 {job['technician'] or 'Unassigned'} | 📅 {job['created_at'][:10]}</div>
                            <span class="{status_class}">{job['status']}</span>
                        </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info("No jobs found matching your search term")
    
    conn.close()

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

def store_management():
    """Only accessible by admin users"""
    user = st.session_state.user
    
    if user['role'] != 'admin':
        st.error("❌ Access Denied: Admin privileges required")
        return
    
    st.markdown('''
        <div class="main-header">
            <h1>🏪 Store Management</h1>
            <p>Manage all store locations and their performance</p>
        </div>
    ''', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🏪 View Stores", "➕ Add Store", "📊 Store Analytics"])
    
    db = DatabaseManager()
    conn = db.get_connection()
    
    with tab1:
        st.markdown("### Store Directory")
        
        stores_query = """
            SELECT s.id, s.name, s.location, s.phone, s.email, s.created_at,
                   COUNT(DISTINCT u.id) as staff_count,
                   COUNT(DISTINCT j.id) as total_jobs,
                   COUNT(DISTINCT c.id) as total_customers,
                   COALESCE(SUM(CASE WHEN j.status = 'Completed' THEN j.actual_cost ELSE 0 END), 0) as total_revenue
            FROM stores s
            LEFT JOIN users u ON s.id = u.store_id AND u.role = 'staff'
            LEFT JOIN jobs j ON s.id = j.store_id
            LEFT JOIN customers c ON s.id = c.store_id
            GROUP BY s.id, s.name, s.location, s.phone, s.email, s.created_at
            ORDER BY s.created_at ASC
        """
        
        stores_df = pd.read_sql(stores_query, conn)
        
        if not stores_df.empty:
            for _, store in stores_df.iterrows():
                with st.expander(f"🏪 {store['name']} - {store['location']}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**Store Information**")
                        st.write(f"**Name:** {store['name']}")
                        st.write(f"**Location:** {store['location']}")
                        st.write(f"**Phone:** {store['phone']}")
                        st.write(f"**Email:** {store['email']}")
                        st.write(f"**Created:** {store['created_at'][:10]}")
                    
                    with col2:
                        st.markdown("**Staff & Operations**")
                        st.metric("Staff Members", store['staff_count'])
                        st.metric("Total Jobs", store['total_jobs'])
                        st.metric("Customers", store['total_customers'])
                    
                    with col3:
                        st.markdown("**Performance**")
                        st.metric("Total Revenue", f"${store['total_revenue']:.2f}")
                        
                        # Recent activity
                        recent_jobs = pd.read_sql("""
                            SELECT COUNT(*) as count FROM jobs 
                            WHERE store_id = ? AND DATE(created_at) >= DATE('now', '-7 days')
                        """, conn, params=[store['id']]).iloc[0]['count']
                        
                        st.metric("Jobs (Last 7 Days)", recent_jobs)
                    
                    # Store staff list
                    store_staff = pd.read_sql("""
                        SELECT full_name, email, last_login 
                        FROM users 
                        WHERE store_id = ? AND role = 'staff'
                        ORDER BY full_name
                    """, conn, params=[store['id']])
                    
                    if not store_staff.empty:
                        st.markdown("**Store Staff:**")
                        for _, staff in store_staff.iterrows():
                            last_login = staff['last_login'][:10] if staff['last_login'] else 'Never'
                            st.write(f"👨‍🔧 {staff['full_name']} ({staff['email']}) - Last login: {last_login}")
        else:
            st.info("No stores found")
    
    with tab2:
        st.markdown("### Add New Store")
        
        with st.form("new_store_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                store_name = st.text_input("Store Name*", placeholder="e.g., RepairPro Downtown")
                store_location = st.text_input("Location*", placeholder="e.g., Main Street Plaza")
            
            with col2:
                store_phone = st.text_input("Phone Number", placeholder="e.g., 555-0123")
                store_email = st.text_input("Email", placeholder="e.g., downtown@repairpro.com")
            
            submit_store = st.form_submit_button("🏪 Add Store", use_container_width=True)
            
            if submit_store:
                if store_name and store_location:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO stores (name, location, phone, email)
                            VALUES (?, ?, ?, ?)
                        """, (store_name, store_location, store_phone, store_email))
                        
                        store_id = cursor.lastrowid
                        conn.commit()
                        
                        st.success(f"✅ Store '{store_name}' added successfully! (ID: {store_id})")
                        
                    except Exception as e:
                        st.error(f"❌ Error adding store: {str(e)}")
                else:
                    st.error("⚠️ Please fill in required fields (Name and Location)")
    
    with tab3:
        st.markdown("### Store Performance Analytics")
        
        # Store comparison metrics
        store_metrics = pd.read_sql("""
            SELECT s.name as store_name,
                   COUNT(DISTINCT j.id) as total_jobs,
                   COUNT(DISTINCT CASE WHEN j.status = 'Completed' THEN j.id END) as completed_jobs,
                   COUNT(DISTINCT CASE WHEN j.status = 'In Progress' THEN j.id END) as in_progress_jobs,
                   COUNT(DISTINCT c.id) as total_customers,
                   COALESCE(SUM(CASE WHEN j.status = 'Completed' THEN j.actual_cost ELSE 0 END), 0) as total_revenue,
                   COALESCE(AVG(CASE WHEN j.status = 'Completed' THEN j.actual_cost ELSE NULL END), 0) as avg_job_value
            FROM stores s
            LEFT JOIN jobs j ON s.id = j.store_id
            LEFT JOIN customers c ON s.id = c.store_id
            GROUP BY s.id, s.name
            ORDER BY total_revenue DESC
        """, conn)
        
        if not store_metrics.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Revenue by Store")
                fig = px.bar(store_metrics, x='store_name', y='total_revenue',
                            title="Total Revenue by Store",
                            color='store_name',
                            color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.markdown("#### Job Completion Rate")
                store_metrics['completion_rate'] = (store_metrics['completed_jobs'] / store_metrics['total_jobs']) * 100
                fig = px.bar(store_metrics, x='store_name', y='completion_rate',
                            title="Job Completion Rate (%)",
                            color='store_name',
                            color_discrete_sequence=px.colors.qualitative.Pastel1)
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # Monthly trends for selected store
            selected_store = st.selectbox("Select Store for Detailed Analysis", store_metrics['store_name'].tolist())
            
            store_id = pd.read_sql("SELECT id FROM stores WHERE name = ?", conn, params=[selected_store]).iloc[0]['id']
            
            # Monthly revenue trend
            monthly_revenue = pd.read_sql("""
                SELECT strftime('%Y-%m', completed_at) as month,
                       SUM(actual_cost) as revenue,
                       COUNT(*) as jobs_completed
                FROM jobs
                WHERE store_id = ? AND status = 'Completed' AND completed_at IS NOT NULL
                GROUP BY strftime('%Y-%m', completed_at)
                ORDER BY month
            """, conn, params=[store_id])
            
            if not monthly_revenue.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"#### {selected_store} - Monthly Revenue")
                    fig = px.line(monthly_revenue, x='month', y='revenue',
                                 title="Monthly Revenue Trend",
                                 markers=True)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown(f"#### {selected_store} - Jobs Completed")
                    fig = px.bar(monthly_revenue, x='month', y='jobs_completed',
                                title="Monthly Completed Jobs",
                                color='jobs_completed')
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No completed jobs data available for {selected_store}")
        else:
            st.info("No store performance data available")
    
    conn.close()

def reports_management():
    user = st.session_state.user
    
    st.markdown(f'''
        <div class="main-header">
            <h1>📊 Reports & Analytics</h1>
            <p>Generate reports and analyze business performance</p>
        </div>
    ''', unsafe_allow_html=True)
    
    db = DatabaseManager()
    conn = db.get_connection()
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", value=datetime.now())
    
    # Convert dates to strings for SQL query
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    # Store filter for admin users
    if user['role'] == 'admin':
        stores = pd.read_sql("SELECT id, name FROM stores", conn)
        store_options = dict(zip(stores['name'], stores['id']))
        selected_store = st.selectbox("Select Store", ["All Stores"] + list(store_options.keys()))
    else:
        selected_store = None
    
    # Build query conditions based on filters
    conditions = []
    params = []
    
    conditions.append("j.created_at BETWEEN ? AND ?")
    params.extend([start_date_str, end_date_str])
    
    if user['role'] == 'staff':
        conditions.append("j.store_id = ?")
        params.append(user['store_id'])
    elif user['role'] == 'admin' and selected_store != "All Stores":
        conditions.append("j.store_id = ?")
        params.append(store_options[selected_store])
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Generate reports
    tab1, tab2, tab3 = st.tabs(["📈 Performance Report", "💰 Financial Report", "📅 Activity Report"])
    
    with tab1:
        st.markdown("### Performance Metrics")
        
        # Key metrics
        metrics_query = f"""
            SELECT 
                COUNT(*) as total_jobs,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_jobs,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as in_progress_jobs,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_jobs,
                SUM(CASE WHEN status = 'Completed' THEN actual_cost ELSE 0 END) as total_revenue,
                AVG(CASE WHEN status = 'Completed' THEN actual_cost ELSE NULL END) as avg_job_value
            FROM jobs j
            WHERE {where_clause}
        """
        
        metrics = pd.read_sql(metrics_query, conn, params=params).iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Jobs", metrics['total_jobs'])
        with col2:
            st.metric("Completed Jobs", metrics['completed_jobs'])
        with col3:
            st.metric("Revenue", f"${metrics['total_revenue']:,.2f}")
        with col4:
            st.metric("Avg. Job Value", f"${metrics['avg_job_value']:,.2f}" if metrics['avg_job_value'] else "$0.00")
        
        st.markdown("---")
        
        # Job status distribution
        status_query = f"""
            SELECT status, COUNT(*) as count
            FROM jobs j
            WHERE {where_clause}
            GROUP BY status
        """
        
        status_data = pd.read_sql(status_query, conn, params=params)
        
        if not status_data.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Job Status Distribution")
                fig = px.pie(status_data, values='count', names='status',
                            title="Job Status Breakdown",
                            color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### Jobs by Device Type")
                device_query = f"""
                    SELECT device_type, COUNT(*) as count
                    FROM jobs j
                    WHERE {where_clause}
                    GROUP BY device_type
                    ORDER BY count DESC
                """
                device_data = pd.read_sql(device_query, conn, params=params)
                
                fig = px.bar(device_data, x='device_type', y='count',
                            title="Jobs by Device Type",
                            color='device_type')
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No job data available for the selected period")
    
    with tab2:
        st.markdown("### Financial Analysis")
        
        # Revenue trends
        revenue_query = f"""
            SELECT strftime('%Y-%m-%d', completed_at) as date,
                   SUM(actual_cost) as daily_revenue,
                   COUNT(*) as jobs_completed
            FROM jobs j
            WHERE status = 'Completed' AND {where_clause.replace('j.created_at', 'j.completed_at')}
            GROUP BY strftime('%Y-%m-%d', completed_at)
            ORDER BY date
        """
        
        revenue_data = pd.read_sql(revenue_query, conn, params=params)
        
        if not revenue_data.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Daily Revenue")
                fig = px.line(revenue_data, x='date', y='daily_revenue',
                            title="Daily Revenue Trend",
                            markers=True)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### Revenue vs. Jobs Completed")
                fig = px.scatter(revenue_data, x='jobs_completed', y='daily_revenue',
                                title="Revenue vs. Job Volume",
                                trendline="ols")
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # Top revenue customers
            customer_rev_query = f"""
                SELECT j.customer_name, SUM(j.actual_cost) as total_spent, COUNT(*) as jobs_count
                FROM jobs j
                WHERE status = 'Completed' AND {where_clause.replace('j.created_at', 'j.completed_at')}
                GROUP BY j.customer_name
                ORDER BY total_spent DESC
                LIMIT 10
            """
            
            top_customers = pd.read_sql(customer_rev_query, conn, params=params)
            
            if not top_customers.empty:
                st.markdown("#### Top Customers by Revenue")
                fig = px.bar(top_customers, x='customer_name', y='total_spent',
                            title="Top 10 Customers by Revenue",
                            hover_data=['jobs_count'],
                            labels={'total_spent': 'Total Revenue', 'customer_name': 'Customer'})
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No financial data available for the selected period")
    
    with tab3:
        st.markdown("### Activity Report")
        
        # Job activity timeline
        activity_query = f"""
            SELECT strftime('%Y-%m-%d', created_at) as date,
                   COUNT(*) as jobs_created,
                   SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as jobs_completed
            FROM jobs j
            WHERE {where_clause}
            GROUP BY strftime('%Y-%m-%d', created_at)
            ORDER BY date
        """
        
        activity_data = pd.read_sql(activity_query, conn, params=params)
        
        if not activity_data.empty:
            st.markdown("#### Daily Job Activity")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=activity_data['date'], y=activity_data['jobs_created'],
                name='Jobs Created',
                line=dict(color='#667eea', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=activity_data['date'], y=activity_data['jobs_completed'],
                name='Jobs Completed',
                line=dict(color='#28a745', width=2)
            ))
            fig.update_layout(
                title="Job Creation vs. Completion",
                xaxis_title="Date",
                yaxis_title="Number of Jobs"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Export button
            if st.button("📄 Export Activity Report as PDF"):
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=letter)
                
                # PDF content
                c.setFont("Helvetica-Bold", 16)
                c.drawString(100, 750, f"RepairPro Activity Report")
                c.setFont("Helvetica", 12)
                c.drawString(100, 730, f"Date Range: {start_date_str} to {end_date_str}")
                
                if user['role'] == 'admin' and selected_store != "All Stores":
                    c.drawString(100, 710, f"Store: {selected_store}")
                
                # Add summary
                c.setFont("Helvetica-Bold", 14)
                c.drawString(100, 680, "Summary Statistics")
                c.setFont("Helvetica", 12)
                
                c.drawString(120, 650, f"Total Jobs: {activity_data['jobs_created'].sum()}")
                c.drawString(120, 630, f"Completed Jobs: {activity_data['jobs_completed'].sum()}")
                c.drawString(120, 610, f"Completion Rate: {activity_data['jobs_completed'].sum()/activity_data['jobs_created'].sum():.1%}")
                
                # Add chart image
                # Note: In a real app, you would save the plot to a temporary file and add it to the PDF
                c.drawString(100, 580, "Daily Activity Chart (see app for visualization)")
                
                c.save()
                buffer.seek(0)
                
                st.success("Report generated successfully!")
                st.download_button(
                    label="⬇️ Download PDF",
                    data=buffer,
                    file_name=f"RepairPro_Activity_Report_{start_date_str}_to_{end_date_str}.pdf",
                    mime="application/pdf"
                )
        else:
            st.info("No activity data available for the selected period")
    
    conn.close()

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

def main():
    if 'authenticated' not in st.session_state:
        login_signup_page()
    else:
        current_page = sidebar_navigation()
        
        if current_page == "dashboard":
            if st.session_state.user['role'] == 'admin':
                admin_dashboard()
            else:
                staff_dashboard()
        elif current_page == "jobs":
            jobs_management()
        elif current_page == "customers":
            customers_management()
        elif current_page == "stores":
            store_management()
        elif current_page == "reports":
            reports_management()
        elif current_page == "users":
            user_management()
        elif current_page == "settings":
            settings_page()

if __name__ == "__main__":
    main()