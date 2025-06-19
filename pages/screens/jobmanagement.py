import sys
import os
import io
import streamlit as st
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.datamanager.databasemanger import DatabaseManager
from pages.screens.viewjobpage import view_jobs_tab
from pages.screens.createjob import create_job_tab


def jobs_management():
    user = st.session_state.user

    st.markdown(f'''
        <div class="main-header">
            <h1>📋 Jobs Management</h1>
            <p>Manage repair jobs for {user['store_name'] if user.get('store_id') else 'all stores'}</p>
        </div>
    ''', unsafe_allow_html=True)
 
    if user['role'] == 'technician':
        tab1, tab2 = st.tabs([ "📋 View Jobs" , "📝 Add New Job"])
        db = DatabaseManager()
        conn = db.get_connection()

        with tab2:
            st.error("🚫 Access Denied: Technicians don't have access to job management.")
            st.info("Please contact your manager or admin for access to job management.")

        with tab1:
                view_jobs_tab(conn, user)
        

        return
    else :
        tab1, tab2 = st.tabs(["📝 Add New Job", "📋 View Jobs"])
    
        db = DatabaseManager()
        conn = db.get_connection()

        with tab2:
                view_jobs_tab(conn, user)

        with tab1:
                create_job_tab(conn, user, db)
        



    conn.close()





# Additional helper function to view photos for a job
def view_job_photos(conn, job_id):
    """View photos for a specific job"""
    cursor = conn.cursor()
    cursor.execute("SELECT id, photo, uploaded_at FROM job_photos WHERE job_id = ? ORDER BY uploaded_at", (job_id,))
    photos = cursor.fetchall()
    
    if photos:
        st.markdown(f"### 📸 Photos for Job #{job_id}")
        
        cols = st.columns(min(len(photos), 3))
        for i, (photo_id, photo_blob, uploaded_at) in enumerate(photos):
            with cols[i % 3]:
                try:
                    image = Image.open(io.BytesIO(photo_blob))
                    st.image(image, caption=f"Photo {i+1} - {uploaded_at}", use_column_width=True)
                except Exception as e:
                    st.error(f"Error displaying photo {photo_id}")
    else:
        st.info("No photos found for this job.")






def display_job_summary(conn, job_id):
    """Display job summary after creation"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT j.*, c.name as customer_name, c.phone as customer_phone,
               u.full_name as technician_name
        FROM jobs j
        JOIN customers c ON j.customer_id = c.id
        LEFT JOIN technician_assignments ta ON ta.status = 'active'
        LEFT JOIN assignment_jobs aj ON aj.assignment_id = ta.id AND aj.job_id = j.id
        LEFT JOIN users u ON u.id = ta.technician_id
        WHERE j.id = ?
    ''', (job_id,))
    
    job = cursor.fetchone()
    if job:
        with st.expander("📋 Job Summary", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Job ID:** #{job[0]}")
                st.write(f"**Customer:** {job[-3]}")
                st.write(f"**Phone:** {job[-2]}")
                st.write(f"**Device:** {job[3]} {job[4] or ''}")
            
            with col2:
                st.write(f"**Status:** {job[10]}")
                st.write(f"**Estimated Cost:** ${job[8]:.2f}")
                st.write(f"**Actual Cost:** ${job[9]:.2f}")
                st.write(f"**Technician:** {job[-1] or 'Unassigned'}")
            
            with col3:
                st.write(f"**Created:** {job[12]}")
                st.write(f"**Problem:** {job[7][:50]}..." if len(job[7]) > 50 else f"**Problem:** {job[7]}")
                st.write(f"**Notifications:** {job[6]}")



