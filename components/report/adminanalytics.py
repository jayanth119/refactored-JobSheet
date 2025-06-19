import sys 
import os 
import pandas as pd 
import streamlit as st
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io 
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def validate_numeric_data(df, numeric_columns):
    """Ensure specified columns are numeric, converting if necessary"""
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def admin_analytics(conn, start_date_str, end_date_str, user):
    """Complete business analytics for admin users - all stores overview"""
    
    st.markdown("### 🏢 Multi-Store Business Overview")
    
    # Store selector for detailed analysis
    stores = pd.read_sql("SELECT id, name, location FROM stores", conn)
    store_options = dict(zip(stores['name'], stores['id']))
    selected_store = st.selectbox("Focus on Store (Optional)", ["All Stores"] + list(store_options.keys()))
    
    # Build query conditions
    date_condition = "j.created_at BETWEEN ? AND ?"
    params = [start_date_str, end_date_str]
    
    if selected_store != "All Stores":
        store_condition = "j.store_id = ?"
        params.append(store_options[selected_store])
        where_clause = f"{date_condition} AND {store_condition}"
    else:
        where_clause = date_condition
    
    # Create tabs for different analytics
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Executive Dashboard", 
        "🏪 Store Performance", 
        "👥 Customer Analytics", 
        "🔧 Operations Analysis",
        "📈 Financial Deep Dive"
    ])
    
    with tab1:
        executive_dashboard(conn, where_clause, params, selected_store)
    
    with tab2:
        store_performance_analysis(conn, start_date_str, end_date_str)
    
    with tab3:
        customer_analytics(conn, where_clause, params)
    
    with tab4:
        operations_analysis(conn, where_clause, params)
    
    with tab5:
        financial_deep_dive(conn, where_clause, params)


def executive_dashboard(conn, where_clause, params, selected_store):
    """Executive level KPIs and metrics"""
    
    # Key Performance Indicators
    kpi_query = f"""
        SELECT 
            COUNT(*) as total_jobs,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_jobs,
            SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as in_progress_jobs,
            SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_jobs,
            SUM(CASE WHEN status = 'Completed' THEN actual_cost ELSE 0 END) as total_revenue,
            AVG(CASE WHEN status = 'Completed' THEN actual_cost ELSE NULL END) as avg_job_value,
            COUNT(DISTINCT j.customer_id) as unique_customers,
            COUNT(DISTINCT j.store_id) as active_stores
        FROM jobs j
        WHERE {where_clause}
    """
    
    kpis = pd.read_sql(kpi_query, conn, params=params).iloc[0]
    kpis = validate_numeric_data(pd.DataFrame([kpis]), kpis.keys()).iloc[0]
    
    # Display KPIs in columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Jobs", f"{kpis['total_jobs']:,}")
        completion_rate = (kpis['completed_jobs'] / kpis['total_jobs'] * 100) if kpis['total_jobs'] > 0 else 0
        st.metric("Completion Rate", f"{completion_rate:.1f}%")
    
    with col2:
        revenue = kpis['total_revenue'] if kpis['total_revenue'] is not None else 0
        st.metric("Total Revenue", f"₹{revenue:,.2f}")
        avg_value = kpis['avg_job_value'] if kpis['avg_job_value'] is not None else 0
        st.metric("Avg. Job Value", f"₹{avg_value:,.2f}")
    
    with col3:
        st.metric("Unique Customers", f"{kpis['unique_customers']:,}")
        st.metric("Active Stores", f"{kpis['active_stores']:,}")
    
    with col4:
        st.metric("In Progress", f"{kpis['in_progress_jobs']:,}")
        st.metric("Pending", f"{kpis['pending_jobs']:,}")
    
    st.markdown("---")
    
    # Revenue trend analysis
    revenue_trend_query = f"""
        SELECT 
            strftime('%Y-%m-%d', j.created_at) as date,
            SUM(CASE WHEN status = 'Completed' THEN actual_cost ELSE 0 END) as daily_revenue,
            COUNT(*) as jobs_created,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as jobs_completed
        FROM jobs j
        WHERE {where_clause}
        GROUP BY strftime('%Y-%m-%d', j.created_at)
        ORDER BY date
    """
    
    revenue_trend = pd.read_sql(revenue_trend_query, conn, params=params)
    revenue_trend = validate_numeric_data(revenue_trend, ['daily_revenue', 'jobs_created', 'jobs_completed'])
    
    if not revenue_trend.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            try:
                fig = px.line(revenue_trend, x='date', y='daily_revenue',
                             title="Daily Revenue Trend", markers=True)
                fig.update_layout(xaxis_title="Date", yaxis_title="Revenue (₹)")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating revenue trend chart: {str(e)}")
        
        with col2:
            try:
                fig = px.bar(revenue_trend, x='date', y='jobs_created',
                            title="Daily Job Creation", color='jobs_completed')
                fig.update_layout(xaxis_title="Date", yaxis_title="Number of Jobs")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating job creation chart: {str(e)}")

