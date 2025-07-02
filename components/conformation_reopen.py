import streamlit as st 
import pandas as pd
def show_reopen_confirmation_modal(conn, job_id):
    """Show confirmation modal for reopening a completed job"""
    
    # Get job details
    job_query = '''
    SELECT j.id, c.name AS customer_name, j.device_type, j.device_model, j.problem_description
    FROM jobs j
    JOIN customers c ON j.customer_id = c.id
    WHERE j.id = ?
    '''
    job_df = pd.read_sql(job_query, conn, params=[job_id])
    
    if len(job_df) == 0:
        st.error("Job not found")
        return
    
    job = job_df.iloc[0]
    
    # Create modal using st.dialog (if available) or container
    with st.container():
        st.markdown("### 🔄 Reopen Job Confirmation")
        st.markdown("---")
        
        # Display job details
        st.markdown(f"""
        **Job ID:** #{job['id']}  
        **Customer:** {job['customer_name']}  
        **Device:** {job['device_type']} {job['device_model'] if pd.notna(job['device_model']) else ''}  
        **Problem:** {job['problem_description']}
        """)
        
        st.warning("⚠️ This will change the job status from 'Completed' back to 'In Progress'. Are you sure you want to continue?")
        
        # Reason for reopening (optional)
        reopen_reason = st.text_area("Reason for reopening (optional):", placeholder="e.g., Customer returned with same issue, Additional repair needed, etc.")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("✅ Yes, Reopen", type="primary", key=f"confirm_reopen_{job_id}"):
                try:
                    cursor = conn.cursor()
                    
                    # Update job status back to "In Progress"
                    cursor.execute(
                        "UPDATE jobs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        ("In Progress", job_id)
                    )
                    
                    # Add a note to job history/comments if reason provided
                    if reopen_reason.strip():
                        # Assuming there's a job_notes or job_history table
                        try:
                            cursor.execute('''
                                INSERT INTO job_notes (job_id, note, created_at, note_type)
                                VALUES (?, ?, CURRENT_TIMESTAMP, 'status_change')
                            ''', (job_id, f"Job reopened: {reopen_reason.strip()}"))
                        except:
                            # If job_notes table doesn't exist, we can skip this
                            pass
                    
                    conn.commit()
                    
                    # Clear session state
                    for key in list(st.session_state.keys()):
                        if key.startswith(f"show_reopen_confirm_{job_id}"):
                            del st.session_state[key]
                    
                    st.success(f"✅ Job #{job_id} has been reopened and moved to 'In Progress' status!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error reopening job: {str(e)}")
                    conn.rollback()
        
        with col2:
            if st.button("❌ Cancel", key=f"cancel_reopen_{job_id}"):
                # Clear session state
                for key in list(st.session_state.keys()):
                    if key.startswith(f"show_reopen_confirm_{job_id}"):
                        del st.session_state[key]
                st.rerun()
        
        with col3:
            pass  # Empty column for spacing