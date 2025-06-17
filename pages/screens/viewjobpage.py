import streamlit as st 
import pandas as pd 
from datetime import datetime, date
def view_jobs_tab(conn, user):
    """Tab for viewing existing jobs"""
    st.markdown("### Current Jobs")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("Filter by Status", 
                                   ["All", "New", "In Progress", "Completed", "On Hold"])
    with col2:
        date_filter = st.date_input("From Date", value=datetime.now().date())
    with col3:
        device_filter = st.selectbox("Filter by Device", 
                                   ["All", "Smartphone", "Tablet", "Laptop", "Desktop", "Watch", "Other"])
    
    # Build query using only schema-compatible fields
    query = '''
        SELECT j.id, j.created_at, c.name, j.device_type, j.device_model,
               j.problem_description, j.status, j.estimated_cost, j.actual_cost,
               u.full_name as technician
        FROM jobs j
        JOIN customers c ON j.customer_id = c.id
        LEFT JOIN technician_assignments ta ON ta.status = 'active'
        LEFT JOIN assignment_jobs aj ON aj.assignment_id = ta.id AND aj.job_id = j.id
        LEFT JOIN users u ON u.id = ta.technician_id
        WHERE 1=1
    '''
    
    params = []
    
    if user.get('store_id'):
        query += " AND j.store_id = ?"
        params.append(user['store_id'])
    
    if status_filter != "All":
        query += " AND j.status = ?"
        params.append(status_filter)
        
    if device_filter != "All":
        query += " AND j.device_type = ?"
        params.append(device_filter)
    
    query += " ORDER BY j.created_at DESC"
    
    jobs_df = pd.read_sql(query, conn, params=params)
    
    if len(jobs_df) > 0:
        # Format the dataframe for better display
        jobs_df['created_at'] = pd.to_datetime(jobs_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        jobs_df['problem_description'] = jobs_df['problem_description'].str[:50] + '...'
        jobs_df['estimated_cost'] = jobs_df['estimated_cost'].apply(lambda x: f"${x:.2f}")
        jobs_df['actual_cost'] = jobs_df['actual_cost'].apply(lambda x: f"${x:.2f}")
        
        # Rename columns for display
        jobs_df.columns = ['ID', 'Created', 'Customer', 'Device Type', 'Model', 
                          'Problem', 'Status', 'Est. Cost', 'Actual Cost', 'Technician']
        
        st.dataframe(jobs_df, use_container_width=True)
        
        # Add some statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Jobs", len(jobs_df))
        with col2:
            new_jobs = len(jobs_df[jobs_df['Status'] == 'New'])
            st.metric("New Jobs", new_jobs)
        with col3:
            in_progress = len(jobs_df[jobs_df['Status'] == 'In Progress'])
            st.metric("In Progress", in_progress)
        with col4:
            completed = len(jobs_df[jobs_df['Status'] == 'Completed'])
            st.metric("Completed", completed)
    else:
        st.info("No jobs found matching the selected criteria.")