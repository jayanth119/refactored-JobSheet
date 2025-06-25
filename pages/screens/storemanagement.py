import sys 
import os 
import pandas as pd 
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏪 View Stores", "➕ Add Store", "📊 Store Analytics", "📱 Device Analytics", "🔧 Repair Analytics"])
    
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
        st.markdown("### ➕ Add New Store")

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

                        # Insert into `stores`
                        cursor.execute("""
                            INSERT INTO stores (name, location, phone, email)
                            VALUES (?, ?, ?, ?)
                        """, (store_name, store_location, store_phone, store_email))
                        
                        store_id = cursor.lastrowid

                        # Also link this store to the current user (admin/manager)
                        cursor.execute("""
                            INSERT INTO user_stores (user_id, store_id, is_primary)
                            VALUES (?, ?, ?)
                        """, (user['id'], store_id, 0))  # You can set is_primary=1 if you want

                        conn.commit()
                        st.success(f"✅ Store '{store_name}' added and assigned successfully! (ID: {store_id})")

                    except Exception as e:
                        conn.rollback()
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
    
    with tab4:
        st.markdown("### Device Types Analytics")
        
        # Device type distribution across all stores
        device_query = """
            SELECT s.name as store_name, j.device_type, j.device_model,
                   COUNT(*) as job_count,
                   COUNT(CASE WHEN j.status = 'Completed' THEN 1 END) as completed_count,
                   AVG(CASE WHEN j.status = 'Completed' THEN j.actual_cost END) as avg_repair_cost,
                   SUM(CASE WHEN j.status = 'Completed' THEN j.actual_cost ELSE 0 END) as total_revenue
            FROM jobs j
            JOIN stores s ON j.store_id = s.id
            WHERE j.device_type IS NOT NULL AND j.device_type != ''
            GROUP BY s.name, j.device_type, j.device_model
            ORDER BY job_count DESC
        """
        
        device_data = pd.read_sql(device_query, conn)
        
        if not device_data.empty:
            # Overall device type distribution
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Device Types Distribution")
                device_summary = device_data.groupby('device_type').agg({
                    'job_count': 'sum',
                    'completed_count': 'sum',
                    'total_revenue': 'sum'
                }).reset_index()
                
                fig = px.pie(device_summary, values='job_count', names='device_type',
                           title="Jobs by Device Type")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### Revenue by Device Type")
                fig = px.bar(device_summary, x='device_type', y='total_revenue',
                           title="Revenue by Device Type",
                           color='device_type')
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            # Device models breakdown
            st.markdown("#### Most Common Device Models")
            model_summary = device_data.groupby(['device_type', 'device_model']).agg({
                'job_count': 'sum',
                'avg_repair_cost': 'mean'
            }).reset_index().sort_values('job_count', ascending=False).head(15)
            
            fig = px.bar(model_summary, x='device_model', y='job_count',
                        color='device_type', title="Top 15 Device Models by Job Count")
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Store-wise device preferences
            st.markdown("#### Device Types by Store")
            store_device_pivot = device_data.pivot_table(
                index='store_name', 
                columns='device_type', 
                values='job_count', 
                fill_value=0
            )
            
            fig = px.imshow(store_device_pivot.values,
                           x=store_device_pivot.columns,
                           y=store_device_pivot.index,
                           color_continuous_scale='Blues',
                           title="Device Type Distribution Across Stores")
            fig.update_layout(
                xaxis_title="Device Type",
                yaxis_title="Store"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Detailed device analysis table
            st.markdown("#### Detailed Device Analysis")
            device_analysis = device_data.groupby(['device_type', 'device_model']).agg({
                'job_count': 'sum',
                'completed_count': 'sum',
                'avg_repair_cost': 'mean',
                'total_revenue': 'sum'
            }).reset_index()
            
            device_analysis['completion_rate'] = (device_analysis['completed_count'] / device_analysis['job_count'] * 100).round(2)
            device_analysis['avg_repair_cost'] = device_analysis['avg_repair_cost'].round(2)
            device_analysis['total_revenue'] = device_analysis['total_revenue'].round(2)
            
            device_analysis = device_analysis.sort_values('total_revenue', ascending=False)
            
            st.dataframe(
                device_analysis,
                column_config={
                    "device_type": "Device Type",
                    "device_model": "Model",
                    "job_count": "Total Jobs",
                    "completed_count": "Completed",
                    "completion_rate": st.column_config.NumberColumn("Completion Rate (%)", format="%.1f%%"),
                    "avg_repair_cost": st.column_config.NumberColumn("Avg Cost", format="$%.2f"),
                    "total_revenue": st.column_config.NumberColumn("Total Revenue", format="$%.2f")
                },
                use_container_width=True
            )
            
        else:
            st.info("No device data available for analysis")
    
    with tab5:
        st.markdown("### Repair Analytics")
        
        # Repair success rates and performance metrics
        repair_query = """
            SELECT s.name as store_name,
                   j.status,
                   j.device_type,
                   COUNT(*) as count,
                   AVG(j.actual_cost) as avg_cost,
                   AVG(CASE 
                       WHEN j.completed_at IS NOT NULL AND j.started_at IS NOT NULL 
                       THEN (julianday(j.completed_at) - julianday(j.started_at))
                       ELSE NULL 
                   END) as avg_repair_days,
                   SUM(j.actual_cost) as total_revenue
            FROM jobs j
            JOIN stores s ON j.store_id = s.id
            GROUP BY s.name, j.status, j.device_type
            ORDER BY s.name, count DESC
        """
        
        repair_data = pd.read_sql(repair_query, conn)
        
        if not repair_data.empty:
            # Repair status overview
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Repair Status Distribution")
                status_summary = repair_data.groupby('status')['count'].sum().reset_index()
                fig = px.pie(status_summary, values='count', names='status',
                           title="Overall Repair Status Distribution")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### Average Repair Time by Status")
                time_data = repair_data[repair_data['avg_repair_days'].notna()]
                if not time_data.empty:
                    fig = px.bar(time_data.groupby('status')['avg_repair_days'].mean().reset_index(),
                               x='status', y='avg_repair_days',
                               title="Average Repair Time (Days)")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No repair time data available")
            
            # Success rate by store
            st.markdown("#### Repair Success Rate by Store")
            store_success = repair_data.pivot_table(
                index='store_name',
                columns='status',
                values='count',
                fill_value=0
            )
            
            if 'Completed' in store_success.columns:
                store_success['total_jobs'] = store_success.sum(axis=1)
                store_success['success_rate'] = (store_success['Completed'] / store_success['total_jobs'] * 100).round(2)
                
                fig = px.bar(store_success.reset_index(), 
                           x='store_name', y='success_rate',
                           title="Repair Success Rate by Store (%)")
                st.plotly_chart(fig, use_container_width=True)
            
            # Repair complexity analysis
            st.markdown("#### Repair Complexity Analysis")
            
            # Get repair time and cost correlation
            complexity_query = """
                SELECT j.device_type,
                       AVG(j.actual_cost) as avg_cost,
                       AVG(CASE 
                           WHEN j.completed_at IS NOT NULL AND j.started_at IS NOT NULL 
                           THEN (julianday(j.completed_at) - julianday(j.started_at))
                           ELSE NULL 
                       END) as avg_repair_days,
                       COUNT(CASE WHEN j.status = 'Completed' THEN 1 END) as completed_jobs,
                       COUNT(*) as total_jobs
                FROM jobs j
                WHERE j.status = 'Completed'
                GROUP BY j.device_type
                HAVING completed_jobs >= 5
                ORDER BY avg_cost DESC
            """
            
            complexity_data = pd.read_sql(complexity_query, conn)
            
            if not complexity_data.empty and complexity_data['avg_repair_days'].notna().any():
                fig = px.scatter(complexity_data, 
                               x='avg_repair_days', y='avg_cost',
                               size='completed_jobs',
                               hover_data=['device_type'],
                               title="Repair Complexity: Time vs Cost",
                               labels={'avg_repair_days': 'Average Repair Time (Days)',
                                      'avg_cost': 'Average Repair Cost ($)'})
                st.plotly_chart(fig, use_container_width=True)
            
            # Problem patterns analysis
            st.markdown("#### Common Problem Patterns")
            problem_query = """
                SELECT SUBSTR(problem_description, 1, 50) as problem_preview,
                       COUNT(*) as frequency,
                       AVG(actual_cost) as avg_cost,
                       device_type
                FROM jobs
                WHERE problem_description IS NOT NULL 
                  AND problem_description != ''
                  AND status = 'Completed'
                GROUP BY SUBSTR(problem_description, 1, 50), device_type
                HAVING frequency >= 2
                ORDER BY frequency DESC
                LIMIT 20
            """
            
            problem_data = pd.read_sql(problem_query, conn)
            
            if not problem_data.empty:
                st.dataframe(
                    problem_data,
                    column_config={
                        "problem_preview": "Problem Description",
                        "frequency": "Frequency",
                        "avg_cost": st.column_config.NumberColumn("Avg Cost", format="$%.2f"),
                        "device_type": "Device Type"
                    },
                    use_container_width=True
                )
            
            # Monthly repair trends
            st.markdown("#### Monthly Repair Trends")
            monthly_repairs = pd.read_sql("""
                SELECT strftime('%Y-%m', created_at) as month,
                       status,
                       COUNT(*) as job_count,
                       SUM(actual_cost) as revenue
                FROM jobs
                WHERE created_at >= date('now', '-12 months')
                GROUP BY strftime('%Y-%m', created_at), status
                ORDER BY month
            """, conn)
            
            if not monthly_repairs.empty:
                fig = px.line(monthly_repairs, x='month', y='job_count',
                            color='status', title="Monthly Repair Job Trends")
                st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("No repair data available for analysis")
    
    conn.close()