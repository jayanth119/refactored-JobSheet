import sys 
import os 
import pandas as pd 
import streamlit as st
import plotly.express as px
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.css.css import Style
from components.datamanager.databasemanger import DatabaseManager
from components.utils.auth import hash_password , verify_password,authenticate_user , create_user
from pages.screens.loginpage import login_signup_page
from pages.screens.admindashboard import admin_dashboard

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