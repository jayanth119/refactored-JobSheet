import sys
import os
import io
import pandas as pd
import streamlit as st
from datetime import datetime, date
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.css.css import Style
from components.datamanager.databasemanger import DatabaseManager
from components.utils.auth import (
    hash_password, verify_password, authenticate_user, create_user
)
from pages.screens.loginpage import login_signup_page
from pages.screens.admindashboard import admin_dashboard
from components.sidebarnavigation import sidebar_navigation
def display_job():
    with tab2:
        st.markdown("### Current Jobs")
        col1, col2, col3 = st.columns(3)

        with col1:
            status_filter = st.selectbox("Filter by Status", ["All", "New", "In Progress", "Completed", "Pending", "Cancelled"])
        with col2:
            device_filter = st.selectbox("Filter by Device", ["All", "Smartphone", "Laptop", "Desktop", "Tablet", "Other"])
        with col3:
            sort_by = st.selectbox("Sort by", ["Recent First", "Oldest First", "Customer Name", "Status"])

        base_query = """
            SELECT j.*, s.name as store_name
            FROM jobs j
            LEFT JOIN stores s ON j.store_id = s.id
        """

        conditions = []
        params = []

        if user['role'] == 'staff':
            conditions.append("j.store_id = ?")
            params.append(user['store_id'])

        if status_filter != "All":
            conditions.append("j.status = ?")
            params.append(status_filter)

        if device_filter != "All":
            conditions.append("j.device_type = ?")
            params.append(device_filter)

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        if sort_by == "Recent First":
            base_query += " ORDER BY j.created_at DESC"
        elif sort_by == "Oldest First":
            base_query += " ORDER BY j.created_at ASC"
        elif sort_by == "Customer Name":
            base_query += " ORDER BY j.customer_name ASC"
        elif sort_by == "Status":
            base_query += " ORDER BY j.status ASC"

        jobs_df = pd.read_sql(base_query, conn, params=params)

        if not jobs_df.empty:
            for _, job in jobs_df.iterrows():
                with st.expander(f"#{job['id']} - {job['customer_name']} | {job['device_type']} - {job['status']}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Device:** {job['device_type']} - {job.get('device_model', 'N/A')}")
                        st.write(f"**Problem:** {job.get('problem_description', 'N/A')}")
                        st.write(f"**Technician:** {job.get('technician', 'Unassigned')}")
                        if 'technician_phone' in job and job['technician_phone']:
                            st.write(f"**Tech Phone:** {job['technician_phone']}")
                        if 'phone_password' in job and job['phone_password']:
                            st.write(f"**Phone Password:** {'*' * len(str(job['phone_password']))}")
                        if 'notification_method' in job and job['notification_method']:
                            st.write(f"**Notifications:** {job['notification_method']}")

                    # Action buttons
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if st.button("✏️ Edit", key=f"edit_{job['id']}", help="Edit job details"):
                            st.session_state[f"edit_mode_{job['id']}"] = True
                            st.rerun()
                    
                    with col2:
                        if st.button("🔄 Update Status", key=f"status_{job['id']}", help="Update job status"):
                            st.session_state[f"status_mode_{job['id']}"] = True
                            st.rerun()
                    
                    with col3:
                        if st.button("📄 Job Sheet", key=f"sheet_{job['id']}", help="Download job sheet"):
                            # Get all schema fields for PDF generation
                            all_schema_df = pd.read_sql('''
                                SELECT * FROM job_schema 
                                ORDER BY field_order, id
                            ''', conn)
                            pdf_bytes = generate_enhanced_job_sheet_pdf(job['id'], dict(job), all_schema_df)
                            st.download_button(
                                label="📄 Download",
                                data=pdf_bytes,
                                file_name=f"job_sheet_{job['id']}.pdf",
                                mime="application/pdf",
                                key=f"download_{job['id']}"
                            )
                    
                    with col4:
                        if st.button("🗑️ Delete", key=f"delete_{job['id']}"):
                            if st.session_state.get(f"confirm_delete_{job['id']}", False):
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM jobs WHERE id = ?", (job['id'],))
                                conn.commit()
                                st.success(f"Job #{job['id']} deleted successfully!")
                                if f"confirm_delete_{job['id']}" in st.session_state:
                                    del st.session_state[f"confirm_delete_{job['id']}"]
                                st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{job['id']}"] = True
                                st.warning("Click delete again to confirm")
                    
                    # Edit mode
                    if st.session_state.get(f"edit_mode_{job['id']}", False):
                        st.markdown("---")
                        st.markdown("#### Edit Job Details")
                        
                        # Get active and non-paused schema for editing
                        edit_schema_df = pd.read_sql('''
                            SELECT * FROM job_schema 
                            WHERE is_active = 1 AND is_paused = 0
                            ORDER BY field_order, id
                        ''', conn)
                        
                        with st.form(f"edit_job_form_{job['id']}"):
                            edit_data = {}
                            edit_col1, edit_col2 = st.columns(2)
                            edit_col_toggle = True
                            
                            for _, field in edit_schema_df.iterrows():
                                current_col = edit_col1 if edit_col_toggle else edit_col2
                                current_value = job.get(field['field_name'], '')
                                
                                with current_col:
                                    if field['field_type'] == 'text':
                                        edit_data[field['field_name']] = st.text_input(
                                            field['field_label'],
                                            value=str(current_value) if current_value else '',
                                            key=f"edit_{job['id']}_{field['field_name']}"
                                        )
                                    
                                    elif field['field_type'] == 'email':
                                        edit_data[field['field_name']] = st.text_input(
                                            field['field_label'],
                                            value=str(current_value) if current_value else '',
                                            key=f"edit_{job['id']}_{field['field_name']}"
                                        )
                                    
                                    elif field['field_type'] == 'phone':
                                        edit_data[field['field_name']] = st.text_input(
                                            field['field_label'],
                                            value=str(current_value) if current_value else '',
                                            key=f"edit_{job['id']}_{field['field_name']}"
                                        )
                                    
                                    elif field['field_type'] == 'password':
                                        edit_data[field['field_name']] = st.text_input(
                                            field['field_label'],
                                            value=str(current_value) if current_value else '',
                                            type="password",
                                            key=f"edit_{job['id']}_{field['field_name']}"
                                        )
                                    
                                    elif field['field_type'] == 'pattern':
                                        # For editing, show as regular text input with current value
                                        edit_data[field['field_name']] = st.text_input(
                                            field['field_label'] + f" (Pattern: {field['pattern']})",
                                            value=str(current_value) if current_value else '',
                                            key=f"edit_{job['id']}_{field['field_name']}"
                                        )
                                    
                                    elif field['field_type'] == 'number':
                                        try:
                                            current_num = float(current_value) if current_value else 0.0
                                        except:
                                            current_num = 0.0
                                        edit_data[field['field_name']] = st.number_input(
                                            field['field_label'],
                                            value=current_num,
                                            min_value=0.0,
                                            step=0.01,
                                            key=f"edit_{job['id']}_{field['field_name']}"
                                        )
                                    
                                    elif field['field_type'] == 'textarea':
                                        edit_data[field['field_name']] = st.text_area(
                                            field['field_label'],
                                            value=str(current_value) if current_value else '',
                                            height=100,
                                            key=f"edit_{job['id']}_{field['field_name']}"
                                        )
                                    
                                    elif field['field_type'] == 'select':
                                        options = field['options'].split(',') if field['options'] else []
                                        if field['field_name'] == 'assigned_technician':
                                            # Special handling for technician selection
                                            if user['role'] == 'admin':
                                                technicians = pd.read_sql("""
                                                    SELECT DISTINCT u.full_name, u.username, s.name as store_name
                                                    FROM users u
                                                    LEFT JOIN stores s ON u.store_id = s.id
                                                    WHERE u.role = 'staff'
                                                    ORDER BY u.full_name
                                                """, conn)
                                                tech_options = [f"{row['full_name']} ({row['username']})" for _, row in technicians.iterrows()]
                                            else:
                                                technicians = pd.read_sql("""
                                                    SELECT full_name, username FROM users 
                                                    WHERE role = 'staff' AND store_id = ?
                                                    ORDER BY full_name
                                                """, conn, params=[user['store_id']])
                                                tech_options = [f"{row['full_name']} ({row['username']})" for _, row in technicians.iterrows()]
                                            
                                            all_options = ["Unassigned"] + tech_options
                                            current_idx = 0
                                            if current_value and current_value in all_options:
                                                current_idx = all_options.index(current_value)
                                            
                                            edit_data[field['field_name']] = st.selectbox(
                                                field['field_label'],
                                                all_options,
                                                index=current_idx,
                                                key=f"edit_{job['id']}_{field['field_name']}"
                                            )
                                        else:
                                            current_idx = 0
                                            if current_value and str(current_value) in options:
                                                current_idx = options.index(str(current_value))
                                            
                                            edit_data[field['field_name']] = st.selectbox(
                                                field['field_label'],
                                                options,
                                                index=current_idx,
                                                key=f"edit_{job['id']}_{field['field_name']}"
                                            )
                                    
                                    elif field['field_type'] == 'multiselect':
                                        options = field['options'].split(',') if field['options'] else []
                                        current_values = str(current_value).split(',') if current_value else []
                                        edit_data[field['field_name']] = st.multiselect(
                                            field['field_label'],
                                            options,
                                            default=[v.strip() for v in current_values if v.strip() in options],
                                            key=f"edit_{job['id']}_{field['field_name']}"
                                        )
                                    
                                    elif field['field_type'] == 'checkbox':
                                        options = field['options'].split(',') if field['options'] else []
                                        if options:  # Multiple checkbox options
                                            st.write(field['field_label'])
                                            current_values = str(current_value).split(',') if current_value else []
                                            selected_options = []
                                            for option in options:
                                                option = option.strip()
                                                checked = option in current_values
                                                if st.checkbox(option, value=checked, key=f"edit_{job['id']}_{field['field_name']}_{option}"):
                                                    selected_options.append(option)
                                            edit_data[field['field_name']] = selected_options
                                        else:  # Single checkbox
                                            checked = bool(current_value) if current_value else False
                                            edit_data[field['field_name']] = st.checkbox(
                                                field['field_label'],
                                                value=checked,
                                                key=f"edit_{job['id']}_{field['field_name']}"
                                            )
                                    
                                    elif field['field_type'] == 'date':
                                        try:
                                            if current_value:
                                                if isinstance(current_value, str):
                                                    current_date = datetime.strptime(current_value[:10], '%Y-%m-%d').date()
                                                else:
                                                    current_date = current_value
                                            else:
                                                current_date = datetime.now().date()
                                        except:
                                            current_date = datetime.now().date()
                                        
                                        edit_data[field['field_name']] = st.date_input(
                                            field['field_label'],
                                            value=current_date,
                                            key=f"edit_{job['id']}_{field['field_name']}"
                                        )
                                
                                edit_col_toggle = not edit_col_toggle
                            
                            # Form buttons
                            save_col, cancel_col = st.columns(2)
                            
                            with save_col:
                                if st.form_submit_button("💾 Save Changes", use_container_width=True):
                                    try:
                                        cursor = conn.cursor()
                                        
                                        # Update job record
                                        update_fields = []
                                        update_values = []
                                        
                                        for field_name, field_value in edit_data.items():
                                            if field_name == 'notification_method' and isinstance(field_value, list):
                                                update_fields.append(f"{field_name} = ?")
                                                update_values.append(','.join(field_value))
                                            else:
                                                update_fields.append(f"{field_name} = ?")
                                                update_values.append(field_value)
                                        
                                        update_values.append(job['id'])
                                        
                                        update_query = f"""
                                            UPDATE jobs SET {', '.join(update_fields)}
                                            WHERE id = ?
                                        """
                                        
                                        cursor.execute(update_query, update_values)
                                        conn.commit()
                                        
                                        st.success(f"✅ Job #{job['id']} updated successfully!")
                                        st.session_state[f"edit_mode_{job['id']}"] = False
                                        st.rerun()
                                        
                                    except Exception as e:
                                        st.error(f"❌ Error updating job: {str(e)}")
                            
                            with cancel_col:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    st.session_state[f"edit_mode_{job['id']}"] = False
                                    st.rerun()
                    
                    # Status update mode
                    if st.session_state.get(f"status_mode_{job['id']}", False):
                        st.markdown("---")
                        st.markdown("#### Update Job Status")
                        
                        with st.form(f"status_form_{job['id']}"):
                            status_col, cost_col = st.columns(2)
                            
                            with status_col:
                                new_status = st.selectbox(
                                    "New Status",
                                    ["New", "In Progress", "Pending", "Completed", "Cancelled"],
                                    index=["New", "In Progress", "Pending", "Completed", "Cancelled"].index(job.get('status', 'New')),
                                    key=f"status_select_{job['id']}"
                                )
                                
                                status_notes = st.text_area(
                                    "Status Update Notes",
                                    placeholder="Add any notes about this status change...",
                                    key=f"status_notes_{job['id']}"
                                )
                            
                            with cost_col:
                                if new_status == "Completed":
                                    actual_cost = st.number_input(
                                        "Final Cost ($)",
                                        value=float(job.get('estimated_cost', 0)) if job.get('estimated_cost') else 0.0,
                                        min_value=0.0,
                                        step=0.01,
                                        key=f"actual_cost_{job['id']}"
                                    )
                                else:
                                    actual_cost = None
                                
                                completion_date = None
                                if new_status == "Completed":
                                    completion_date = st.date_input(
                                        "Completion Date",
                                        value=datetime.now().date(),
                                        key=f"completion_date_{job['id']}"
                                    )
                            
                            # Form buttons
                            update_col, cancel_col = st.columns(2)
                            
                            with update_col:
                                if st.form_submit_button("🔄 Update Status", use_container_width=True):
                                    try:
                                        cursor = conn.cursor()
                                        
                                        update_fields = ["status = ?"]
                                        update_values = [new_status]
                                        
                                        if actual_cost is not None:
                                            update_fields.append("actual_cost = ?")
                                            update_values.append(actual_cost)
                                        
                                        if completion_date:
                                            update_fields.append("completion_date = ?")
                                            update_values.append(completion_date.isoformat())
                                        
                                        if status_notes:
                                            # Add to existing notes or create new
                                            existing_notes = job.get('diagnostic_notes', '') or ''
                                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                                            new_note = f"\n[{timestamp}] Status Update: {status_notes}"
                                            updated_notes = existing_notes + new_note
                                            update_fields.append("diagnostic_notes = ?")
                                            update_values.append(updated_notes)
                                        
                                        update_values.append(job['id'])
                                        
                                        update_query = f"""
                                            UPDATE jobs SET {', '.join(update_fields)}
                                            WHERE id = ?
                                        """
                                        
                                        cursor.execute(update_query, update_values)
                                        conn.commit()
                                        
                                        st.success(f"✅ Job #{job['id']} status updated to: {new_status}")
                                        st.session_state[f"status_mode_{job['id']}"] = False
                                        st.rerun()
                                        
                                    except Exception as e:
                                        st.error(f"❌ Error updating status: {str(e)}")
                            
                            with cancel_col:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    st.session_state[f"status_mode_{job['id']}"] = False
                                    st.rerun()

        else:
            st.info("No jobs found matching your criteria")