# Updated create_admin.py
from pymongo import MongoClient
import hashlib

client = MongoClient("mongodb://localhost:27017")
db = client["text_editor"]
users = db["users"]

username = "admin1"
password = "d"
hashed_password = hashlib.sha256(password.encode()).hexdigest()

if not users.find_one({"username": username}):
    users.insert_one({
        "username": username,
        "user_type": "Super",
        "password": hashed_password,
        "tokens": 1000,
        "blacklist": [],
        "last_login": None,
        "corrections": [],
        "stats": {"submitted": 0, "corrected": 0, "saved": 0},
        "saved_words": []
    })
    print(f"SuperUser '{username}' created.")
else:
    print(f"User '{username}' already exists.")