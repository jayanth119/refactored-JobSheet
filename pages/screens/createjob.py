import streamlit as st 
from PIL import Image
import os 
import sys 
import pandas as pd 

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.utils.createjob import create_job_in_database
def create_job_tab(conn, user, db):
    """Enhanced job creation tab with schema-compatible fields only"""
    st.markdown("### Create New Repair Job")
    
    # Initialize session state for form data persistence
    if 'job_form_data' not in st.session_state:
        st.session_state.job_form_data = {}
    
    with st.form("new_job_form", clear_on_submit=False):
        form_data = {}
        
        # Customer Information Section
        st.markdown("#### 👤 Customer Information")
        col1, col2 = st.columns(2)
        
        with col1:
            customer_name = st.text_input("Customer Name*", 
                                        value=st.session_state.job_form_data.get('customer_name', ''),
                                        placeholder="Enter customer full name")
            customer_phone = st.text_input("Phone Number*", 
                                         value=st.session_state.job_form_data.get('customer_phone', ''),
                                         placeholder="Enter phone number")
        
        with col2:
            customer_email = st.text_input("Email Address", 
                                         value=st.session_state.job_form_data.get('customer_email', ''),
                                         placeholder="Enter email address")
            customer_address = st.text_area("Address", 
                                           value=st.session_state.job_form_data.get('customer_address', ''),
                                           placeholder="Enter customer address",
                                           height=80)
        
        # Check for existing customer
        existing_customer_info = None
        if customer_phone:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, email, address FROM customers 
                WHERE phone = ? OR email = ?
            ''', (customer_phone, customer_email))
            existing_customer_info = cursor.fetchone()
            
            if existing_customer_info:
                st.info(f"📋 Existing customer found: {existing_customer_info[1]}")
                if st.checkbox("Use existing customer details"):
                    customer_name = existing_customer_info[1]
                    customer_email = existing_customer_info[2] or customer_email
                    customer_address = existing_customer_info[3] or customer_address
        
        st.divider()
        
        # Device Information Section
        st.markdown("#### 📱 Device Information")
        col1, col2 = st.columns(2)
        
        with col1:
            device_type = st.selectbox("Device Type*", 
                                     ["Smartphone", "Tablet", "Laptop", "Desktop", "Watch", "Other"],
                                     index=0)
        
        with col2:
            device_model = st.text_input("Device Model", 
                                       placeholder="e.g., iPhone 14, Samsung Galaxy S23")
        
        # Enhanced Password Section
        st.markdown("#### 🔐 Device Security")
        password_section = render_password_section()
        device_password_type = password_section['type'] if password_section else "None"
        device_password = password_section['value'] if password_section else ""
        
        st.divider()
        
        # Problem Description Section
        st.markdown("#### 🔧 Repair Details")
        problem_description = st.text_area("Problem Description*", 
                                         placeholder="Describe the issue in detail...",
                                         height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            estimated_cost = st.number_input("Estimated Cost ($)", min_value=0.0, value=0.0, step=5.0)
        with col2:
            actual_cost = st.number_input("Actual Cost ($)", min_value=0.0, value=0.0, step=5.0)
        
        # Technician Assignment
        st.markdown("#### 👨‍🔧 Assignment")
        technician_assignment = render_technician_assignment(conn, user)
        
        # Notification Preferences
        st.markdown("#### 📢 Notification Preferences")
        notification_methods = st.multiselect(
            "How should we notify the customer?",
            ["SMS", "Email", "Phone Call", "WhatsApp"],
            default=["SMS"]
        )
        
        # Enhanced Photo Upload Section
        st.markdown("#### 📸 Device Photos")
        uploaded_photos = st.file_uploader(
            "Upload device photos (optional)",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            help="Upload photos of the device showing the issue (Max 10MB per photo)"
        )
        
        # Show photo preview if photos are uploaded
        if uploaded_photos:
            st.markdown("**Photo Preview:**")
            cols = st.columns(min(len(uploaded_photos), 4))
            for i, photo in enumerate(uploaded_photos[:4]):  # Show max 4 previews
                with cols[i]:
                    try:
                        image = Image.open(photo)
                        st.image(image, caption=photo.name, use_column_width=True)
                        st.caption(f"Size: {len(photo.getvalue()) / 1024:.1f} KB")
                    except Exception as e:
                        st.error(f"Error loading {photo.name}")
            
            if len(uploaded_photos) > 4:
                st.info(f"... and {len(uploaded_photos) - 4} more photos")
        
        # Form submission
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit_job = st.form_submit_button("🔧 Create Job", use_container_width=True)

        if submit_job:
            # Validation
            errors = []
            if not customer_name.strip():
                errors.append("Customer name is required")
            if not customer_phone.strip():
                errors.append("Customer phone is required")
            if not problem_description.strip():
                errors.append("Problem description is required")
            
            # Validate photo sizes
            if uploaded_photos:
                for photo in uploaded_photos:
                    photo_size_mb = len(photo.getvalue()) / (1024 * 1024)
                    if photo_size_mb > 10:
                        errors.append(f"Photo {photo.name} is too large ({photo_size_mb:.1f}MB). Max size is 10MB.")
            
            if errors:
                st.error("⚠️ Please fix the following errors:\n" + "\n".join(f"• {error}" for error in errors))
            else:
                with st.spinner("Creating job and processing photos..."):
                    # Create the job
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
                            'estimated_cost': estimated_cost,
                            'actual_cost': actual_cost,
                            'technician_id': technician_assignment,
                            'notification_methods': notification_methods,
                            'existing_customer_id': existing_customer_info[0] if existing_customer_info else None
                        },
                        uploaded_photos
                    )
                    
                if success:
                    st.success(f"✅ Job #{job_id} created successfully!")
                    
                    # Clear form data
                    st.session_state.job_form_data = {}
                    
                    # Show job summary with photo count
                    display_job_summary_with_photos(conn, job_id)
                    
                    # Option to create another job
                    if st.button("Create Another Job"):
                        st.rerun()

def display_job_summary_with_photos(conn, job_id):
    """Display job summary after creation with photo information"""
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
    
    # Get photo count
    cursor.execute("SELECT COUNT(*) FROM job_photos WHERE job_id = ?", (job_id,))
    photo_count = cursor.fetchone()[0]
    
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
                st.write(f"**📸 Photos:** {photo_count} uploaded")
def render_password_section():
    """Render enhanced password section with conditional inputs"""
    password_type = st.selectbox(
        "Device Lock Type*",
        ["None", "PIN", "Password", "Pattern"]
    )
    
    password_value = ""
    if password_type != "None":
        if password_type == "PIN":
            password_value = st.text_input(
                "PIN Code",
                type="password",
                placeholder="Enter device PIN",
                help="Enter the numeric PIN code"
            )
        elif password_type == "Password":
            password_value = st.text_input(
                "Password",
                type="password",
                placeholder="Enter device password",
                help="Enter the alphanumeric password"
            )
        elif password_type == "Pattern":
            password_value = st.text_input(
                "Pattern Description",
                placeholder="Describe the unlock pattern",
                help="Describe the pattern (e.g., L-shape, Z-pattern, etc.)"
            )
        elif password_type in ["Face ID", "Touch ID", "Fingerprint"]:
            st.info(f"✓ {password_type} selected - No additional input required")
            password_value = password_type
        else:  # Other
            password_value = st.text_input(
                "Security Details",
                placeholder="Describe the security method",
                help="Provide details about the security method"
            )
    
    return {
        'type': password_type,
        'value': password_value
    }


def render_technician_assignment(conn, user):
    """Render technician assignment section"""
    # Get available technicians for the current store
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
        tech_options.extend([(f"{row['full_name']} ({row['email']})", row['id']) 
                           for _, row in technicians_df.iterrows()])
        
        selected_tech = st.selectbox(
            "Assign Technician",
            tech_options,
            format_func=lambda x: x[0],
            help="Select a technician to assign this job to"
        )
        return selected_tech[1]
    else:
        st.warning("⚠️ No technicians available for assignment")
        return None
