import json

with open("users.json", "r") as f:
    users = json.load(f)

def verify_user(username: str, password: str) -> bool:
    for user in users:
        if user["username"] == username and user["password"] == password:
            return True
    return False

def get_id_by_username(username: str) -> int | None:
    for user in users:
        if user["username"] == username:
            return user["id"]
    return None