def store_performance_analysis(conn, start_date_str, end_date_str):
    """Detailed store-by-store performance comparison"""
    
    store_performance_query = f"""
        SELECT 
            s.name as store_name,
            s.location,
            COUNT(j.id) as total_jobs,
            SUM(CASE WHEN j.status = 'Completed' THEN 1 ELSE 0 END) as completed_jobs,
            SUM(CASE WHEN j.status = 'Completed' THEN j.actual_cost ELSE 0 END) as total_revenue,
            AVG(CASE WHEN j.status = 'Completed' THEN j.actual_cost ELSE NULL END) as avg_job_value,
            COUNT(DISTINCT j.customer_id) as unique_customers
        FROM stores s
        LEFT JOIN jobs j ON s.id = j.store_id AND j.created_at BETWEEN ? AND ?
        GROUP BY s.id, s.name, s.location
        ORDER BY total_revenue DESC
    """
    
    store_data = pd.read_sql(store_performance_query, conn, params=[start_date_str, end_date_str])
    store_data = validate_numeric_data(store_data, ['total_jobs', 'completed_jobs', 'total_revenue', 'avg_job_value'])
    
    if not store_data.empty:
        # Store performance comparison
        col1, col2 = st.columns(2)
        
        with col1:
            try:
                fig = px.bar(store_data, x='store_name', y='total_revenue',
                            title="Revenue by Store", color='total_revenue')
                fig.update_layout(xaxis_title="Store", yaxis_title="Revenue (₹)")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating revenue by store chart: {str(e)}")
        
        with col2:
            try:
                fig = px.scatter(store_data, x='total_jobs', y='total_revenue',
                               size='unique_customers', hover_name='store_name',
                               title="Jobs vs Revenue (bubble size = customers)")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating jobs vs revenue chart: {str(e)}")
        
        # Store performance table
        st.markdown("#### Store Performance Summary")
        store_data['completion_rate'] = (store_data['completed_jobs'] / store_data['total_jobs'] * 100).round(1)
        store_data['avg_job_value'] = store_data['avg_job_value'].round(2)
        store_data['total_revenue'] = store_data['total_revenue'].round(2)
        
        st.dataframe(store_data[['store_name', 'location', 'total_jobs', 'completed_jobs', 
                                'completion_rate', 'total_revenue', 'avg_job_value', 'unique_customers']])

def customer_analytics(conn, where_clause, params):
    """Customer behavior and loyalty analysis"""
    
    # Top customers by revenue
    top_customers_query = f"""
        SELECT 
            c.name as customer_name,
            c.phone,
            c.email,
            COUNT(j.id) as total_jobs,
            SUM(CASE WHEN j.status = 'Completed' THEN j.actual_cost ELSE 0 END) as total_spent,
            AVG(CASE WHEN j.status = 'Completed' THEN j.actual_cost ELSE NULL END) as avg_job_value,
            s.name as preferred_store
        FROM customers c
        JOIN jobs j ON c.id = j.customer_id
        LEFT JOIN stores s ON j.store_id = s.id
        WHERE {where_clause}
        GROUP BY c.id, c.name, c.phone, c.email, s.name
        ORDER BY total_spent DESC
        LIMIT 20
    """
    
    top_customers = pd.read_sql(top_customers_query, conn, params=params)
    top_customers = validate_numeric_data(top_customers, ['total_jobs', 'total_spent', 'avg_job_value'])
    
    if not top_customers.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            try:
                fig = px.bar(top_customers.head(10), x='customer_name', y='total_spent',
                            title="Top 10 Customers by Revenue", color='total_jobs')
                fig.update_layout(xaxis={'tickangle': 45})
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating top customers chart: {str(e)}")
        
        with col2:
            try:
                # Customer loyalty analysis
                customer_segments = top_customers.copy()
                customer_segments['segment'] = pd.cut(customer_segments['total_jobs'], 
                                                    bins=[0, 1, 3, 5, float('inf')], 
                                                    labels=['One-time', 'Occasional', 'Regular', 'Loyal'])
                
                segment_counts = customer_segments['segment'].value_counts()
                fig = px.pie(values=segment_counts.values, names=segment_counts.index,
                            title="Customer Loyalty Segments")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating customer segments chart: {str(e)}")
        
        st.markdown("#### Top Customers Details")
        st.dataframe(top_customers)


