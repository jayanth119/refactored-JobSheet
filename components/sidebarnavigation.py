import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.utils.session import check_session_timeout
from components.css.slidercss import sliderCss

def sidebar_navigation():
    user = st.session_state.user
    
    # Add custom CSS for professional sidebar
    st.markdown(sliderCss, unsafe_allow_html=True)
    
    # Initialize current page in session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'
    
    # Header with home redirect functionality - make it truly clickable
    # Create the header as a button with custom styling
    if st.sidebar.button(f"🔧 RepairPro\n{user['store_name']}", key="header_home_btn", use_container_width=True):
        st.session_state.current_page = 'dashboard'
        st.rerun()
    
    # Session info
    session_duration = check_session_timeout(st)
    remaining_time = 3600 - session_duration
    hours = int(remaining_time // 3600)
    minutes = int((remaining_time % 3600) // 60)
    
    # Profession display
    profession_display = {
        "admin": "Admin - System Manager",
        "technician": "Technician - Repair Expert",
        "staff": "Staff - Support Executive",
        "manager": "Manager - Store Head",
        "user": "Customer User"
    }
    
    # Navigation menu based on role
    if user['role'] == 'admin':
        menu_items = {
            "🏠 Dashboard": "dashboard",
            "📋 Jobs": "jobs",
            "👥 Customers": "customers",
            "📱 Old Mobiles": "old_mobiles", 
            "🏪 Store Management": "stores",
            "📊 Reports": "reports",
            "👤 User Management": "users",
            "⚙️ Settings": "settings"
        }
    elif user['role'] == "manager":
        menu_items = {
            "🏠 Dashboard": "dashboard",
            "📋 Jobs": "jobs",
            "👥 Customers": "customers",
            "📱 Old Mobiles": "old_mobiles", 
            "📊 Reports": "reports",
            "⚙️ Settings": "settings"
        }
    else:
        menu_items = {
            "🏠 Dashboard": "dashboard",
            "📋 Jobs": "jobs",
            "📱 Old Mobiles": "old_mobiles",  # New page added
            "⚙️ Settings": "settings"
        }
    
    # Create clickable menu items
    selected_page = None
    
    for menu_text, page_key in menu_items.items():
        # Check if this is the current active page
        is_active = st.session_state.current_page == page_key
        active_class = "active" if is_active else ""
        
        # Create clickable menu item
        menu_item_html = f"""
            <div class="menu-item {active_class}" onclick="window.parent.postMessage({{type: 'streamlit:setComponentValue', value: '{page_key}'}}, '*')">
                {menu_text}
            </div>
        """
        
        # Use button for actual functionality
        if st.sidebar.button(menu_text, key=f"menu_{page_key}", use_container_width=True):
            st.session_state.current_page = page_key
            selected_page = page_key
            st.rerun()
    
    # Role display
    role_description = profession_display.get(user['role'], "Professional")
    st.sidebar.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)
    
    st.sidebar.markdown(f"""
        <div class="role-display">
            <div>🧑‍💼 {role_description}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Sign out section
    st.sidebar.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)
    
    if st.sidebar.button("🚪 Sign Out", key="signout_btn", use_container_width=True):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
    
    # Session info
    st.sidebar.markdown(f"""
        <div class="session-info">
            ⏰ Session expires in: {hours:02d}:{minutes:02d}
        </div>
    """, unsafe_allow_html=True)
    
    # Return the selected page or current page
    return selected_page if selected_page else st.session_state.current_page