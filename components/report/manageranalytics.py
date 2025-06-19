import sys 
import os 
import pandas as pd 
import streamlit as st
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import plotly.express as px

def manager_analytics(conn, start_date_str, end_date_str, user):
    """Store-specific analytics for manager users"""
    
    st.markdown(f"### 🏪 Store Analytics - {user.get('store_name', 'Your Store')}")
    
    # Manager sees only their store data
    where_clause = "j.created_at BETWEEN ? AND ? AND j.store_id = ?"
    params = [start_date_str, end_date_str, user['store_id']]
    
    # Get store information
    store_info = pd.read_sql("SELECT name, location, phone, email FROM stores WHERE id = ?", 
                            conn, params=[user['store_id']])
    
    if not store_info.empty:
        store = store_info.iloc[0]
        st.info(f"📍 {store['name']} | {store['location']} | 📞 {store['phone']}")
    
    # Create manager-specific tabs
    tab1, tab2  = st.tabs([
        "📊 Store Dashboard", 
        "👨‍🔧 Team Performance", 
    ])
    
    with tab1:
        store_dashboard(conn, where_clause, params, user['store_id'], user)
    
    with tab2:
        team_performance(conn, where_clause, params, user['store_id'])
    
    # with tab3:
    #     customer_management(conn, where_clause, params, user['store_id'])
    
    # with tab4:
    #     revenue_analysis(conn, where_clause, params)


