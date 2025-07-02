import sys 
import os 
import pandas as pd 
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager

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
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🏪 View Stores", 
        "➕ Add Store", 
        "📊 Store Analytics", 
        "📱 Device Analytics", 
        "🔧 Repair Analytics",
        "👨‍🔧 Technician Analytics",
        "📅 Daily Analysis"
    ])
    
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
            device_analysis['avg_repair_cost'] = device_analysis['avg_repair_cost']
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

    with tab6:
        st.markdown("### 👨‍🔧 Technician Analytics")
        
        # Technician performance overview
        col1, col2 = st.columns(2)
        
        with col1:
            # Date range selector for technician analysis
            st.markdown("#### Filter by Date Range")
            date_range = st.date_input(
                "Select Date Range",
                value=[datetime.now() - timedelta(days=30), datetime.now()],
                max_value=datetime.now(),
                key="tech_date_range"
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date = datetime.now() - timedelta(days=30)
                end_date = datetime.now()
        
        with col2:
            # Store filter for technician analysis
            st.markdown("#### Filter by Store")
            all_stores_tech = pd.read_sql("SELECT id, name FROM stores ORDER BY name", conn)
            store_options = ["All Stores"] + all_stores_tech['name'].tolist()
            selected_store_tech = st.selectbox("Select Store", store_options, key="tech_store_filter")
        
        # Build the technician query with filters
        tech_base_query = """
            SELECT u.id as technician_id, u.full_name as technician_name, u.email,
                   s.name as store_name,
                   COUNT(DISTINCT j.id) as total_jobs,
                   COUNT(DISTINCT CASE WHEN j.status = 'Completed' THEN j.id END) as completed_jobs,
                   COUNT(DISTINCT CASE WHEN j.status = 'In Progress' THEN j.id END) as in_progress_jobs,
                   COUNT(DISTINCT CASE WHEN j.status = 'Failed' THEN j.id END) as failed_jobs,
                   COALESCE(SUM(CASE WHEN j.status = 'Completed' THEN j.actual_cost ELSE 0 END), 0) as total_revenue,
                   COALESCE(AVG(CASE WHEN j.status = 'Completed' THEN j.actual_cost END), 0) as avg_job_value,
                   AVG(CASE 
                       WHEN j.completed_at IS NOT NULL AND j.started_at IS NOT NULL 
                       THEN (julianday(j.completed_at) - julianday(j.started_at))
                       ELSE NULL 
                   END) as avg_completion_time,
                   u.last_login
            FROM users u
            LEFT JOIN stores s ON u.store_id = s.id
            LEFT JOIN jobs j ON u.id = j.assigned_by
            WHERE u.role IN ('staff', 'technician')
        """
        
        # Add date filter
        tech_base_query += f" AND (j.created_at IS NULL OR j.created_at BETWEEN '{start_date}' AND '{end_date}')"
        
        # Add store filter
        if selected_store_tech != "All Stores":
            store_id_tech = all_stores_tech[all_stores_tech['name'] == selected_store_tech]['id'].iloc[0]
            tech_base_query += f" AND u.store_id = {store_id_tech}"
        
        tech_base_query += """
            GROUP BY u.id, u.full_name, u.email, s.name, u.last_login
            ORDER BY completed_jobs DESC
        """
        
        technician_data = pd.read_sql(tech_base_query, conn)
        
        if not technician_data.empty:
            # Main technician performance chart
            st.markdown("#### 👨‍🔧 Technician vs Number of Jobs Repaired")
            
            # Create a comprehensive technician performance chart
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Jobs Completed by Technician', 'Total Revenue by Technician', 
                               'Job Success Rate (%)', 'Average Job Value'),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # Sort by completed jobs for better visualization
            tech_sorted = technician_data.sort_values('completed_jobs', ascending=True)
            
            # Jobs completed chart
            fig.add_trace(
                go.Bar(
                    x=tech_sorted['completed_jobs'],
                    y=tech_sorted['technician_name'],
                    orientation='h',
                    name='Completed Jobs',
                    marker_color='lightblue',
                    text=tech_sorted['completed_jobs'],
                    textposition='outside'
                ),
                row=1, col=1
            )
            
            # Revenue chart
            fig.add_trace(
                go.Bar(
                    x=tech_sorted['total_revenue'],
                    y=tech_sorted['technician_name'],
                    orientation='h',
                    name='Total Revenue',
                    marker_color='lightgreen',
                    text=[f'${x:.0f}' for x in tech_sorted['total_revenue']],
                    textposition='outside'
                ),
                row=1, col=2
            )
            
            # Success rate calculation and chart
            tech_sorted['success_rate'] = (tech_sorted['completed_jobs'] / tech_sorted['total_jobs'] * 100).fillna(0)
            fig.add_trace(
                go.Bar(
                    x=tech_sorted['success_rate'],
                    y=tech_sorted['technician_name'],
                    orientation='h',
                    name='Success Rate',
                    marker_color='orange',
                    text=[f'{x:.1f}%' for x in tech_sorted['success_rate']],
                    textposition='outside'
                ),
                row=2, col=1
            )
            
            # Average job value chart
            fig.add_trace(
                go.Bar(
                    x=tech_sorted['avg_job_value'],
                    y=tech_sorted['technician_name'],
                    orientation='h',
                    name='Avg Job Value',
                    marker_color='purple',
                    text=[f'${x:.0f}' for x in tech_sorted['avg_job_value']],
                    textposition='outside'
                ),
                row=2, col=2
            )
            
            fig.update_layout(
                height=600,
                showlegend=False,
                title_text="Comprehensive Technician Performance Dashboard"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Detailed technician comparison table
            st.markdown("#### Detailed Technician Performance")
            
            # Prepare data for display
            display_data = technician_data.copy()
            display_data['success_rate'] = (display_data['completed_jobs'] / display_data['total_jobs'] * 100).fillna(0).round(1)
            display_data['avg_completion_time'] = display_data['avg_completion_time'].fillna(0).round(1)
            display_data['last_login_formatted'] = display_data['last_login'].apply(
                lambda x: x[:10] if x else 'Never'
            )
            
            # Display the dataframe with custom formatting
            st.dataframe(
                display_data[['technician_name', 'store_name', 'total_jobs', 'completed_jobs', 
                             'in_progress_jobs', 'failed_jobs', 'success_rate', 'total_revenue', 
                             'avg_job_value', 'avg_completion_time', 'last_login_formatted']],
                column_config={
                    "technician_name": "Technician Name",
                    "store_name": "Store",
                    "total_jobs": "Total Jobs",
                    "completed_jobs": "Completed",
                    "in_progress_jobs": "In Progress", 
                    "failed_jobs": "Failed",
                    "success_rate": st.column_config.NumberColumn("Success Rate (%)", format="%.1f%%"),
                    "total_revenue": st.column_config.NumberColumn("Total Revenue", format="$%.2f"),
                    "avg_job_value": st.column_config.NumberColumn("Avg Job Value", format="$%.2f"),
                    "avg_completion_time": st.column_config.NumberColumn("Avg Days to Complete", format="%.1f"),
                    "last_login_formatted": "Last Login"
                },
                use_container_width=True
            )
            
            # Top performers section
            st.markdown("#### 🏆 Top Performing Technicians")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Most Jobs Completed**")
                top_jobs = technician_data.nlargest(3, 'completed_jobs')
                for i, (_, tech) in enumerate(top_jobs.iterrows()):
                    medal = ["🥇", "🥈", "🥉"][i]
                    st.write(f"{medal} {tech['technician_name']} - {tech['completed_jobs']} jobs")
            
            with col2:
                st.markdown("**Highest Revenue**")
                top_revenue = technician_data.nlargest(3, 'total_revenue')
                for i, (_, tech) in enumerate(top_revenue.iterrows()):
                    medal = ["🥇", "🥈", "🥉"][i]
                    st.write(f"{medal} {tech['technician_name']} - ${tech['total_revenue']:.2f}")
            
            with col3:
                st.markdown("**Best Success Rate**")
                tech_with_jobs = technician_data[technician_data['total_jobs'] >= 5]  # Only consider techs with at least 5 jobs
                if not tech_with_jobs.empty:
                    tech_with_jobs['success_rate'] = (tech_with_jobs['completed_jobs'] / tech_with_jobs['total_jobs'] * 100)
                    top_success = tech_with_jobs.nlargest(3, 'success_rate')
                    for i, (_, tech) in enumerate(top_success.iterrows()):
                        medal = ["🥇", "🥈", "🥉"][i]
                        st.write(f"{medal} {tech['technician_name']} - {tech['success_rate']:.1f}%")
                else:
                    st.write("Not enough data")
            
            # Workload distribution
            st.markdown("#### 📊 Current Workload Distribution")
            
            current_workload = pd.read_sql("""
                SELECT u.full_name as technician_name,
                       s.name as store_name,
                       COUNT(CASE WHEN j.status = 'In Progress' THEN 1 END) as active_jobs,
                       COUNT(CASE WHEN j.status = 'New' THEN 1 END) as pending_jobs,
                       COUNT(CASE WHEN j.status IN ('In Progress', 'New') THEN 1 END) as total_workload
                FROM users u
                LEFT JOIN stores s ON u.store_id = s.id
                LEFT JOIN jobs j ON u.id = j.assigned_by
                WHERE u.role IN ('staff', 'technician')
                GROUP BY u.id, u.full_name, s.name
                ORDER BY total_workload DESC
            """, conn)
            
            if not current_workload.empty:
                fig = px.bar(current_workload, 
                           x='technician_name', 
                           y=['active_jobs', 'pending_jobs'],
                           title="Current Workload by Technician",
                           labels={'value': 'Number of Jobs', 'variable': 'Job Status'},
                           color_discrete_map={'active_jobs': 'orange', 'pending_jobs': 'lightblue'})
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("No technician data available for the selected criteria")
    
    with tab7:
        st.markdown("### 📅 Daily Analysis")
        
        # Date selector for daily analysis
        col1, col2 = st.columns(2)
        
        with col1:
            analysis_date = st.date_input(
                "Select Date for Analysis",
                value=datetime.now().date(),
                max_value=datetime.now().date(),
                key="daily_analysis_date"
            )
        
        with col2:
            # Store filter for daily analysis
            daily_store_options = ["All Stores"] + all_stores_tech['name'].tolist()
            selected_daily_store = st.selectbox("Select Store", daily_store_options, key="daily_store_filter")
        
        # Build query for daily analysis
        daily_base_query = f"""
            SELECT s.name as store_name,
                   COUNT(DISTINCT j.id) as total_jobs_created,
                   COUNT(DISTINCT CASE WHEN j.status = 'Completed' AND DATE(j.completed_at) = '{analysis_date}' THEN j.id END) as jobs_completed_today,
                   COUNT(DISTINCT CASE WHEN j.status = 'New' THEN j.id END) as new_jobs,
                   COUNT(DISTINCT CASE WHEN j.status = 'In Progress' THEN j.id END) as in_progress_jobs,
                   COALESCE(SUM(CASE WHEN j.status = 'Completed' AND DATE(j.completed_at) = '{analysis_date}' THEN j.actual_cost ELSE 0 END), 0) as daily_revenue,
                   COUNT(DISTINCT c.id) as customers_served
            FROM stores s
            LEFT JOIN jobs j ON s.id = j.store_id AND DATE(j.created_at) = '{analysis_date}'
            LEFT JOIN customers c ON s.id = c.store_id AND DATE(c.created_at) = '{analysis_date}'
        """
        
        if selected_daily_store != "All Stores":
            store_id_daily = all_stores_tech[all_stores_tech['name'] == selected_daily_store]['id'].iloc[0]
            daily_base_query += f" WHERE s.id = {store_id_daily}"
        
        daily_base_query += " GROUP BY s.id, s.name ORDER BY daily_revenue DESC"
        
        daily_data = pd.read_sql(daily_base_query, conn)
        
        if not daily_data.empty:
            # Daily summary metrics
            st.markdown(f"#### 📊 Daily Summary for {analysis_date}")
            
            total_jobs_created = daily_data['total_jobs_created'].sum()
            total_jobs_completed = daily_data['jobs_completed_today'].sum()
            total_daily_revenue = daily_data['daily_revenue'].sum()
            total_customers = daily_data['customers_served'].sum()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📋 Jobs Created", total_jobs_created)
            
            with col2:
                st.metric("✅ Jobs Completed", total_jobs_completed)
            
            with col3:
                st.metric("💰 Daily Revenue", f"${total_daily_revenue:.2f}")
            
            with col4:
                st.metric("👥 New Customers", total_customers)
            
            # Daily performance by store
            if selected_daily_store == "All Stores":
                st.markdown("#### 🏪 Store Performance Today")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.bar(daily_data, x='store_name', y='total_jobs_created',
                               title="Jobs Created Today by Store",
                               color='store_name')
                    fig.update_layout(showlegend=False)
                    fig.update_xaxes(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    fig = px.bar(daily_data, x='store_name', y='daily_revenue',
                               title="Revenue Generated Today by Store",
                               color='store_name')
                    fig.update_layout(showlegend=False)
                    fig.update_xaxes(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)
            
            # Hourly analysis for the selected date
            st.markdown("#### ⏰ Hourly Job Creation Pattern")
            
            hourly_query = f"""
                SELECT strftime('%H', j.created_at) as hour,
                       COUNT(*) as jobs_count,
                       SUM(j.actual_cost) as hourly_revenue
                FROM jobs j
                JOIN stores s ON j.store_id = s.id
                WHERE DATE(j.created_at) = '{analysis_date}'
            """
            
            if selected_daily_store != "All Stores":
                hourly_query += f" AND s.name = '{selected_daily_store}'"
            
            hourly_query += """
                GROUP BY strftime('%H', j.created_at)
                ORDER BY hour
            """
            
            hourly_data = pd.read_sql(hourly_query, conn)
            
            if not hourly_data.empty:
                # Convert hour to more readable format
                hourly_data['hour_formatted'] = hourly_data['hour'].apply(lambda x: f"{x}:00")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.line(hourly_data, x='hour_formatted', y='jobs_count',
                                title="Jobs Created by Hour",
                                markers=True)
                    fig.update_xaxes(title="Hour of Day")
                    fig.update_yaxes(title="Number of Jobs")
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    fig = px.bar(hourly_data, x='hour_formatted', y='hourly_revenue',
                               title="Revenue by Hour",
                               color='hourly_revenue')
                    fig.update_xaxes(title="Hour of Day")
                    fig.update_yaxes(title="Revenue ($)")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No hourly data available for {analysis_date}")
            
            # Daily technician activity
            st.markdown("#### 👨‍🔧 Technician Activity Today")
            
            daily_tech_query = f"""
                SELECT u.full_name as technician_name,
                       s.name as store_name,
                       COUNT(CASE WHEN DATE(j.created_at) = '{analysis_date}' THEN 1 END) as jobs_assigned_today,
                       COUNT(CASE WHEN DATE(j.completed_at) = '{analysis_date}' THEN 1 END) as jobs_completed_today,
                       SUM(CASE WHEN DATE(j.completed_at) = '{analysis_date}' THEN j.actual_cost ELSE 0 END) as revenue_today
                FROM users u
                LEFT JOIN stores s ON u.store_id = s.id
                LEFT JOIN jobs j ON u.id = j.assigned_by
                WHERE u.role IN ('staff', 'technician')
            """
            
            if selected_daily_store != "All Stores":
                daily_tech_query += f" AND s.name = '{selected_daily_store}'"
            
            daily_tech_query += """
                GROUP BY u.id, u.full_name, s.name
                HAVING jobs_assigned_today > 0 OR jobs_completed_today > 0
                ORDER BY jobs_completed_today DESC, jobs_assigned_today DESC
            """
            
            daily_tech_data = pd.read_sql(daily_tech_query, conn)
            
            if not daily_tech_data.empty:
                st.dataframe(
                    daily_tech_data,
                    column_config={
                        "technician_name": "Technician",
                        "store_name": "Store",
                        "jobs_assigned_today": "Jobs Assigned Today",
                        "jobs_completed_today": "Jobs Completed Today",
                        "revenue_today": st.column_config.NumberColumn("Revenue Today", format="$%.2f")
                    },
                    use_container_width=True
                )
            else:
                st.info(f"No technician activity data for {analysis_date}")
            
            # Device types worked on today
            st.markdown("#### 📱 Device Types Serviced Today")
            
            device_daily_query = f"""
                SELECT j.device_type,
                       COUNT(*) as count,
                       AVG(j.actual_cost) as avg_cost
                FROM jobs j
                JOIN stores s ON j.store_id = s.id
                WHERE DATE(j.created_at) = '{analysis_date}'
                  AND j.device_type IS NOT NULL 
                  AND j.device_type != ''
            """
            
            if selected_daily_store != "All Stores":
                device_daily_query += f" AND s.name = '{selected_daily_store}'"
            
            device_daily_query += """
                GROUP BY j.device_type
                ORDER BY count DESC
            """
            
            device_daily_data = pd.read_sql(device_daily_query, conn)
            
            if not device_daily_data.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.pie(device_daily_data, values='count', names='device_type',
                               title="Device Types Serviced Today")
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    fig = px.bar(device_daily_data, x='device_type', y='avg_cost',
                               title="Average Repair Cost by Device Type",
                               color='device_type')
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No device service data for {analysis_date}")
            
            # Weekly comparison
            st.markdown("#### 📈 Weekly Trend Comparison")
            
            # Get data for the past 7 days including selected date
            week_start = analysis_date - timedelta(days=6)
            week_end = analysis_date
            
            weekly_query = f"""
                SELECT DATE(j.created_at) as date,
                       COUNT(*) as jobs_created,
                       COUNT(CASE WHEN j.status = 'Completed' THEN 1 END) as jobs_completed,
                       SUM(CASE WHEN j.status = 'Completed' THEN j.actual_cost ELSE 0 END) as daily_revenue
                FROM jobs j
                JOIN stores s ON j.store_id = s.id
                WHERE DATE(j.created_at) BETWEEN '{week_start}' AND '{week_end}'
            """
            
            if selected_daily_store != "All Stores":
                weekly_query += f" AND s.name = '{selected_daily_store}'"
            
            weekly_query += """
                GROUP BY DATE(j.created_at)
                ORDER BY date
            """
            
            weekly_data = pd.read_sql(weekly_query, conn)
            
            if not weekly_data.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    
                    fig.add_trace(
                        go.Scatter(x=weekly_data['date'], y=weekly_data['jobs_created'],
                                 mode='lines+markers', name='Jobs Created', line=dict(color='blue')),
                        secondary_y=False
                    )
                    
                    fig.add_trace(
                        go.Scatter(x=weekly_data['date'], y=weekly_data['jobs_completed'],
                                 mode='lines+markers', name='Jobs Completed', line=dict(color='green')),
                        secondary_y=False
                    )
                    
                    fig.update_xaxes(title_text="Date")
                    fig.update_yaxes(title_text="Number of Jobs", secondary_y=False)
                    fig.update_layout(title_text="7-Day Job Activity Trend")
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    fig = px.line(weekly_data, x='date', y='daily_revenue',
                                title="7-Day Revenue Trend",
                                markers=True)
                    fig.update_yaxes(title="Revenue ($)")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No weekly trend data available")
                
        else:
            st.info(f"No data available for {analysis_date}")
    
    conn.close()
    