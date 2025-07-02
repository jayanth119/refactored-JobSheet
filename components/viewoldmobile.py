import streamlit as st 
import os 
import sys 
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager

def view_old_mobiles():
    st.header("All Old Mobile Records")
    
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        
        # Get current user's store_id for filtering
        store_id = st.session_state.user.get('store_id')
        user_role = st.session_state.user.get('role')
        
        # Build query based on user role
        if user_role == 'admin':
            # Admin can see all records
            query = '''
                SELECT om.*, s.name as store_name 
                FROM old_mobiles om 
                LEFT JOIN stores s ON om.store_id = s.id 
                ORDER BY om.created_at DESC
            '''
            df = pd.read_sql_query(query, conn)
        else:
            # Other roles see only their store's records
            query = '''
                SELECT * FROM old_mobiles 
                WHERE store_id = ? 
                ORDER BY created_at DESC
            '''
            df = pd.read_sql_query(query, conn, params=[store_id])
        
        conn.close()
        
        if df.empty:
            st.info("No old mobile records found.")
            return
        
        # Add search and filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_term = st.text_input("🔍 Search", placeholder="Search by customer name, phone, or brand")
        
        with col2:
            # Handle case where mobile_brand column might have None values
            brand_options = ["All"] + [brand for brand in df['mobile_brand'].dropna().unique().tolist() if brand]
            brand_filter = st.selectbox("Filter by Brand", brand_options)
        
        with col3:
            # Handle case where repair_status column might have None values
            status_options = ["All"] + [status for status in df['repair_status'].dropna().unique().tolist() if status]
            status_filter = st.selectbox("Filter by Status", status_options)
        
        # Apply filters
        filtered_df = df.copy()
        
        if search_term:
            # Use proper pandas string operations with na=False to handle None values
            filtered_df = filtered_df[
                (filtered_df['customer_name'].astype(str).str.contains(search_term, case=False, na=False)) |
                (filtered_df['customer_phone'].astype(str).str.contains(search_term, case=False, na=False)) |
                (filtered_df['mobile_brand'].astype(str).str.contains(search_term, case=False, na=False))
            ]
        
        if brand_filter != "All":
            filtered_df = filtered_df[filtered_df['mobile_brand'] == brand_filter]
        
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['repair_status'] == status_filter]
        
        # Display statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Records", len(filtered_df))
        
        with col2:
            working_count = len(filtered_df[filtered_df['repair_status'] == 'Working'])
            st.metric("Working Phones", working_count)
        
        with col3:
            not_working_count = len(filtered_df[filtered_df['repair_status'] == 'Not Working'])
            st.metric("Not Working", not_working_count)
        
        # Display records in expandable format
        st.subheader(f"Records ({len(filtered_df)})")
        
        for index, record in filtered_df.iterrows():
            with st.expander(f"📱 {record['mobile_brand']} {record['mobile_model']} - {record['customer_name']} ({record['customer_phone']})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Customer Details:**")
                    st.write(f"• Name: {record['customer_name']}")
                    st.write(f"• Phone: {record['customer_phone']}")
                    if pd.notna(record['customer_email']) and record['customer_email']:
                        st.write(f"• Email: {record['customer_email']}")
                    if pd.notna(record['aadhar_number']) and record['aadhar_number']:
                        st.write(f"• Aadhar: {record['aadhar_number']}")
                    if pd.notna(record['customer_address']) and record['customer_address']:
                        st.write(f"• Address: {record['customer_address']}")
                
                with col2:
                    st.write("**Mobile Details:**")
                    st.write(f"• Brand: {record['mobile_brand']}")
                    st.write(f"• Model: {record['mobile_model']}")
                    if pd.notna(record['imei_number']) and record['imei_number']:
                        st.write(f"• IMEI: {record['imei_number']}")
                    st.write(f"• Status: {record['repair_status']}")
                    if pd.notna(record['warranty_status']) and record['warranty_status']:
                        st.write(f"• Warranty Status: {record['warranty_status']}")
                    if pd.notna(record['estimated_value']) and record['estimated_value'] > 0:
                        st.write(f"• Est. Value: ₹{record['estimated_value']:,.0f}")
                
                if pd.notna(record['accessories_included']) and record['accessories_included']:
                    st.write(f"**Accessories:** {record['accessories_included']}")
                
                if pd.notna(record['notes']) and record['notes']:
                    st.write(f"**Notes:** {record['notes']}")
                
                if pd.notna(record['repair_description']) and record['repair_description']:
                    st.write(f"**Repair Description:** {record['repair_description']}")
                
                st.write(f"**Registered:** {record['created_at']}")
                
                # Action buttons
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                
                with col_btn1:
                    pass 
                    # if st.button(f"📝 Edit", key=f"edit_{record['id']}"):
                    #     edit_old_mobile_record(record)
                
                with col_btn2:
                    if st.button(f"🗑️ Delete", key=f"delete_{record['id']}"):
                        if delete_old_mobile_record(record['id']):
                            st.rerun()
                
                with col_btn3:
                    pass 
                    # if st.button(f"📄 Generate Report", key=f"report_{record['id']}"):
                    #     generate_mobile_report(record)
        
    except Exception as e:
        st.error(f"Error loading records: {str(e)}")

def edit_old_mobile_record(record):
    st.subheader("Edit Mobile Record")
    # Implementation for editing records
    st.info("Edit functionality can be implemented here")

def delete_old_mobile_record(record_id):
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM old_mobiles WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
        st.success("Record deleted successfully!")
        return True
    except Exception as e:
        st.error(f"Error deleting record: {str(e)}")
        return False

def generate_mobile_report(record):
    st.subheader("Mobile Report")
    # Implementation for generating reports
    st.info("Report generation functionality can be implemented here")