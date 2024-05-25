# auth.py

import os
import json

AUTH_FILE = 'auth.json'

def load_auth_data():
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_auth_data(data):
    with open(AUTH_FILE, 'w') as file:
        json.dump(data, file, indent=4)

def add_credentials(user_id, username, password):
    data = load_auth_data()
    data[user_id] = {'username': username, 'password': password}
    save_auth_data(data)

def get_credentials(user_id):
    data = load_auth_data()
    return data.get(str(user_id))

def remove_credentials(user_id):
    data = load_auth_data()
    if str(user_id) in data:
        del data[str(user_id)]
        save_auth_data(data)
