import streamlit as st
import os
import sys
import json
import time
import hashlib
from components.css.css import Style
from components.datamanager.databasemanger import DatabaseManager
from components.utils.auth import authenticate_user
from pages.screens.loginpage import login_signup_page
from pages.screens.admindashboard import admin_dashboard
from pages.screens.staffdashboard import staff_dashboard
from pages.screens.jobmanagement import jobs_management
from pages.screens.storemanagement import store_management
from pages.screens.customersmanagement import customers_management
from pages.screens.reportmanagement import reports_management
from pages.screens.settingpage import settings_page
from pages.screens.usermanagement import user_management
from components.sidebarnavigation import sidebar_navigation

st.set_page_config(
    page_title="RepairPro - Management System",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(Style, unsafe_allow_html=True)

TOKEN_FILE = "tokens.json"

def main():
    token = st.query_params.get("token", None)

    if 'authenticated' not in st.session_state:
        if token:
            try:
                with open(TOKEN_FILE, "r") as f:
                    token_map = json.load(f)
                if token in token_map:
                    st.session_state.user = token_map[token]
                    st.session_state.authenticated = True
            except Exception as e:
                st.error("Session recovery failed. Please log in again.")
                print("Token error:", e)

    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        login_signup_page()
    else:
        # Optional logout button
        # with st.sidebar:
        #     if st.button("Logout"):
        #         st.session_state.clear()
        #         st.query_params.clear()
        #         st.rerun()

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