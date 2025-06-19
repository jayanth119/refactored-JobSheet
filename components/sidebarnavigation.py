import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.utils.session import check_session_timeout


def sidebar_navigation():
    user = st.session_state.user

    # Header
    st.sidebar.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 10px; margin-bottom: 1rem;">
            <h2 style="color: white; margin: 0;">🔧 RepairPro</h2>
            <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 0.9rem;">{user['store_name']}</p>
        </div>
    """, unsafe_allow_html=True)

    # User info
    st.sidebar.markdown(f"""
        <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
            <div style="color: white; font-weight: 600;">{user['full_name']}</div>
            <div style="color: rgba(255,255,255,0.7); font-size: 0.8rem; text-transform: uppercase;">{user['role']}</div>
        </div>
    """, unsafe_allow_html=True)

    # Session info
    session_duration = check_session_timeout(st)
    remaining_time = 3600 - session_duration
    hours = int(remaining_time // 3600)
    minutes = int((remaining_time % 3600) // 60)

    st.sidebar.markdown(f"""
        <div class="session-info">
            ⏰ Session expires in: {hours:02d}:{minutes:02d}
        </div>
    """, unsafe_allow_html=True)

    # Profession display (instead of stats)
    profession_display = {
        "admin": "Admin - System Manager",
        "technician": "Technician - Repair Expert",
        "staff": "Staff - Support Executive",
        "manager": "Manager - Store Head",
        "user": "Customer User"
    }

    # Navigation menu
    if user['role'] == 'admin':
        menu_items = {
            "🏠 Dashboard": "dashboard",
            "📋 Jobs": "jobs",
            "👥 Customers": "customers",
            "🏪 Store Management": "stores",
            "📊 Reports": "reports",
            "👤 User Management": "users",
            "⚙️ Settings": "settings"
        }
    if user['role'] =="manager":
        menu_items = {
            "🏠 Dashboard": "dashboard",
            "📋 Jobs": "jobs",
            "👥 Customers": "customers",
            "📊 Reports": "reports",
            "⚙️ Settings": "settings"
        }   
    else:
        menu_items = {
            "🏠 Dashboard": "dashboard",
            "📋 Jobs": "jobs",
            "👥 Customers": "customers",
            "📊 Reports": "reports",
            "⚙️ Settings": "settings"
        }

    role_description = profession_display.get(user['role'], "Professional")
    selected = st.sidebar.radio("Menu", list(menu_items.keys()))

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"""
        <div style="background: #ffffff11; padding: 1rem; border-radius: 10px; text-align: center;">
            <div style="color: white; font-weight: bold; font-size: 1rem;">🧑‍💼 {role_description}</div>
        </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("---")

    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

    return menu_items[selected]
