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
def job_schema_config():
    """Page to configure job schema fields"""
    st.markdown(f'''
        <div class="main-header">
            <h1>⚙️ Job Schema Configuration</h1>
            <p>Configure the fields that appear on job sheets</p>
        </div>
    ''', unsafe_allow_html=True)
    
    db = DatabaseManager()
    conn = db.get_connection()
    
    # Initialize schema if not exists
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_schema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_name TEXT NOT NULL,
            field_label TEXT NOT NULL,
            field_type TEXT NOT NULL,
            is_required BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            is_paused BOOLEAN DEFAULT FALSE,
            field_order INTEGER DEFAULT 0,
            options TEXT,
            pattern TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add new columns if they don't exist
    try:
        cursor.execute('ALTER TABLE job_schema ADD COLUMN is_paused BOOLEAN DEFAULT FALSE')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE job_schema ADD COLUMN pattern TEXT')
    except:
        pass
    
    # Insert default schema if empty
    existing_fields = cursor.execute("SELECT COUNT(*) FROM job_schema").fetchone()[0]
    if existing_fields == 0:
        default_fields = [
            ('customer_name', 'Customer Name', 'text', True, True, False, 1, '', ''),
            ('customer_phone', 'Customer Phone', 'phone', True, True, False, 2, '', ''),
            ('customer_email', 'Customer Email', 'email', False, True, False, 3, '', ''),
            ('phone_password', 'Phone Password/PIN', 'pattern', False, True, False, 4, '', '8-3-4'),
            ('device_type', 'Device Type', 'select', True, True, False, 5, 'Smartphone,Laptop,Desktop,Tablet,Smart Watch,Gaming Console,TV,Other Electronics', ''),
            ('device_model', 'Device Model', 'text', True, True, False, 6, '', ''),
            ('serial_number', 'Serial/IMEI Number', 'text', False, True, False, 7, '', ''),
            ('problem_description', 'Problem Description', 'textarea', True, True, False, 8, '', ''),
            ('diagnostic_notes', 'Initial Diagnostic Notes', 'textarea', False, True, False, 9, '', ''),
            ('estimated_cost', 'Estimated Cost ($)', 'number', True, True, False, 10, '', ''),
            ('deposit_amount', 'Deposit Amount ($)', 'number', False, True, False, 11, '', ''),
            ('notification_method', 'Notification Method', 'checkbox', False, True, False, 12, 'Email,WhatsApp,SMS,Phone Call', ''),
            ('phone_received_by', 'Phone Received By', 'text', True, True, False, 13, '', ''),
            ('assigned_technician', 'Assigned Technician', 'select', False, True, False, 14, '', ''),
            ('technician_phone', 'Technician Phone', 'phone', False, True, False, 15, '', ''),
            ('status', 'Initial Status', 'select', True, True, False, 16, 'New,In Progress,Pending,Completed,Cancelled', ''),
            ('received_date', 'Received Date', 'date', True, True, False, 17, '', ''),
            ('terms_accepted', 'Terms and Conditions', 'checkbox', True, True, False, 18, '', '')
        ]
        
        for field in default_fields:
            cursor.execute('''
                INSERT INTO job_schema (field_name, field_label, field_type, is_required, is_active, is_paused, field_order, options, pattern)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', field)
    
    conn.commit()
    
    # Display current schema
    st.markdown("### Current Job Sheet Fields")
    
    schema_df = pd.read_sql('''
        SELECT * FROM job_schema 
        ORDER BY field_order, id
    ''', conn)
    
    if not schema_df.empty:
        for idx, field in schema_df.iterrows():
            # Color coding for status
            status_color = "🔴" if field['is_paused'] else ("🟢" if field['is_active'] else "🔵")
            status_text = "PAUSED" if field['is_paused'] else ("ACTIVE" if field['is_active'] else "INACTIVE")
            
            with st.expander(f"{status_color} {field['field_label']} ({field['field_type']}) - {status_text}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Field Name:** {field['field_name']}")
                    st.write(f"**Type:** {field['field_type']}")
                    st.write(f"**Required:** {'Yes' if field['is_required'] else 'No'}")
                
                with col2:
                    st.write(f"**Active:** {'Yes' if field['is_active'] else 'No'}")
                    st.write(f"**Paused:** {'Yes' if field['is_paused'] else 'No'}")
                    st.write(f"**Order:** {field['field_order']}")
                    if field['options']:
                        st.write(f"**Options:** {field['options']}")
                    if field['pattern']:
                        st.write(f"**Pattern:** {field['pattern']}")
                
                with col3:
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button(f"Edit", key=f"edit_field_{field['id']}"):
                            st.session_state[f"edit_field_{field['id']}"] = True
                            st.rerun()
                    
                    with btn_col2:
                        pause_text = "Resume" if field['is_paused'] else "Pause"
                        if st.button(f"{pause_text}", key=f"pause_field_{field['id']}"):
                            new_pause_status = not field['is_paused']
                            cursor.execute('''
                                UPDATE job_schema SET is_paused = ? WHERE id = ?
                            ''', (new_pause_status, field['id']))
                            conn.commit()
                            st.rerun()
                
                # Edit form
                if st.session_state.get(f"edit_field_{field['id']}", False):
                    with st.form(f"edit_field_form_{field['id']}"):
                        edit_col1, edit_col2 = st.columns(2)
                        
                        with edit_col1:
                            new_label = st.text_input("Field Label", value=field['field_label'])
                            new_type = st.selectbox("Field Type", 
                                ['text', 'email', 'phone', 'password', 'pattern', 'number', 'textarea', 'select', 'multiselect', 'checkbox', 'date'],
                                index=['text', 'email', 'phone', 'password', 'pattern', 'number', 'textarea', 'select', 'multiselect', 'checkbox', 'date'].index(field['field_type']))
                            new_required = st.checkbox("Required", value=field['is_required'])
                            new_active = st.checkbox("Active", value=field['is_active'])
                        
                        with edit_col2:
                            new_paused = st.checkbox("Paused", value=field['is_paused'])
                            new_order = st.number_input("Order", value=field['field_order'], min_value=0)
                            new_options = st.text_input("Options (comma-separated)", value=field['options'] or '')
                            
                            # Pattern field for pattern type
                            if new_type == 'pattern':
                                new_pattern = st.text_input("Pattern (e.g., 8-3-4 for XXX-XX-XXXX)", value=field['pattern'] or '')
                                st.caption("Pattern format: numbers separated by dashes (e.g., 8-3-4 creates XXX-XX-XXXX)")
                            else:
                                new_pattern = ''
                        
                        submit_col1, submit_col2 = st.columns(2)
                        with submit_col1:
                            if st.form_submit_button("Save Changes"):
                                cursor.execute('''
                                    UPDATE job_schema SET 
                                        field_label = ?, field_type = ?, is_required = ?, 
                                        is_active = ?, is_paused = ?, field_order = ?, options = ?, pattern = ?
                                    WHERE id = ?
                                ''', (new_label, new_type, new_required, new_active, new_paused, new_order, new_options, new_pattern, field['id']))
                                conn.commit()
                                st.success("Field updated successfully!")
                                st.session_state[f"edit_field_{field['id']}"] = False
                                st.rerun()
                        
                        with submit_col2:
                            if st.form_submit_button("Cancel"):
                                st.session_state[f"edit_field_{field['id']}"] = False
                                st.rerun()
    
    # Add new field
    st.markdown("### Add New Field")
    with st.form("new_field_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            field_name = st.text_input("Field Name (internal)", placeholder="e.g., warranty_period")
            field_label = st.text_input("Field Label (display)", placeholder="e.g., Warranty Period")
            field_type = st.selectbox("Field Type", 
                ['text', 'email', 'phone', 'password', 'pattern', 'number', 'textarea', 'select', 'multiselect', 'checkbox', 'date'])
            is_required = st.checkbox("Required Field")
            
        with col2:
            is_active = st.checkbox("Active", value=True)
            is_paused = st.checkbox("Paused", value=False)
            field_order = st.number_input("Display Order", value=len(schema_df) + 1, min_value=0)
            options = st.text_input("Options (comma-separated)", placeholder="For select/multiselect/checkbox fields")
            
            # Pattern field
            if field_type == 'pattern':
                pattern = st.text_input("Pattern (e.g., 8-3-4)", placeholder="e.g., 8-3-4 for XXX-XX-XXXX")
                st.caption("Pattern format: numbers separated by dashes")
            else:
                pattern = ''
        
        if st.form_submit_button("Add Field", use_container_width=True):
            if field_name and field_label:
                cursor.execute('''
                    INSERT INTO job_schema (field_name, field_label, field_type, is_required, is_active, is_paused, field_order, options, pattern)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (field_name, field_label, field_type, is_required, is_active, is_paused, field_order, options, pattern))
                conn.commit()
                st.success("New field added successfully!")
                st.rerun()
            else:
                st.error("Please provide field name and label")
    
    conn.close()