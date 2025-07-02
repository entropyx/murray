import hashlib
import json
import os
import datetime
from logger_config import get_logger

# Inicializar logger para este módulo
logger = get_logger("auth")

def check_credentials(username, password):
    try:
        if not os.path.exists('traffic_metrics/users.json'):
            return False
        with open('traffic_metrics/users.json', 'r') as f:
            users = json.load(f)
        if username not in users:
            return False
        stored_hash = users[username]['password']
        input_hash = hashlib.sha256(password.encode()).hexdigest()
        return stored_hash == input_hash
    except Exception as e:
        logger.error(f"Error verifying credentials: {str(e)}")
        return False

def add_user(username, password, role="user", registration_token=None):
    try:
        if registration_token:
            is_valid, assigned_role = validate_registration_link(registration_token)
            if not is_valid:
                return False, "Invalid or expired registration link"
            role = assigned_role
        if os.path.exists('traffic_metrics/users.json'):
            with open('traffic_metrics/users.json', 'r') as f:
                users = json.load(f)
        else:
            users = {}
        if username in users:
            return False, "The user already exists"
        users[username] = {
            'password': hashlib.sha256(password.encode()).hexdigest(),
            'role': role
        }
        with open('traffic_metrics/users.json', 'w') as f:
            json.dump(users, f, indent=4)
        return True, "User created successfully"
    except Exception as e:
        return False, f"Error creating user: {str(e)}"

def get_user_role(username):
    try:
        with open('traffic_metrics/users.json', 'r') as f:
            users = json.load(f)
        return users[username]['role']
    except Exception as e:
        return "user"

def create_registration_link(role, max_uses=1):
    try:
        token = hashlib.sha256(os.urandom(32)).hexdigest()[:16]
        if os.path.exists('traffic_metrics/registration_links.json'):
            with open('traffic_metrics/registration_links.json', 'r') as f:
                links = json.load(f)
        else:
            links = {}
        links[token] = {
            'role': role,
            'max_uses': max_uses,
            'used_count': 0,
            'created_at': str(datetime.datetime.now())
        }
        with open('traffic_metrics/registration_links.json', 'w') as f:
            json.dump(links, f, indent=4)
        return token
    except Exception as e:
        return None, f"Error creating registration link: {str(e)}"

def validate_registration_link(token):
    try:
        if not os.path.exists('traffic_metrics/registration_links.json'):
            return False, None
        with open('traffic_metrics/registration_links.json', 'r') as f:
            links = json.load(f)
        if token not in links:
            return False, None
        link_info = links[token]
        if link_info['used_count'] >= link_info['max_uses']:
            return False, None
        return True, link_info['role']
    except Exception as e:
        return False, None

def mark_link_as_used(token):
    try:
        with open('traffic_metrics/registration_links.json', 'r') as f:
            links = json.load(f)
        links[token]['used_count'] += 1
        with open('traffic_metrics/registration_links.json', 'w') as f:
            json.dump(links, f, indent=4)
        return True
    except Exception as e:
        return False 