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

def add_credentials(user_id, website, username, password):
    data = load_auth_data()
    if str(user_id) not in data:
        data[str(user_id)] = {}
    data[str(user_id)][website] = {'username': username, 'password': password}
    save_auth_data(data)

def get_credentials(user_id):
    data = load_auth_data()
    return data.get(str(user_id), {})

def remove_credentials(user_id, website):
    data = load_auth_data()
    if str(user_id) in data and website in data[str(user_id)]:
        del data[str(user_id)][website]
        save_auth_data(data)
        return True
    return False
