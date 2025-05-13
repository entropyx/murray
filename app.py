import streamlit as st
import hashlib
import json
import os

# Function to check credentials
def check_credentials(username, password):
    try:
        if not os.path.exists('users.json'):
            return False
            
        with open('users.json', 'r') as f:
            users = json.load(f)
        
        # Search for the user
        if username not in users:
            return False
            
        # Check the password
        stored_hash = users[username]['password']
        input_hash = hashlib.sha256(password.encode()).hexdigest()
        
        return stored_hash == input_hash
    except Exception as e:
        st.error(f"Error al verificar credenciales: {str(e)}")
        return False

# Function to add new user
def add_user(username, password, role="user"):
    try:
        # Load existing users or create new dictionary
        if os.path.exists('users.json'):
            with open('users.json', 'r') as f:
                users = json.load(f)
        else:
            users = {}
        
        # Check if the user already exists
        if username in users:
            return False, "The user already exists"
        
        # Create new user
        users[username] = {
            'password': hashlib.sha256(password.encode()).hexdigest(),
            'role': role
        }
        
        # Save in JSON
        with open('users.json', 'w') as f:
            json.dump(users, f, indent=4)
            
        return True, "User created successfully"
    except Exception as e:
        return False, f"Error creating user: {str(e)}"

# Add this function after check_credentials and before add_user
def get_user_role(username):
    try:
        with open('users.json', 'r') as f:
            users = json.load(f)
        return users[username]['role']
    except Exception as e:
        st.error(f"Error getting user role: {e}")
        return "user"  # Default role if there's an error

# Configure page
st.set_page_config(
    page_title="Geo Murray",
    page_icon="utils/Group 105.png",
    layout="wide"
)

# Initialize session state for login
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Login system
if not st.session_state.authenticated:
    st.title("Login")
    
    # Create tabs for login and registration
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if check_credentials(username, password):
                    st.session_state.authenticated = True
                    st.session_state.role = get_user_role(username)
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Username or password incorrect")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("New Username")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            register = st.form_submit_button("Register")
            
            if register:
                if new_password != confirm_password:
                    st.error("The passwords do not match")
                elif len(new_password) < 6:
                    st.error("The password must be at least 6 characters long")
                else:
                    success, message = add_user(new_username, new_password)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

# Only show the main content if authenticated
if st.session_state.authenticated:
    # Navigation setup
    pages = []
    if st.session_state.role == "admin":
        pages = [
            st.Page("experimental_design.py", title="Experimental design"),
            st.Page("experimental_evaluation.py", title="Experimental evaluation"),
            st.Page("dashboard.py", title="Dashboard"),
        ]
    else:
        pages = [
            st.Page("experimental_design.py", title="Experimental design"),
            st.Page("experimental_evaluation.py", title="Experimental evaluation"),
        ]

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
    unsafe_allow_html=True
)

# Ocultar elementos específicos de Streamlit
# hide_streamlit_style = """
#             <style>
#             /* Ocultar específicamente el enlace 'dashboard' */
#             [data-testid="stSidebarNav"] div:has(> a:contains("dashboard")) {display: none !important;}
#             [data-testid="stSidebarNav"] div:has(> a[href*="dashboard"]) {display: none !important;}
#             [data-testid="stSidebarNav"] a[href*="dashboard"] {display: none !important;}
#             [data-testid="stSidebarNav"] div:has(> a:contains("dashborad")) {display: none !important;}
#             [data-testid="stSidebarNav"] div:has(> a[href*="dashborad"]) {display: none !important;}
#             [data-testid="stSidebarNav"] a[href*="dashborad"] {display: none !important;}
            
#             div.stButton > button:first-child {
#                 background-color: #3e7cb1;
#                 color: white;
#                 border-radius: 5px;
#             }
#             div.stButton > button:hover {
#                 background-color: #2c5a8f;
#                 color: white;
#             }
#             </style>
#             """
# st.markdown(hide_streamlit_style, unsafe_allow_html=True)