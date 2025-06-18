import streamlit as st
import pandas as pd 
import io 
from PIL import Image

def visualize_pattern(pattern_str):
    grid = [["①", "②", "③"],
            ["④", "⑤", "⑥"],
            ["⑦", "⑧", "⑨"]]
    
    # Convert string like "2 → 5 → 8 → 7 → 4 → 1" to a list of ints
    try:
        points = [int(p.strip()) for p in pattern_str.split("→")]
    except Exception:
        return "Invalid pattern format"

    # Create a grid of status
    status_grid = [["" for _ in range(3)] for _ in range(3)]
    num_to_coords = {
        1: (0, 0), 2: (0, 1), 3: (0, 2),
        4: (1, 0), 5: (1, 1), 6: (1, 2),
        7: (2, 0), 8: (2, 1), 9: (2, 2),
    }

    for i, num in enumerate(points):
        r, c = num_to_coords.get(num, (-1, -1))
        if r == -1: continue
        grid[r][c] = f"🔵{num}"  # Highlight selected point

    rows = [" ".join(row) for row in grid]
    return "\n".join(rows)

def show_job_details_modal(conn, job_id):
    """Show complete job details in a centered modal dialog with photos"""
    cursor = conn.cursor()
    
    query = '''
    SELECT 
        j.id, j.created_at, j.updated_at, j.completed_at,
        j.device_type, j.device_model, j.device_password_type, j.device_password,
        j.notification_methods, j.problem_description, j.status,
        j.estimated_cost, j.raw_cost, j.actual_cost,
        c.name AS customer_name, c.phone AS customer_phone,
        c.email AS customer_email, c.address AS customer_address,
        s.name AS store_name, s.location AS store_location,
        u.full_name AS technician_name
    FROM jobs j
    JOIN customers c ON j.customer_id = c.id
    LEFT JOIN stores s ON j.store_id = s.id
    LEFT JOIN assignment_jobs aj ON aj.job_id = j.id
    LEFT JOIN technician_assignments ta ON ta.id = aj.assignment_id AND ta.status = 'active'
    LEFT JOIN users u ON u.id = ta.technician_id
    WHERE j.id = ?
    '''
    
    cursor.execute(query, (job_id,))
    job_details = cursor.fetchone()
    
    # Fetch job photos if they exist
    photo_query = "SELECT photo FROM job_photos WHERE job_id = ?"
    cursor.execute(photo_query, (job_id,))
    photos = cursor.fetchall()
    
    if job_details:
        @st.dialog(f"📋 Job Details - #{job_id}")
        def job_details_dialog():
            col1, col2 = st.columns([6, 1])
            # with col2:
                # if st.button("❌", key=f"close_{job_id}", help="Close"):
                #     st.session_state[f"show_details_{job_id}"] = False
                #     st.rerun()
            
            # Customer Info
            st.markdown("### 👤 Customer Information")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                **Name:** {job_details[14]}  
                **Phone:** {job_details[15]}  
                **Email:** {job_details[16] or 'Not provided'}
                """)
            with col2:
                st.markdown(f"""
                **Address:** {job_details[17] or 'Not provided'}  
                **Store:** {job_details[18] or 'Not assigned'}  
                **Location:** {job_details[19] or 'Not available'}
                """)
            
            st.divider()

            # Device Info
            st.markdown("### 📱 Device Information")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                **Device Type:** {job_details[4]}  
                **Model:** {job_details[5] or 'Not specified'}  
                **Password Type:** {job_details[6] or 'None'}
                """)
            with col2:
                st.markdown(f"""
                **Password:** {job_details[7] or 'Not provided'}  
                **Notifications:** {job_details[8] or 'Not specified'}  
                **Technician:** {job_details[20] or 'Unassigned'}
                """)
            
            pattern_text = job_details[7] or 'Not provided'
            if job_details[6] == "Pattern":
                pattern_display = visualize_pattern(pattern_text)
                st.markdown(f"**Pattern:**\n```\n{pattern_display}\n```")
            else:
                st.markdown(f"**Password:** {pattern_text}")
            st.divider()

            # Problem Description
            st.markdown("### 🔧 Problem Description")
            st.text_area("", value=job_details[9], height=100, disabled=True, key=f"problem_{job_id}")
            
            # Status
            col1, col2 = st.columns(2)
            with col1:
                status_color = {"New": "🔴", "In Progress": "🟡", "Completed": "🟢"}.get(job_details[10], "⚪")
                st.markdown(f"**Status:** {status_color} {job_details[10]}")
            with col2:
                st.markdown(f"**Created:** {pd.to_datetime(job_details[1]).strftime('%Y-%m-%d %H:%M')}")

            st.divider()

            # Financials
            st.markdown("### 💰 Financial Details")
            estimated = job_details[11] or 0
            raw = job_details[12] or 0  
            actual = job_details[13] or 0
            profit = actual - raw
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Estimated Cost", f"${estimated:.2f}")
            with col2:
                st.metric("Raw Cost", f"${raw:.2f}")
            with col3:
                st.metric("Final Cost", f"${actual:.2f}")
            with col4:
                profit_color = "normal" if profit >= 0 else "inverse"
                st.metric("Profit", f"${profit:.2f}", delta=f"${profit:.2f}", delta_color=profit_color)
            if actual > 0:
                margin = (profit / actual) * 100
                margin_color = "🟢" if margin > 30 else "🟡" if margin > 10 else "🔴"
                st.markdown(f"**Profit Margin:** {margin_color} {margin:.1f}%")

            # Timeline
            if job_details[2] or job_details[3]:
                st.markdown("### 📅 Timeline")
                col1, col2 = st.columns(2)
                if job_details[2]:
                    col1.markdown(f"**Last Updated:** {pd.to_datetime(job_details[2]).strftime('%Y-%m-%d %H:%M')}")
                if job_details[3]:
                    col2.markdown(f"**Completed:** {pd.to_datetime(job_details[3]).strftime('%Y-%m-%d %H:%M')}")

            st.divider()

            # Job Photos (if any)
            if photos:
                st.markdown("### 📷 Attached Photos")
                for i, (photo_blob,) in enumerate(photos):
                    try:
                        image = Image.open(io.BytesIO(photo_blob))
                        st.image(image, caption=f"Photo {i+1}", use_container_width=True)
                    except Exception:
                        st.warning(f"Unable to display photo {i+1}")

            st.divider()

            # Action buttons
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if job_details[10] == "New":
                    if st.button("▶️ Start Job", key=f"modal_start_{job_id}", type="primary"):
                        st.session_state[f"show_details_{job_id}"] = False
                        st.session_state[f"show_update_{job_id}"] = "In Progress"
                        st.rerun()
            with col2:
                if job_details[10] == "In Progress":
                    if st.button("✅ Complete Job", key=f"modal_complete_{job_id}", type="primary"):
                        st.session_state[f"show_details_{job_id}"] = False
                        st.session_state[f"show_update_{job_id}"] = "Completed"
                        st.rerun()
            with col3:
                if st.button("💰 Edit Costs", key=f"modal_edit_{job_id}"):
                    st.session_state[f"show_details_{job_id}"] = False
                    st.session_state[f"show_update_{job_id}"] = job_details[10]
                    st.rerun()

        job_details_dialog()
    else:
        st.error("Job details not found.")
        st.session_state[f"show_details_{job_id}"] = False
