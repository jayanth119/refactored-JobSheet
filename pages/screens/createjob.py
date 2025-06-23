import streamlit as st 
from PIL import Image
import os 
import sys 
import pandas as pd 

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.utils.createjob import create_job_in_database
from components.notifications.email_utils import send_job_status_email
from components.utils.models import models
from components.billpreview import display_bill_preview

def create_job_tab(conn, user, db):
    st.markdown("### Create New Repair Job")

    if 'job_form_data' not in st.session_state:
        st.session_state.job_form_data = {}
    if 'job_created_successfully' not in st.session_state:
        st.session_state.job_created_successfully = False

    if st.session_state.job_created_successfully:
        st.success("✅ Job created successfully!")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🔧 Create Another Job", use_container_width=True):
                st.session_state.job_created_successfully = False
                st.session_state.job_form_data = {}
                st.rerun()
        
        # Display the bill preview after successful job creation
        display_bill_preview(
            conn, 
            st.session_state.last_created_job_id, 
            st.session_state.job_form_data['customer_name'],
            st.session_state.job_form_data['customer_phone'],
            st.session_state.job_form_data['device_type'],
            st.session_state.job_form_data['device_model'],
            st.session_state.job_form_data['problem_description'],
            st.session_state.job_form_data['deposit_cost'],
            st.session_state.job_form_data['actual_cost'],
            status= "New"
        )
        st.divider()
        return

    # ✅ Render device password type and value BEFORE the form to allow reactivity
    st.markdown("#### 🔐 Device Security")
    st.info("💡 Password/PIN will be securely stored")
    password_section = render_password_section()  # Now reactive outside the form
    device_password_type = password_section['type']
    device_password = password_section['value']
    if device_password:
        st.success("🔒 Password/PIN captured - will be stored securely")
    
    st.markdown("#### 📱 Device Information")
    col1, col2 = st.columns(2)

    with col1:
        device_type = st.selectbox("Device Type*", ["Smartphone", "Tablet", "Laptop", "Desktop", "Watch", "Other"], index=0)
    with col2:
        device_model = st.selectbox("Device Model", models)
    
    with st.form("new_job_form", clear_on_submit=False):
        st.markdown("#### 👤 Customer Information")
        col1, col2 = st.columns(2)

        with col1:
            customer_name = st.text_input("Customer Name*", value=st.session_state.job_form_data.get('customer_name', ''), placeholder="Enter customer full name")
            customer_phone = st.text_input("Phone Number*", value=st.session_state.job_form_data.get('customer_phone', ''), placeholder="Enter phone number")

        with col2:
            customer_email = st.text_input("Email Address", value=st.session_state.job_form_data.get('customer_email', ''), placeholder="Enter email address")
            customer_address = st.text_area("Address", value=st.session_state.job_form_data.get('customer_address', ''), placeholder="Enter customer address", height=80)

        existing_customer_info = None
        if customer_phone:
            cursor = conn.cursor()
            cursor.execute('''SELECT id, name, email, address FROM customers WHERE phone = ? OR email = ?''', (customer_phone, customer_email))
            existing_customer_info = cursor.fetchone()
            if existing_customer_info:
                st.success(f"✅ Existing customer found: {existing_customer_info[1]} - Details auto-loaded")
                customer_name = existing_customer_info[1]
                customer_email = existing_customer_info[2] or customer_email
                customer_address = existing_customer_info[3] or customer_address
                st.info(f"📋 Using details: {customer_name} | {customer_email} | {customer_address}")

        st.divider()
        st.markdown("#### 🔧 Repair Details")
        problem_description = st.text_area("Problem Description*", placeholder="Describe the issue in detail...", height=100)
        col1, col2 = st.columns(2)
        with col1:
            deposit_cost = st.number_input("Deposit Amount ($)", min_value=0.0, value=0.0, step=5.0)
        with col2:
            actual_cost = st.number_input("Actual Cost ($)", min_value=0.0, value=0.0, step=5.0)

        st.markdown("#### 👨‍🔧 Assignment")
        technician_assignment = render_technician_assignment(conn, user)

        st.markdown("#### 📢 Notification Preferences")
        notification_methods = st.multiselect("How should we notify the customer?", ["SMS", "Email", "Phone Call", "WhatsApp"], default=["Email"])

        st.markdown("#### 📸 Device Photos")
        st.info("💡 Photos will be uploaded and securely stored")
        uploaded_photos = st.file_uploader("Upload device photos (optional)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, help="Upload photos of the device showing the issue (Max 10MB per photo)")
        if uploaded_photos:
            st.success(f"📸 {len(uploaded_photos)} photo(s) ready for upload")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit_job = st.form_submit_button("🔧 Create Job", use_container_width=True)

        if submit_job:
            errors = []
            if not customer_name.strip():
                errors.append("Customer name is required")
            if not customer_phone.strip():
                errors.append("Customer phone is required")
            if not problem_description.strip():
                errors.append("Problem description is required")

            if uploaded_photos:
                for photo in uploaded_photos:
                    photo_size_mb = len(photo.getvalue()) / (1024 * 1024)
                    if photo_size_mb > 10:
                        errors.append(f"Photo {photo.name} is too large ({photo_size_mb:.1f}MB). Max size is 10MB.")

            if errors:
                st.error("⚠️ Please fix the following errors:\n" + "\n".join(f"• {error}" for error in errors))
            else:
                # Store form data in session state
                st.session_state.job_form_data = {
                    'customer_name': customer_name,
                    'customer_phone': customer_phone,
                    'customer_email': customer_email,
                    'customer_address': customer_address,
                    'device_type': device_type,
                    'device_model': device_model,
                    'problem_description': problem_description,
                    'deposit_cost': deposit_cost,
                    'actual_cost': actual_cost
                }
                
                with st.spinner("Creating job and processing uploads..."):
                    success, job_id = create_job_in_database(
                        conn, db, user,
                        {
                            'customer_name': customer_name,
                            'customer_phone': customer_phone,
                            'customer_email': customer_email,
                            'customer_address': customer_address,
                            'device_type': device_type,
                            'device_model': device_model,
                            'device_password_type': device_password_type,
                            'device_password': device_password,
                            'problem_description': problem_description,
                            'deposit_cost': deposit_cost,
                            'actual_cost': actual_cost,
                            'technician_id': technician_assignment,
                            'notification_methods': notification_methods,
                            'existing_customer_id': existing_customer_info[0] if existing_customer_info else None,
                            'auto_used_existing': bool(existing_customer_info)
                        },
                        uploaded_photos
                    )
                    
                if success:      
                    send_job_status_email(conn, job_id)
                    st.session_state.job_created_successfully = True
                    st.session_state.last_created_job_id = job_id
                    
                    if device_password:
                        st.success("🔒 Password/PIN uploaded and secured")
                    if uploaded_photos:
                        st.success(f"📸 {len(uploaded_photos)} photo(s) uploaded successfully")
                    if existing_customer_info:
                        st.success("👤 Existing customer details automatically applied")
                    
                    st.rerun()



def render_password_section():
    password_type = st.radio(
        "Device Lock Type*",
        ["None", "PIN", "Password", "Pattern"],
        help="Select the type of security lock on the device",
        horizontal=True,
        key="device_lock_type"
    )

    password_value = ""
    if password_type != "None":
        st.markdown("---")
        st.markdown(f"#### 🔐 Enter {password_type}")
        if password_type == "PIN":
            password_value = st.text_input("PIN Code", type="password", placeholder="Enter device PIN (e.g., 1234)", key="pin_input_field")
        elif password_type == "Password":
            password_value = st.text_input("Password", type="password", placeholder="Enter device password", key="password_input_field")
        elif password_type == "Pattern":
            password_value = st.text_input("Pattern Sequence", placeholder="e.g., 1 → 5 → 9 → 6 → 3", key="pattern_input_field")
            with st.expander("📱 Pattern Helper", expanded=False):
                st.markdown("""
                **Pattern Grid Reference:**
                ```
                1 — 2 — 3
                |   |   |
                4 — 5 — 6
                |   |   |
                7 — 8 — 9
                ```
                **Example formats:**
                - Simple: `1 → 5 → 9`
                - Complex: `2 → 5 → 8 → 7 → 4 → 1`
                """)
    return {'type': password_type, 'value': password_value.strip() if password_value else ""}

def render_technician_assignment(conn, user):
    if user.get('store_id'):
        technicians_df = pd.read_sql('''
            SELECT u.id, u.full_name, u.email
            FROM users u
            JOIN store_technicians st ON u.id = st.technician_id
            WHERE st.store_id = ? AND st.is_active = 1 AND u.role = 'technician'
            ORDER BY u.full_name
        ''', conn, params=[user['store_id']])
    else:
        technicians_df = pd.read_sql('''
            SELECT u.id, u.full_name, u.email
            FROM users u
            JOIN store_technicians st ON u.id = st.technician_id
            WHERE st.is_active = 1 AND u.role = 'technician'
            ORDER BY u.full_name
        ''', conn)
    
    if len(technicians_df) > 0:
        tech_options = [("Unassigned", None)]
        tech_options.extend([(f"{row['full_name']} ({row['email']})", row['id']) for _, row in technicians_df.iterrows()])
        selected_tech = st.selectbox("Assign Technician", tech_options, format_func=lambda x: x[0], help="Select a technician to assign this job to")
        return selected_tech[1]
    else:
        st.warning("⚠️ No technicians available for assignment")
        return None