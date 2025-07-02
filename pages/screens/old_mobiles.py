import streamlit as st
import os 
import sys 

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.viewoldmobile import view_old_mobiles
from components.createoldmobile import create_old_mobile_form

def old_mobiles_page():
    st.title("📱 Old Mobile Management")
    
    # Create tabs for Create and View functionality
    tab1, tab2 = st.tabs(["📝 Register Old Mobile", "📋 View All Records"])
    
    with tab1:
        create_old_mobile_form()
    
    with tab2:
        view_old_mobiles()

