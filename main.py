import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import hashlib
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import time
import sys
import os 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.css.css import Style
from components.datamanager.databasemanger import DatabaseManager
from components.utils.auth import hash_password , verify_password,authenticate_user , create_user
from pages.screens.loginpage import login_signup_page
from pages.screens.admindashboard import admin_dashboard
from pages.screens.staffdashboard import staff_dashboard 
from pages.screens.jobmanagement import  jobs_management
from pages.screens.storemanagement import store_management
from pages.screens.customersmanagement import  customers_management
from pages.screens.reportmanagement import reports_management
from pages.screens.settingpage import settings_page
from pages.screens.usermanagement import user_management 
from components.sidebarnavigation import sidebar_navigation

# Configure Streamlit page
st.set_page_config(
    page_title="RepairPro - Management System",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS styling
st.markdown(Style, unsafe_allow_html=True)


def main():
    if 'authenticated' not in st.session_state:
        login_signup_page()
    else:
        current_page = sidebar_navigation()
        
        if current_page == "dashboard":
            if st.session_state.user['role'] == 'admin':
                admin_dashboard(st)
            else:
                staff_dashboard()
        elif current_page == "jobs":
            jobs_management()
        elif current_page == "customers":
            customers_management()
        elif current_page == "stores":
            store_management()
        elif current_page == "reports":
            reports_management()
        elif current_page == "users":
            user_management()
        elif current_page == "settings":
            settings_page()

if __name__ == "__main__":
    main()