def operations_analysis(conn, where_clause, params):
    """Operations and workflow analysis"""
    
    # Job status flow analysis
    status_flow_query = f"""
        SELECT 
            status,
            COUNT(*) as count,
            AVG(CASE 
                WHEN completed_at IS NOT NULL AND created_at IS NOT NULL 
                THEN (julianday(completed_at) - julianday(created_at)) * 24 
                ELSE NULL 
            END) as avg_completion_hours
        FROM jobs j
        WHERE {where_clause}
        GROUP BY status
        ORDER BY count DESC
    """
    
    status_data = pd.read_sql(status_flow_query, conn, params=params)
    
    if not status_data.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.funnel(status_data, x='count', y='status',
                           title="Job Status Flow")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Completion time analysis
            completed_data = status_data[status_data['avg_completion_hours'].notna()]
            if not completed_data.empty:
                fig = px.bar(completed_data, x='status', y='avg_completion_hours',
                            title="Average Completion Time by Status")
                st.plotly_chart(fig, use_container_width=True)

def financial_deep_dive(conn, where_clause, params):
    """Deep financial analysis for admin users"""
    
    # Monthly revenue trend
    monthly_revenue_query = f"""
        SELECT 
            strftime('%Y-%m', j.created_at) as month,
            COUNT(*) as total_jobs,
            SUM(CASE WHEN status = 'Completed' THEN actual_cost ELSE 0 END) as revenue,
            SUM(CASE WHEN status = 'Completed' THEN raw_cost ELSE 0 END) as cost,
            SUM(CASE WHEN status = 'Completed' THEN (actual_cost - raw_cost) ELSE 0 END) as profit
        FROM jobs j
        WHERE {where_clause} AND status = 'Completed'
        GROUP BY strftime('%Y-%m', j.created_at)
        ORDER BY month
    """
    
    monthly_data = pd.read_sql(monthly_revenue_query, conn, params=params)
    
    if not monthly_data.empty:
        st.markdown("#### Monthly Financial Performance")
        
        # Calculate profit margins
        monthly_data['profit_margin'] = ((monthly_data['profit'] / monthly_data['revenue']) * 100).round(2)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=monthly_data['month'], y=monthly_data['revenue'], 
                                name='Revenue', marker_color='lightblue'))
            fig.add_trace(go.Bar(x=monthly_data['month'], y=monthly_data['cost'], 
                                name='Cost', marker_color='lightcoral'))
            fig.add_trace(go.Bar(x=monthly_data['month'], y=monthly_data['profit'], 
                                name='Profit', marker_color='lightgreen'))
            
            fig.update_layout(title='Monthly Revenue, Cost & Profit',
                            xaxis_title='Month', yaxis_title='Amount (₹)',
                            barmode='group')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.line(monthly_data, x='month', y='profit_margin',
                         title='Monthly Profit Margin %', markers=True)
            fig.update_layout(xaxis_title='Month', yaxis_title='Profit Margin (%)')
            st.plotly_chart(fig, use_container_width=True)
        
        # Financial summary table
        st.markdown("#### Financial Summary")
        financial_summary = monthly_data[['month', 'total_jobs', 'revenue', 'cost', 'profit', 'profit_margin']]
        financial_summary.columns = ['Month', 'Jobs', 'Revenue (₹)', 'Cost (₹)', 'Profit (₹)', 'Profit Margin (%)']
        st.dataframe(financial_summary)
        
        # Overall financial metrics
        total_revenue = monthly_data['revenue'].sum()
        total_cost = monthly_data['cost'].sum()
        total_profit = total_revenue - total_cost
        overall_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Revenue", f"₹{total_revenue:,.2f}")
        with col2:
            st.metric("Total Cost", f"₹{total_cost:,.2f}")
        with col3:
            st.metric("Total Profit", f"₹{total_profit:,.2f}")
        with col4:
            st.metric("Overall Margin", f"{overall_margin:.2f}%")
