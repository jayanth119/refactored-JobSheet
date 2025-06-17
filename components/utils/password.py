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
def render_pattern_input(field_label, pattern, is_required=False):
    """Render a pattern-based input field"""
    if not pattern:
        return st.text_input(field_label + ('*' if is_required else ''), placeholder="Enter value")
    
    # Parse pattern (e.g., "8-3-4" -> [8, 3, 4])
    try:
        pattern_parts = [int(x) for x in pattern.split('-')]
    except:
        return st.text_input(field_label + ('*' if is_required else ''), placeholder="Enter value")
    
    st.write(field_label + ('*' if is_required else ''))
    
    # Create columns for each pattern part
    cols = st.columns(len(pattern_parts) + (len(pattern_parts) - 1))  # Extra columns for separators
    
    values = []
    col_idx = 0
    
    for i, part_length in enumerate(pattern_parts):
        with cols[col_idx]:
            placeholder = 'X' * part_length
            value = st.text_input(
                label="",
                placeholder=placeholder,
                max_chars=part_length,
                key=f"{field_label}_part_{i}",
                label_visibility="collapsed"
            )
            values.append(value)
        
        col_idx += 1
        
        # Add separator except for last part
        if i < len(pattern_parts) - 1:
            with cols[col_idx]:
                st.write("-")
            col_idx += 1
    
    # Combine values
    combined_value = '-'.join(values) if any(values) else ''
    return combined_value