def store_dashboard(conn, where_clause, params, store_id, user):
    """Store-specific dashboard for managers"""

    st.subheader("📊 Store Dashboard")

    # === KPIs ===
    store_kpi_query = f"""
    SELECT 
        COUNT(*) as total_jobs,
        COALESCE(SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END), 0) as completed_jobs,
        COALESCE(SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END), 0) as in_progress_jobs,
        COALESCE(SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END), 0) as pending_jobs,
        COALESCE(SUM(CASE WHEN status = 'Completed' THEN actual_cost ELSE 0 END), 0) as total_revenue,
        COUNT(DISTINCT customer_id) as unique_customers
    FROM jobs j
    WHERE {where_clause} AND store_id = ?
    """

    query_params = params.copy()
    query_params.append(store_id)

    try:
        store_kpis_df = pd.read_sql(store_kpi_query, conn, params=query_params)
    except Exception as e:
        st.error(f"❌ Failed to load store KPIs: {e}")
        return

    if store_kpis_df.empty:
        st.warning("⚠️ No data found for the selected period.")
        return

    store_kpis = store_kpis_df.iloc[0]

    total_jobs = int(store_kpis['total_jobs'] or 0)
    completed_jobs = int(store_kpis['completed_jobs'] or 0)
    in_progress_jobs = int(store_kpis['in_progress_jobs'] or 0)
    pending_jobs = int(store_kpis['pending_jobs'] or 0)
    total_revenue = float(store_kpis['total_revenue'] or 0.0)
    unique_customers = int(store_kpis['unique_customers'] or 0)

    # === Metrics UI ===
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Jobs", f"{total_jobs:,}")
        st.metric("Completed", f"{completed_jobs:,}")
    with col2:
        st.metric("Revenue", f"₹{total_revenue:,.2f}")
        st.metric("Unique Customers", f"{unique_customers:,}")
    with col3:
        st.metric("In Progress", f"{in_progress_jobs:,}")
        st.metric("Pending", f"{pending_jobs:,}")

    # === Performance Charts ===
    col1, col2 = st.columns([2, 1])

    # --- Bar Chart: Jobs by Status ---
    with col1:
        st.markdown(f"### 📊 {user['store_name']} - Performance Overview")
        try:
            status_data = pd.read_sql("""
                SELECT status, COUNT(*) as count
                FROM jobs
                WHERE store_id = ?
                GROUP BY status
                ORDER BY count DESC
            """, conn, params=[user['store_id']])

            if not status_data.empty:
                fig = px.bar(
                    status_data,
                    x='status', y='count',
                    title=f"Jobs by Status - {user['store_name']}",
                    color='status',
                    color_discrete_map={
                        'New': '#ffc107',
                        'In Progress': '#17a2b8',
                        'Completed': '#28a745',
                        'Pending': '#dc3545'
                    }
                )
                fig.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No job status data available.")
        except Exception as e:
            st.error(f"Error loading job status chart: {e}")

    # --- Line Chart: Revenue Trend ---
    with col2:
        st.markdown("### 📈 Monthly Revenue Trend")
        try:
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
                fig = px.line(
                    monthly_revenue,
                    x='month', y='revenue',
                    title="Revenue Trend",
                    markers=True
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No revenue data available.")
        except Exception as e:
            st.error(f"Error loading revenue chart: {e}")



def team_performance(conn, where_clause, params, store_id):
    """Team performance analysis for managers - CORRECTED VERSION"""
    
    # First, get all technicians assigned to this store
    technicians_query = """
        SELECT 
            u.id,
            u.full_name,
            u.email
        FROM users u
        JOIN store_technicians st ON u.id = st.technician_id
        WHERE st.store_id = ? 
            AND st.is_active = 1 
            AND u.role = 'technician'
    """
    
    technicians_df = pd.read_sql(technicians_query, conn, params=[store_id])
    
    if technicians_df.empty:
        st.info("No technicians assigned to this store.")
        return
    
    # Now get performance data for each technician
    performance_data = []
    
    for _, tech in technicians_df.iterrows():
        # Get assignments for this technician in the date range
        assignments_query = """
            SELECT 
                ta.id as assignment_id,
                ta.status as assignment_status,
                COUNT(DISTINCT aj.job_id) as jobs_in_assignment,
                SUM(CASE WHEN j.status = 'Completed' THEN 1 ELSE 0 END) as completed_jobs,
                SUM(CASE WHEN j.status = 'Completed' THEN COALESCE(j.actual_cost, 0) ELSE 0 END) as revenue_generated
            FROM technician_assignments ta
            LEFT JOIN assignment_jobs aj ON ta.id = aj.assignment_id
            LEFT JOIN jobs j ON aj.job_id = j.id AND j.store_id = ?
            WHERE ta.technician_id = ?
                AND ta.assigned_at BETWEEN ? AND ?
            GROUP BY ta.id, ta.status
        """
        
        tech_assignments = pd.read_sql(assignments_query, conn, 
                                     params=[store_id, tech['id'], params[0], params[1]])
        
        # Calculate totals for this technician
        total_assignments = len(tech_assignments)
        completed_assignments = len(tech_assignments[tech_assignments['assignment_status'] == 'completed'])
        total_jobs = tech_assignments['jobs_in_assignment'].sum() if not tech_assignments.empty else 0
        completed_jobs = tech_assignments['completed_jobs'].sum() if not tech_assignments.empty else 0
        revenue_generated = tech_assignments['revenue_generated'].sum() if not tech_assignments.empty else 0
        
        performance_data.append({
            'id': tech['id'],
            'full_name': tech['full_name'],
            'email': tech['email'],
            'total_assignments': total_assignments,
            'completed_assignments': completed_assignments,
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'revenue_generated': revenue_generated
        })
    
    team_data = pd.DataFrame(performance_data)
    
    if not team_data.empty and team_data['total_assignments'].sum() > 0:
        st.markdown("#### Team Performance")
        
        # Calculate completion rates safely
        team_data['assignment_completion_rate'] = team_data.apply(
            lambda row: (row['completed_assignments'] / row['total_assignments'] * 100) 
            if row['total_assignments'] > 0 else 0, axis=1
        ).round(1)
        
        team_data['job_completion_rate'] = team_data.apply(
            lambda row: (row['completed_jobs'] / row['total_jobs'] * 100) 
            if row['total_jobs'] > 0 else 0, axis=1
        ).round(1)
        
        team_data['revenue_generated'] = team_data['revenue_generated'].fillna(0).round(2)
        
        # Display team data
        display_data = team_data[['full_name', 'total_assignments', 'completed_assignments', 
                                 'assignment_completion_rate', 'total_jobs', 'completed_jobs',
                                 'job_completion_rate', 'revenue_generated']].copy()
        display_data.columns = ['Technician', 'Total Assignments', 'Completed Assignments', 
                               'Assignment Rate (%)', 'Total Jobs', 'Completed Jobs',
                               'Job Completion Rate (%)', 'Revenue Generated (₹)']
        
        st.dataframe(display_data, use_container_width=True)
        
        # Team performance visualization
        if len(team_data) > 1:
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(team_data, x='full_name', y='revenue_generated',
                            title="Revenue Generated by Team Members", 
                            color='job_completion_rate',
                            color_continuous_scale='viridis')
                fig.update_layout(xaxis_title="Technician Name", yaxis_title="Revenue (₹)")
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(team_data, x='full_name', y='total_jobs',
                            title="Jobs Assigned vs Completed", 
                            color='completed_jobs',
                            color_continuous_scale='blues')
                fig.update_layout(xaxis_title="Technician Name", yaxis_title="Number of Jobs")
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No technician performance data available for the selected period.")


def customer_management(conn, where_clause, params, store_id):
    """Customer management analytics for managers - CORRECTED VERSION"""
    
    # Get customers with jobs in the specified date range for this store
    customer_query = """
        SELECT 
            c.id,
            c.name as customer_name,
            c.phone,
            c.email,
            COUNT(j.id) as total_jobs,
            SUM(CASE WHEN j.status = 'Completed' THEN COALESCE(j.actual_cost, 0) ELSE 0 END) as total_spent,
            SUM(CASE WHEN j.status = 'Completed' THEN 1 ELSE 0 END) as completed_jobs,
            SUM(CASE WHEN j.status IN ('Pending', 'In Progress') THEN 1 ELSE 0 END) as active_jobs,
            MAX(j.created_at) as last_visit,
            MIN(j.created_at) as first_visit
        FROM customers c
        JOIN jobs j ON c.id = j.customer_id
        WHERE j.store_id = ? AND j.created_at BETWEEN ? AND ?
        GROUP BY c.id, c.name, c.phone, c.email
        ORDER BY total_spent DESC
        LIMIT 20
    """
    
    customers = pd.read_sql(customer_query, conn, params=[store_id, params[0], params[1]])
    
    if not customers.empty:
        st.markdown("#### Top Customers This Period")
        
        # Format the data for display
        customers['total_spent'] = customers['total_spent'].fillna(0).round(2)
        customers['last_visit'] = pd.to_datetime(customers['last_visit']).dt.strftime('%Y-%m-%d')
        customers['first_visit'] = pd.to_datetime(customers['first_visit']).dt.strftime('%Y-%m-%d')
        
        # Calculate customer loyalty metrics
        customers['avg_job_value'] = customers.apply(
            lambda row: row['total_spent'] / row['completed_jobs'] if row['completed_jobs'] > 0 else 0, 
            axis=1
        ).round(2)
        
        # Display customer summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Customers", len(customers))
        with col2:
            st.metric("Total Revenue", f"₹{customers['total_spent'].sum():,.2f}")
        with col3:
            st.metric("Avg Customer Value", f"₹{customers['total_spent'].mean():,.2f}")
        with col4:
            st.metric("Repeat Customers", len(customers[customers['total_jobs'] > 1]))
        
        # Rename columns for better display
        display_customers = customers[['customer_name', 'phone', 'total_jobs', 'completed_jobs',
                                     'active_jobs', 'total_spent', 'avg_job_value', 'last_visit']].copy()
        display_customers.columns = ['Customer Name', 'Phone', 'Total Jobs', 'Completed Jobs',
                                   'Active Jobs', 'Total Spent (₹)', 'Avg Job Value (₹)', 'Last Visit']
        
        st.dataframe(display_customers, use_container_width=True)
        
        # Customer analytics charts
        if len(customers) > 1:
            col1, col2 = st.columns(2)
            
            with col1:
                # Top customers by revenue
                top_customers = customers.head(10)
                fig = px.bar(top_customers, x='customer_name', y='total_spent',
                            title="Top 10 Customers by Revenue", 
                            color='total_jobs',
                            color_continuous_scale='blues')
                fig.update_layout(xaxis_title="Customer Name", yaxis_title="Total Spent (₹)")
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Customer job completion rate
                fig = px.scatter(customers, x='total_jobs', y='total_spent',
                               size='avg_job_value', hover_name='customer_name',
                               title="Customer Value Analysis",
                               labels={'total_jobs': 'Total Jobs', 'total_spent': 'Total Spent (₹)'})
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No customer data available for the selected period.")


def revenue_analysis(conn, where_clause, params):
    """Detailed revenue analysis - CORRECTED VERSION"""
    
    # Revenue by device type for completed jobs only
    device_revenue_query = f"""
        SELECT 
            device_type,
            COUNT(*) as job_count,
            SUM(COALESCE(actual_cost, 0)) as total_revenue,
            AVG(COALESCE(actual_cost, 0)) as avg_revenue,
            MIN(COALESCE(actual_cost, 0)) as min_revenue,
            MAX(COALESCE(actual_cost, 0)) as max_revenue
        FROM jobs j
        WHERE {where_clause} AND status = 'Completed' AND actual_cost > 0
        GROUP BY device_type
        ORDER BY total_revenue DESC
    """
    
    device_revenue = pd.read_sql(device_revenue_query, conn, params=params)
    
    # Daily revenue trend
    daily_revenue_query = f"""
        SELECT 
            DATE(j.created_at) as job_date,
            COUNT(*) as jobs_count,
            SUM(CASE WHEN status = 'Completed' THEN COALESCE(actual_cost, 0) ELSE 0 END) as daily_revenue,
            COUNT(CASE WHEN status = 'Completed' THEN 1 END) as completed_jobs
        FROM jobs j
        WHERE {where_clause}
        GROUP BY DATE(j.created_at)
        ORDER BY job_date
    """
    
    daily_revenue = pd.read_sql(daily_revenue_query, conn, params=params)
    
    if not device_revenue.empty:
        st.markdown("#### Revenue Analysis by Device Type")
        
        # Clean and format data
        device_revenue['total_revenue'] = device_revenue['total_revenue'].fillna(0).round(2)
        device_revenue['avg_revenue'] = device_revenue['avg_revenue'].fillna(0).round(2)
        device_revenue['min_revenue'] = device_revenue['min_revenue'].fillna(0).round(2)
        device_revenue['max_revenue'] = device_revenue['max_revenue'].fillna(0).round(2)
        
        # Display summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Revenue", f"₹{device_revenue['total_revenue'].sum():,.2f}")
        with col2:
            st.metric("Completed Jobs", f"{device_revenue['job_count'].sum():,}")
        with col3:
            st.metric("Avg Job Value", f"₹{device_revenue['total_revenue'].sum() / device_revenue['job_count'].sum():,.2f}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.pie(device_revenue, values='total_revenue', names='device_type',
                        title="Revenue Distribution by Device Type")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(device_revenue, x='device_type', y='avg_revenue',
                        title="Average Revenue per Device Type", 
                        color='job_count',
                        color_continuous_scale='viridis')
            fig.update_layout(xaxis_title="Device Type", yaxis_title="Average Revenue (₹)")
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        
        # Summary table
        st.markdown("#### Device Type Summary")
        summary_data = device_revenue.copy()
        summary_data.columns = ['Device Type', 'Job Count', 'Total Revenue (₹)', 
                               'Avg Revenue (₹)', 'Min Revenue (₹)', 'Max Revenue (₹)']
        st.dataframe(summary_data, use_container_width=True)
        
        # Daily revenue trend
        if not daily_revenue.empty and len(daily_revenue) > 1:
            st.markdown("#### Daily Revenue Trend")
            daily_revenue['job_date'] = pd.to_datetime(daily_revenue['job_date'])
            
            fig = px.line(daily_revenue, x='job_date', y='daily_revenue',
                         title="Daily Revenue Trend",
                         markers=True)
            fig.update_layout(xaxis_title="Date", yaxis_title="Revenue (₹)")
            st.plotly_chart(fig, use_container_width=True)
            
            # Show daily summary
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Best Day Revenue", f"₹{daily_revenue['daily_revenue'].max():,.2f}")
            with col2:
                st.metric("Average Daily Revenue", f"₹{daily_revenue['daily_revenue'].mean():,.2f}")
    
    else:
        st.info("No completed jobs with revenue data available for the selected period.")


# Additional helper function for better error handling
def safe_sql_query(conn, query, params=None, default_value=None):
    """Safely execute SQL query with error handling"""
    try:
        result = pd.read_sql(query, conn, params=params)
        return result if not result.empty else default_value
    except Exception as e:
        st.error(f"Database query error: {str(e)}")
        return default_value