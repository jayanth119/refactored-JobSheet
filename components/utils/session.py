
import time
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from components.css.css import Style
# from components.datamanager.databasemanger import DatabaseManager
# from components.utils.auth import hash_password , verify_password,authenticate_user , create_user
# from pages.loginpage import login_signup_page

def check_session_timeout(st):
    if 'login_time' in st.session_state:
        session_duration = time.time() - st.session_state.login_time
        if session_duration > 3600:  # 1 hour timeout
            st.session_state.clear()
            st.rerun()
        return session_duration
    return 0
