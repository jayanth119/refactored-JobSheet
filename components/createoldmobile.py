from datetime import datetime
import streamlit as st
import pandas as pd
import os 
import sys 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager

def create_old_mobile_form():
    st.header("Register Old Mobile Phone")
    
    with st.form("old_mobile_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Customer Information")
            customer_name = st.text_input("Customer Name *", placeholder="Enter full name")
            customer_phone = st.text_input("Phone Number *", placeholder="Enter 10-digit mobile number")
            customer_email = st.text_input("Email", placeholder="customer@email.com")
            aadhar_number = st.text_input("Aadhar Number", placeholder="Enter 12-digit Aadhar number")
            customer_address = st.text_area("Address", placeholder="Enter complete address")
        
        with col2:
            st.subheader("Mobile Information")
            mobile_brand = st.selectbox("Mobile Brand *", [
                "Select Brand", "Apple", "Samsung", "OnePlus", "Xiaomi", "Realme", 
                "Oppo", "Vivo", "Google", "Nothing", "Motorola", "Nokia", "Other"
            ])
            
            if mobile_brand == "Other":
                mobile_brand = st.text_input("Specify Brand", placeholder="Enter brand name")
            elif mobile_brand == "Select Brand":
                mobile_brand = ""  # Set to empty if no brand selected
            
            mobile_model = st.text_input("Mobile Model *", placeholder="e.g., iPhone 14, Galaxy S23")
            imei_number = st.text_input("IMEI Number (Optional)", placeholder="Enter 15-digit IMEI")
            
            repair_status = st.selectbox("Repair Status *", [
                "Working", "Not Working", "Partially Working", "Screen Damaged", 
                "Battery Issues", "Water Damaged", "Other Issues"
            ])
            warranty_status = st.selectbox("Warranty Status *", [
                "Yes", "No"
            ])
            
            repair_description = ""
            if repair_status == "Other Issues":
                repair_description = st.text_area("Describe the issue", placeholder="Explain the problem")
            else:
                repair_description = repair_status
        
        st.subheader("Additional Details")
        col3, col4 = st.columns(2)
        
        with col3:
            estimated_value = st.number_input("Estimated Value (₹)", min_value=0.0, step=100.0)
            purchase_date = st.date_input("Original Purchase Date (Optional)")
        
        with col4:
            accessories_included = st.multiselect("Accessories Included", [
                "Charger", "Earphones", "Box", "Manual", "Screen Guard", "Back Cover"
            ])
            
        notes = st.text_area("Additional Notes", placeholder="Any other relevant information")
        
        submitted = st.form_submit_button("Register Old Mobile", type="primary")
        
        if submitted:
            # Validation
            if not customer_name or not customer_phone or not mobile_brand or not mobile_model or not repair_status:
                st.error("Please fill all required fields marked with *")
                return
            
            # Validate phone number
            if len(customer_phone) != 10 or not customer_phone.isdigit():
                st.error("Please enter a valid 10-digit phone number")
                return
            
            # Validate Aadhar if provided
            if aadhar_number and (len(aadhar_number) != 12 or not aadhar_number.isdigit()):
                st.error("Please enter a valid 12-digit Aadhar number")
                return
            
            # Validate IMEI if provided
            if imei_number and (len(imei_number) != 15 or not imei_number.isdigit()):
                st.error("Please enter a valid 15-digit IMEI number")
                return
            
            # Save to database
            if save_old_mobile_record(
                customer_name, customer_phone, customer_email, aadhar_number, customer_address,
                mobile_brand, mobile_model, imei_number, repair_status, warranty_status, repair_description,
                estimated_value, purchase_date, accessories_included, notes
            ):
                st.success("✅ Old mobile record registered successfully!")
            else:
                st.error("❌ Failed to register record. Please try again.")

def save_old_mobile_record(customer_name, customer_phone, customer_email, aadhar_number, 
                          customer_address, mobile_brand, mobile_model, imei_number, 
                          repair_status, warranty_status, repair_description, estimated_value, purchase_date, 
                          accessories_included, notes):
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get current user's store_id
        store_id = st.session_state.user.get('store_id')
        
        # Convert accessories list to string
        accessories_str = ", ".join(accessories_included) if accessories_included else ""
        
        # Convert empty strings to None for optional fields
        customer_email = customer_email if customer_email else None
        aadhar_number = aadhar_number if aadhar_number else None
        customer_address = customer_address if customer_address else None
        imei_number = imei_number if imei_number else None
        notes = notes if notes else None
        estimated_value = estimated_value if estimated_value > 0 else 0
        
        # Handle purchase_date - convert to string or None
        purchase_date_str = purchase_date.strftime('%Y-%m-%d') if purchase_date else None
        
        # Insert record
        cursor.execute('''
            INSERT INTO old_mobiles (
                customer_name, customer_phone, customer_email, aadhar_number, customer_address,
                mobile_brand, mobile_model, imei_number, repair_status, warranty_status, repair_description,
                estimated_value, purchase_date, accessories_included, notes, store_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            customer_name, customer_phone, customer_email, aadhar_number, customer_address,
            mobile_brand, mobile_model, imei_number, repair_status, warranty_status, repair_description,
            estimated_value, purchase_date_str, accessories_str, notes, store_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return False