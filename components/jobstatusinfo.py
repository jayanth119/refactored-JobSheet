import streamlit as st 


def display_job_info(data):
    
    job_id, model, problem, cost, status, cust_name, cust_phone, store_name, store_phone = data
    style = """
            <style>
            .home{
            text-align: center;
            margin-bottom: 30px;
            }
            </style>
            """
    
    st.markdown(style, unsafe_allow_html=True)
    st.markdown(f"**<div class='home'>🆔 Job ID:** #{job_id}</div>",unsafe_allow_html=True)
    st.markdown(f"**<div class='home'>🧑 Customer Name:** {cust_name or 'N/A'}</div>",unsafe_allow_html=True)
    st.markdown(f"**<div class='home'>📱 Device Model:** {model}</div>",unsafe_allow_html=True)
    st.markdown(f"**<div class='home'>🛠️ Issue Reported:** {problem}</div>",unsafe_allow_html=True)
    st.markdown(f"**<div class='home'>📊 Current Status:** `{status}`</div>",unsafe_allow_html=True)
    st.markdown(f"*<div class='home'>*📞 Customer Contact:** {cust_phone or 'N/A'}</div>",unsafe_allow_html=True)
    st.markdown(f"**<div class='home'>💰 Cost:** ₹{cost}</div>",unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"**<div class='home'>🏬 Store Name:** {store_name or 'N/A'}</div>",unsafe_allow_html=True)
    st.markdown(f"**<div class='home'>📞 Store Contact:** {store_phone or 'N/A'}</div>",unsafe_allow_html=True)
