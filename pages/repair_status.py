import streamlit as st
from components.datamanager.databasemanger import DatabaseManager

def fetch_job_details(job_id):
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()

        # Debug print
        # print("Looking for job_id:", job_id)

        # Updated query with LEFT JOIN to prevent failure when related customer/store is missing
        cursor.execute('''
            SELECT j.id, j.device_model, j.problem_description, j.actual_cost, j.status, 
                   c.name AS customer_name, c.phone AS customer_phone,
                   s.name AS store_name, s.phone AS store_phone
            FROM jobs j
            LEFT JOIN customers c ON j.customer_id = c.id
            LEFT JOIN stores s ON j.store_id = s.id
            WHERE j.id = ?
        ''', (job_id,))
        result = cursor.fetchone()

        # print("Fetched job data:", result)
        return result

    except Exception as e:
        st.error("❌ Failed to retrieve job details.")
        print("Database error:", e)
        return None

def main():
    st.set_page_config(page_title="Repair Status", page_icon="🛠️")

    # Hide sidebar, toggle arrow, and Streamlit header/footer
    hide_sidebar_style = """
    <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        header, footer, [data-testid="stHeader"] {
            visibility: hidden;
        }
        .block-container {
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
    </style>
    """
    st.markdown(hide_sidebar_style, unsafe_allow_html=True)

    # Title
    st.title("🔍 Track Your Repair Job")

    # Extract job_id from URL
    job_id = st.query_params.get("job_id", None)

    if not job_id:
        st.warning("No Jobsheet ID provided in the URL.")
        return

    try:
        job_id = int(job_id)
    except ValueError:
        st.error("Invalid Job ID in URL.")
        return

    # Fetch and display job details
    data = fetch_job_details(job_id)

    if data:
        job_id, model, problem, cost, status, cust_name, cust_phone, store_name, store_phone = data
        st.markdown(f"**🧑 Customer Name:** {cust_name or 'N/A'}")
        st.markdown(f"**📱 Device Model:** {model}")
        st.markdown(f"**🛠️ Issue Reported:** {problem}")
        st.markdown(f"**📊 Current Status:** `{status}`")
        st.markdown(f"**💰 Cost:** ₹{cost}")
        st.markdown("---")
        st.markdown(f"**🏬 Store Name:** {store_name or 'N/A'}")
        st.markdown(f"**📞 Store Contact:** {store_phone or 'N/A'}")
    else:
        st.error("❌ No repair job found for the provided ID.")

if __name__ == "__main__":
    main()
