import streamlit as st
import os 
import sys 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager
def show_update_status_modal(conn, job_id, new_status):
    """Modal for updating job status with cost adjustment - centered UI"""
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                j.id, j.status, j.estimated_cost, j.raw_cost, j.actual_cost,
                c.name AS customer_name, j.device_type, j.device_model
            FROM jobs j
            JOIN customers c ON j.customer_id = c.id
            WHERE j.id = ?
        ''', (job_id,))
        
        job_details = cursor.fetchone()
        
        if not job_details:
            st.error("Job details not found.")
            return
    except Exception as e:
        st.error(f"Error fetching job details: {str(e)}")
        return

    @st.dialog(f"📋 Update Job #{job_id} Status")
    def update_status_dialog():
        # Create a NEW connection inside the dialog   
        db = DatabaseManager()
        new_conn= db.get_connection()
        
        # Close button
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("❌", key=f"close_update_{job_id}", help="Close"):
                st.session_state[f"show_update_{job_id}"] = False
                new_conn.close()
                st.rerun()
        
        # Job Information Header
        st.markdown("### 📋 Job Information")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            **Customer:** {job_details[5]}  
            **Device:** {job_details[6]} {job_details[7] or ''}  
            **Current Status:** {job_details[1]}
            """)
        with col2:
            status_icon = "▶️" if new_status == "In Progress" else "✅"
            st.markdown(f"""
            **New Status:** {status_icon} {new_status}  
            **Job ID:** #{job_details[0]}
            """)
        
        st.divider()
        
        # Cost Update Form
        st.markdown("### 💰 Update Costs")
        
        with st.form(f"update_job_form_{job_id}"):
            col1, col2 = st.columns(2)
            
            with col1:
                raw_cost = st.number_input(
                    "Raw Cost ($)", 
                    value=float(job_details[3] or 0), 
                    min_value=0.0, 
                    step=0.01,
                    help="Your actual costs (parts, labor, overhead, etc.)"
                )
                
            with col2:
                actual_cost = st.number_input(
                    "Final Cost ($)", 
                    value=float(job_details[4] or job_details[2] or 0), 
                    min_value=0.0, 
                    step=0.01,
                    help="Amount charged to customer"
                )
            
            # Show profit calculation
            profit = actual_cost - raw_cost
            profit_margin = (profit / actual_cost * 100) if actual_cost > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                profit_color = "🟢" if profit > 0 else "🔴" if profit < 0 else "⚪"
                st.metric("Profit", f"${profit:.2f}", delta=f"{profit_color}")
            with col2:
                margin_color = "🟢" if profit_margin > 30 else "🟡" if profit_margin > 10 else "🔴"
                st.metric("Profit Margin", f"{profit_margin:.1f}%", delta=f"{margin_color}")
            with col3:
                st.metric("Estimated", f"${job_details[2]:.2f}")
            
            st.divider()
            
            # Additional notes
            notes = st.text_area(
                "Notes (Optional)", 
                placeholder="Add any notes about this status change...",
                height=80
            )
            
            # Submit buttons
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                cancel_clicked = st.form_submit_button("❌ Cancel", use_container_width=True)
                
            with col2:
                update_costs_only = st.form_submit_button("💰 Update Costs Only", use_container_width=True)
                
            with col3:
                status_icon = "▶️" if new_status == "In Progress" else "✅"
                update_status_clicked = st.form_submit_button(
                    f"{status_icon} Update to {new_status}", 
                    type="primary", 
                    use_container_width=True
                )
            
            # Handle form submissions
            if cancel_clicked:
                st.session_state[f"show_update_{job_id}"] = False
                new_conn.close()
                st.rerun()
                
            elif update_costs_only or update_status_clicked:
                try:
                    cursor = new_conn.cursor()
                    
                    if update_costs_only:
                        # Update only costs, keep current status
                        cursor.execute('''
                            UPDATE jobs 
                            SET raw_cost = ?, actual_cost = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (raw_cost, actual_cost, job_id))
                        
                        success_msg = f"✅ Costs updated for Job #{job_id}"
                    else:
                        # Update job status and costs
                        cursor.execute('''
                            UPDATE jobs 
                            SET status = ?, raw_cost = ?, actual_cost = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (new_status, raw_cost, actual_cost, job_id))
                        
                        # Set completed_at if status is Completed
                        if new_status == 'Completed':
                            cursor.execute('''
                                UPDATE jobs 
                                SET completed_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            ''', (job_id,))
                        
                        # Update technician assignments status if needed
                        cursor.execute('''
                            UPDATE technician_assignments 
                            SET status = ?
                            WHERE id IN (
                                SELECT ta.id 
                                FROM technician_assignments ta
                                JOIN assignment_jobs aj ON ta.id = aj.assignment_id
                                WHERE aj.job_id = ? AND ta.status = 'active'
                            )
                        ''', ('completed' if new_status == 'Completed' else 'active', job_id))
                        
                        success_icon = "▶️" if new_status == "In Progress" else "✅"
                        success_msg = f"{success_icon} Job #{job_id} updated to {new_status}"
                    
                    # Log the status change if notes provided
                    if notes.strip():
                        cursor.execute('''
                            INSERT INTO job_notes (job_id, note, created_at)
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                        ''', (job_id, f"Status changed to {new_status}: {notes}" if update_status_clicked else f"Costs updated: {notes}"))
                    
                    new_conn.commit()
                    st.success(success_msg)
                    
                    # Clear the modal and close connection
                    st.session_state[f"show_update_{job_id}"] = False
                    new_conn.close()
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error updating job: {str(e)}")
                    new_conn.rollback()
                    new_conn.close()
    
    # Show the dialog
    update_status_dialog()


