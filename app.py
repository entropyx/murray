import streamlit as st
import hashlib
import json
import os
import datetime
from utils_auth import check_credentials, add_user, mark_link_as_used

# Check if authentication is required
AUTH_REQUIRED = bool(os.getenv('MURRAY_PASSWORD'))

st.set_page_config(
    page_title="Geo Murray", page_icon="utils/Group 105.png", layout="wide"
)

# Add this function after check_credentials and before add_user
def get_user_role(username):
    try:
        with open("traffic_metrics/users.json", "r") as f:
            users = json.load(f)
        return users[username]["role"]
    except Exception as e:
        st.error(f"Error getting user role: {e}")
        return "user"


def create_registration_link(role, max_uses=1):
    try:
        # Generate a unique token
        token = hashlib.sha256(os.urandom(32)).hexdigest()[:16]

        if os.path.exists("traffic_metrics/registration_links.json"):
            with open("traffic_metrics/registration_links.json", "r") as f:
                links = json.load(f)
        else:
            links = {}

        links[token] = {
            "role": role,
            "max_uses": max_uses,
            "used_count": 0,
            "created_at": str(datetime.datetime.now()),
        }

        with open("traffic_metrics/registration_links.json", "w") as f:
            json.dump(links, f, indent=4)

        return token
    except Exception as e:
        return None, f"Error creating registration link: {str(e)}"


def validate_registration_link(token):
    try:
        if not os.path.exists("traffic_metrics/registration_links.json"):
            return False, None

        with open("traffic_metrics/registration_links.json", "r") as f:
            links = json.load(f)

        if token not in links:
            return False, None

        link_info = links[token]
        if link_info["used_count"] >= link_info["max_uses"]:
            return False, None

        return True, link_info["role"]
    except Exception as e:
        return False, None

# Initialize session state for login
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = not AUTH_REQUIRED  # Auto-authenticate if no auth required
if 'role' not in st.session_state:
    st.session_state.role = "user"
if 'username' not in st.session_state:
    st.session_state.username = "Guest" if not AUTH_REQUIRED else ""

# Login system - only show if authentication is required
if AUTH_REQUIRED and not st.session_state.authenticated:
    st.title("Welcome to Geo Murray")
    st.write("Login or register.")

    query_params = st.query_params
    url_token = query_params.get("token", [""])[0]
    if "registration_token" not in st.session_state:
        st.session_state.registration_token = url_token

    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login = st.form_submit_button("Login")
            if login:
                is_entropy_email = username.strip().endswith("@entropy.tech")
                if is_entropy_email:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.role = "user"
                    st.rerun()
                elif check_credentials(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.role = get_user_role(username)
                    st.rerun()
                else:
                    st.error("Username or password incorrect")

    with tab2:
        with st.form("register_form"):
            username = st.text_input("Username")
            reg_input = st.text_input(
                "Registration token or valid email", key="registration_token"
            )
            new_password = st.text_input("New password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")
            register = st.form_submit_button("Register")
            if register:
                is_entropy_email = reg_input.strip().endswith("@entropy.tech")
                if not is_entropy_email and not reg_input:
                    st.error(
                        "You must enter a valid Registration Token or a valid email in the second field."
                    )
                elif new_password != confirm_password:
                    st.error("The passwords do not match")
                elif len(new_password) < 6:
                    st.error("The password must be at least 6 characters long")
                elif not username:
                    st.error("You must enter a username.")
                else:
                    if is_entropy_email:
                        success, message = add_user(
                            username.strip(), new_password, role="user"
                        )
                    else:
                        success, message = add_user(
                            username.strip(),
                            new_password,
                            registration_token=reg_input.strip(),
                        )
                        if success and reg_input:
                            mark_link_as_used(reg_input.strip())
                    if success:
                        st.success(message)
                    else:
                        st.error(message)


if st.session_state.authenticated:
    pages = []
    if st.session_state.role == "admin":
        pages = {
            "Hello "
            + st.session_state.username: [
                st.Page("experimental_design.py", title="Experimental design"),
                st.Page("experimental_evaluation.py", title="Experimental evaluation"),
                st.Page("dashboard.py", title="Dashboard"),
            ]
        }
    else:
        pages = {
            "Hello "
            + st.session_state.username: [
                st.Page("experimental_design.py", title="Experimental design"),
                st.Page("experimental_evaluation.py", title="Experimental evaluation"),
            ]
        }

    pg = st.navigation(pages)
    pg.run()

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6, .stTextHeader {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
    }
    
    button, input, textarea, select {
        font-family: 'Inter', sans-serif !important;
    }

    
    .stButton>button {
        font-size: 16px;
        font-weight: 600;
    }

    
    .stTextInput>div>div>input, 
    .stTextArea>div>textarea, 
    .stSelectbox>div>div>select, 
    .stMultiselect>div>div>div {
        font-family: 'Inter', sans-serif !important;
    }

    
    .stSlider {
        font-family: 'Inter', sans-serif;
    }
    
    </style>
    """,
    unsafe_allow_html=True,
)
