import sys 
import os 
import pandas as pd 
import streamlit as st
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.css.css import Style
from components.datamanager.databasemanger import DatabaseManager
from components.utils.auth import hash_password , verify_password,authenticate_user , create_user
from pages.screens.loginpage import login_signup_page
from pages.screens.admindashboard import admin_dashboard
from components.sidebarnavigation import sidebar_navigation

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