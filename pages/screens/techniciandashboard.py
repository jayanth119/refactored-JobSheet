import sys
import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager

def technician_dashboard():
    user = st.session_state.user
    
    # Header
    st.markdown(f'''
        <div class="main-header">
            <h1>🔧 Technician Dashboard</h1>
            <p>Welcome back, {user['full_name']} | {user['store_name']}</p>
        </div>
    ''', unsafe_allow_html=True)
    
    # Database
    db = DatabaseManager()
    conn = db.get_connection()
    
    # === Key Metrics ===
    col1, col2, col3, col4 = st.columns(4)
    
    # Get technician's assigned jobs
    assigned_jobs = pd.read_sql("""
        SELECT COUNT(*) as count 
        FROM technician_assignments ta
        JOIN assignment_jobs aj ON ta.id = aj.assignment_id
        WHERE ta.technician_id = ? AND ta.status = 'active'
    """, conn, params=[user['id']]).iloc[0]['count']
    
    # Jobs in progress
    in_progress_jobs = pd.read_sql("""
        SELECT COUNT(*) as count 
        FROM jobs j
        JOIN assignment_jobs aj ON j.id = aj.job_id
        JOIN technician_assignments ta ON aj.assignment_id = ta.id
        WHERE ta.technician_id = ? AND j.status = 'In Progress'
    """, conn, params=[user['id']]).iloc[0]['count']
    
    # Jobs completed today
    completed_today = pd.read_sql("""
        SELECT COUNT(*) as count 
        FROM jobs j
        JOIN assignment_jobs aj ON j.id = aj.job_id
        JOIN technician_assignments ta ON aj.assignment_id = ta.id
        WHERE ta.technician_id = ? AND j.status = 'Completed' 
        AND DATE(j.completed_at) = DATE('now')
    """, conn, params=[user['id']]).iloc[0]['count']
    
    # Total completed jobs
    total_completed = pd.read_sql("""
        SELECT COUNT(*) as count 
        FROM jobs j
        JOIN assignment_jobs aj ON j.id = aj.job_id
        JOIN technician_assignments ta ON aj.assignment_id = ta.id
        WHERE ta.technician_id = ? AND j.status = 'Completed'
    """, conn, params=[user['id']]).iloc[0]['count']
    
    with col1:
        st.markdown(f'''
            <div class="metric-card">
                <div class="metric-number">{assigned_jobs}</div>
                <div class="metric-label">Assigned Jobs</div>
            </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f'''
            <div class="metric-card">
                <div class="metric-number">{in_progress_jobs}</div>
                <div class="metric-label">In Progress</div>
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
                <div class="metric-number">{total_completed}</div>
                <div class="metric-label">Total Completed</div>
            </div>
        ''', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # === Tabs ===
    tab1, tab2, tab4, tab5 = st.tabs(["🎯 My Jobs", "📊 Performance", "📈 Analytics", "📝 Job History"])
    
    with tab1:
        st.markdown("### My Current Jobs")
        
        # Get current assignments
        current_jobs = pd.read_sql("""
            SELECT j.id, j.device_type, j.device_model, j.problem_description,
                   j.status, j.created_at, j.actual_cost, j.deposit_cost,
                   c.name as customer_name, c.phone as customer_phone,
                   ta.assigned_at, ta.started_at, ta.notes as assignment_notes
            FROM jobs j
            JOIN customers c ON j.customer_id = c.id
            JOIN assignment_jobs aj ON j.id = aj.job_id
            JOIN technician_assignments ta ON aj.assignment_id = ta.id
            WHERE ta.technician_id = ? AND ta.status = 'active'
            ORDER BY 
                CASE j.status 
                    WHEN 'In Progress' THEN 1
                    WHEN 'New' THEN 2
                    WHEN 'Pending' THEN 3
                    ELSE 4
                END,
                j.created_at ASC
        """, conn, params=[user['id']])
        
        if not current_jobs.empty:
            for _, job in current_jobs.iterrows():
                status_color = {
                    'New': '🔵',
                    'In Progress': '🟡',
                    'Pending': '🟠',
                    'Completed': '🟢'
                }.get(job['status'], '⚪')
                
                with st.expander(f"{status_color} Job #{job['id']} - {job['device_type']} {job['device_model']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Job Details**")
                        st.write(f"**Customer:** {job['customer_name']}")
                        st.write(f"**Phone:** {job['customer_phone']}")
                        st.write(f"**Device:** {job['device_type']} {job['device_model']}")
                        st.write(f"**Problem:** {job['problem_description']}")
                        st.write(f"**Status:** {job['status']}")
                        st.write(f"**Created:** {job['created_at'][:16]}")
                        
                        if job['assignment_notes']:
                            st.write(f"**Notes:** {job['assignment_notes']}")
                    
                    with col2:
                        st.markdown("**Actions**")
                        
                        # Status update buttons
                        # if job['status'] == 'New':
                        #     if st.button(f"🚀 Start Job #{job['id']}", key=f"start_{job['id']}"):
                        #         update_job_status(conn, job['id'], 'In Progress', user['id'])
                        #         st.rerun()
                        
                        # elif job['status'] == 'In Progress':
                        #     if st.button(f"✅ Complete Job #{job['id']}", key=f"complete_{job['id']}"):
                        #         update_job_status(conn, job['id'], 'Completed', user['id'])
                        #         st.rerun()
                            
                        #     if st.button(f"⏸️ Set Pending #{job['id']}", key=f"pending_{job['id']}"):
                        #         update_job_status(conn, job['id'], 'Pending', user['id'])
                        #         st.rerun()
                        
                        # elif job['status'] == 'Pending':
                        #     if st.button(f"🔄 Resume Job #{job['id']}", key=f"resume_{job['id']}"):
                        #         update_job_status(conn, job['id'], 'In Progress', user['id'])
                        #         st.rerun()
                        
                        # Add job notes
                        # with st.form(f"notes_form_{job['id']}"):
                        #     new_note = st.text_area("Add Note", key=f"note_{job['id']}")
                        #     if st.form_submit_button("Add Note"):
                        #         if new_note:
                        #             add_job_note(conn, job['id'], new_note)
                        #             st.success("Note added!")
                        #             st.rerun()
        else:
            st.info("No jobs currently assigned to you.")
    
    with tab2:
        st.markdown("### My Performance")
        
        # Performance metrics
        perf_data = pd.read_sql("""
            SELECT 
                COUNT(*) as total_jobs,
                COUNT(CASE WHEN j.status = 'Completed' THEN 1 END) as completed_jobs,
                AVG(CASE WHEN j.status = 'Completed' AND j.started_at IS NOT NULL AND j.completed_at IS NOT NULL
                    THEN (julianday(j.completed_at) - julianday(j.started_at)) END) as avg_completion_time,
                AVG(CASE WHEN j.status = 'Completed' THEN j.actual_cost END) as avg_job_value,
                SUM(CASE WHEN j.status = 'Completed' THEN j.actual_cost ELSE 0 END) as total_revenue
            FROM jobs j
            JOIN assignment_jobs aj ON j.id = aj.job_id
            JOIN technician_assignments ta ON aj.assignment_id = ta.id
            WHERE ta.technician_id = ?
        """, conn, params=[user['id']])
        
        if not perf_data.empty and perf_data.iloc[0]['total_jobs'] > 0:
            metrics = perf_data.iloc[0]
            completion_rate = (metrics['completed_jobs'] / metrics['total_jobs']) * 100 if metrics['total_jobs'] > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Completion Rate", f"{completion_rate:.1f}%")
                st.metric("Average Job Value", f"${metrics['avg_job_value']:.2f}" if metrics['avg_job_value'] else "N/A")
            
            with col2:
                st.metric("Total Revenue Generated", f"${metrics['total_revenue']:.2f}")
                st.metric("Average Completion Time", f"{metrics['avg_completion_time']:.1f} days" if metrics['avg_completion_time'] else "N/A")
            
            with col3:
                st.metric("Total Jobs", int(metrics['total_jobs']))
                st.metric("Completed Jobs", int(metrics['completed_jobs']))
            
            # Monthly performance chart
            monthly_perf = pd.read_sql("""
                SELECT strftime('%Y-%m', j.completed_at) as month,
                       COUNT(*) as completed_jobs,
                       SUM(j.actual_cost) as revenue
                FROM jobs j
                JOIN assignment_jobs aj ON j.id = aj.job_id
                JOIN technician_assignments ta ON aj.assignment_id = ta.id
                WHERE ta.technician_id = ? AND j.status = 'Completed'
                  AND j.completed_at >= date('now', '-12 months')
                GROUP BY strftime('%Y-%m', j.completed_at)
                ORDER BY month
            """, conn, params=[user['id']])
            
            if not monthly_perf.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.line(monthly_perf, x='month', y='completed_jobs',
                                title="Monthly Completed Jobs", markers=True)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    fig = px.bar(monthly_perf, x='month', y='revenue',
                               title="Monthly Revenue Generated")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No performance data available yet.")
    
    # with tab3:
    #     pass 
        # st.markdown("### Quick Actions")
        
        # col1, col2 = st.columns(2)
        
        # with col1:
        #     st.markdown("#### Job Status Updates")
            
        #     # Quick status updates for multiple jobs
        #     pending_jobs = pd.read_sql("""
        #         SELECT j.id, j.device_type, j.device_model, c.name as customer_name
        #         FROM jobs j
        #         JOIN customers c ON j.customer_id = c.id
        #         JOIN assignment_jobs aj ON j.id = aj.job_id
        #         JOIN technician_assignments ta ON aj.assignment_id = ta.id
        #         WHERE ta.technician_id = ? AND j.status IN ('New', 'In Progress', 'Pending')
        #         ORDER BY j.created_at
        #     """, conn, params=[user['id']])
            
        #     if not pending_jobs.empty:
        #         for _, job in pending_jobs.iterrows():
        #             col_a, col_b, col_c = st.columns([2, 1, 1])
        #             with col_a:
        #                 st.write(f"#{job['id']} - {job['customer_name']}")
        #                 st.caption(f"{job['device_type']} {job['device_model']}")
                    
        #             with col_b:
        #                 if st.button("▶️ Start", key=f"quick_start_{job['id']}"):
        #                     update_job_status(conn, job['id'], 'In Progress', user['id'])
        #                     st.rerun()
                    
        #             with col_c:
        #                 if st.button("✅ Done", key=f"quick_complete_{job['id']}"):
        #                     update_job_status(conn, job['id'], 'Completed', user['id'])
        #                     st.rerun()
        #     else:
        #         st.info("No pending jobs")
        
        # with col2:
        #     st.markdown("#### Today's Summary")
            
        #     today_summary = pd.read_sql("""
        #         SELECT 
        #             j.status,
        #             COUNT(*) as count
        #         FROM jobs j
        #         JOIN assignment_jobs aj ON j.id = aj.job_id
        #         JOIN technician_assignments ta ON aj.assignment_id = ta.id
        #         WHERE ta.technician_id = ? 
        #           AND DATE(j.created_at) = DATE('now')
        #         GROUP BY j.status
        #     """, conn, params=[user['id']])
            
        #     if not today_summary.empty:
        #         for _, row in today_summary.iterrows():
        #             st.metric(f"{row['status']} Jobs", int(row['count']))
        #     else:
        #         st.info("No jobs today")
    
    with tab4:
        st.markdown("### My Analytics")
        
        # Device type specialization
        device_stats = pd.read_sql("""
            SELECT j.device_type,
                   COUNT(*) as job_count,
                   COUNT(CASE WHEN j.status = 'Completed' THEN 1 END) as completed,
                   AVG(CASE WHEN j.status = 'Completed' THEN j.actual_cost END) as avg_revenue
            FROM jobs j
            JOIN assignment_jobs aj ON j.id = aj.job_id
            JOIN technician_assignments ta ON aj.assignment_id = ta.id
            WHERE ta.technician_id = ? AND j.device_type IS NOT NULL
            GROUP BY j.device_type
            ORDER BY job_count DESC
        """, conn, params=[user['id']])
        
        if not device_stats.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Device Specialization")
                fig = px.pie(device_stats, values='job_count', names='device_type',
                           title="Jobs by Device Type")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### Revenue by Device Type")
                fig = px.bar(device_stats, x='device_type', y='avg_revenue',
                           title="Average Revenue per Device Type")
                st.plotly_chart(fig, use_container_width=True)
            
            # Weekly performance
            weekly_perf = pd.read_sql("""
                SELECT strftime('%W', j.completed_at) as week,
                       COUNT(*) as completed_jobs
                FROM jobs j
                JOIN assignment_jobs aj ON j.id = aj.job_id
                JOIN technician_assignments ta ON aj.assignment_id = ta.id
                WHERE ta.technician_id = ? AND j.status = 'Completed'
                  AND j.completed_at >= date('now', '-8 weeks')
                GROUP BY strftime('%W', j.completed_at)
                ORDER BY week
            """, conn, params=[user['id']])
            
            if not weekly_perf.empty:
                st.markdown("#### Weekly Performance Trend")
                fig = px.line(weekly_perf, x='week', y='completed_jobs',
                            title="Jobs Completed per Week", markers=True)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No analytics data available yet.")
    
    with tab5:
        st.markdown("### Job History")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Filter by Status", 
                                       ['All', 'Completed', 'In Progress', 'Pending', 'New'])
        with col2:
            days_filter = st.selectbox("Time Period", 
                                     ['Last 7 days', 'Last 30 days', 'Last 90 days', 'All time'])
        with col3:
            device_filter = st.selectbox("Device Type", ['All'] + 
                                       pd.read_sql("SELECT DISTINCT device_type FROM jobs WHERE device_type IS NOT NULL", conn)['device_type'].tolist())
        
        # Build query based on filters
        where_conditions = ["ta.technician_id = ?"]
        params = [user['id']]
        
        if status_filter != 'All':
            where_conditions.append("j.status = ?")
            params.append(status_filter)
        
        if days_filter != 'All time':
            days = {'Last 7 days': 7, 'Last 30 days': 30, 'Last 90 days': 90}[days_filter]
            where_conditions.append("j.created_at >= date('now', '-{} days')".format(days))
        
        if device_filter != 'All':
            where_conditions.append("j.device_type = ?")
            params.append(device_filter)
        
        history_query = f"""
            SELECT j.id, j.device_type, j.device_model, j.problem_description,
                   j.status, j.created_at, j.completed_at, j.actual_cost,
                   c.name as customer_name, c.phone as customer_phone
            FROM jobs j
            JOIN customers c ON j.customer_id = c.id
            JOIN assignment_jobs aj ON j.id = aj.job_id
            JOIN technician_assignments ta ON aj.assignment_id = ta.id
            WHERE {' AND '.join(where_conditions)}
            ORDER BY j.created_at DESC
            LIMIT 50
        """
        
        job_history = pd.read_sql(history_query, conn, params=params)
        
        if not job_history.empty:
            # Display as a table with better formatting
            display_df = job_history.copy()
            display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            display_df['completed_at'] = pd.to_datetime(display_df['completed_at']).dt.strftime('%Y-%m-%d %H:%M')
            display_df['actual_cost'] = display_df['actual_cost'].fillna(0).round(2)
            
            st.dataframe(
                display_df,
                column_config={
                    "id": "Job ID",
                    "device_type": "Device",
                    "device_model": "Model",
                    "customer_name": "Customer",
                    "customer_phone": "Phone",
                    "status": "Status",
                    "created_at": "Created",
                    "completed_at": "Completed",
                    "actual_cost": st.column_config.NumberColumn("Cost", format="$%.2f")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No job history found with the selected filters.")
    
    conn.close()

def update_job_status(conn, job_id, new_status, technician_id):
    """Update job status and log the change"""
    cursor = conn.cursor()
    
    if new_status == 'In Progress':
        cursor.execute("""
            UPDATE jobs 
            SET status = ?, started_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, job_id))
    elif new_status == 'Completed':
        cursor.execute("""
            UPDATE jobs 
            SET status = ?, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, job_id))
    else:
        cursor.execute("""
            UPDATE jobs 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, job_id))
    
    # Add a note about the status change
    cursor.execute("""
        INSERT INTO job_notes (job_id, note)
        VALUES (?, ?)
    """, (job_id, f"Status changed to {new_status} by technician"))
    
    conn.commit()

def add_job_note(conn, job_id, note):
    """Add a note to a job"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO job_notes (job_id, note)
        VALUES (?, ?)
    """, (job_id, note))
    conn.commit()