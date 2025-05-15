# Updated core.py – full version with SuperUser functionality
import hashlib
import requests
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson.objectid import ObjectId

client = MongoClient("mongodb://localhost:27017")
db = client["text_editor"]
users_collection = db["users"]
complaints_collection = db["complaints"]
collab_collection = db["collaborations"]
blacklist_suggestions = db["blacklist_suggestions"]

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(username, user_type, password):
    if user_type not in ["Free", "Paid", "Super"]:
        if user_type not in ["Free", "Paid"]:
            return False, "Only Free and Paid users can register here."
    if users_collection.find_one({"username": username}):
        return False, "Username already exists."
    hashed_pw = hash_password(password)
    tokens = 0  if user_type == "Free" else (100 if user_type == "Paid" else 1000)
    user_data = {
        "username": username,
        "user_type": user_type,
        "password": hashed_pw,
        "tokens": tokens,
        "blacklist": [],
        "last_login": None,
        "corrections": [],
        "stats": {"submitted": 0, "corrected": 0, "saved": 0},
        "saved_words": [],
        "status": "active"
    }
    users_collection.insert_one(user_data)
    return True, "User registered successfully."

def get_user(username, password=None):
    user = users_collection.find_one({"username": username})
    if not user:
        return None
    if user.get("status") == "suspended":
        return "suspended"
    if user["user_type"] == "Free" and user.get("last_login"):
        last_login = user["last_login"]
        if datetime.utcnow() - last_login < timedelta(minutes=3):
            return "login_cooldown"
    if password and user["password"] != hash_password(password):
        return "invalid_password"
    users_collection.update_one({"username": username}, {"$set": {"last_login": datetime.utcnow()}})
    return user

def update_tokens(username, tokens):
    users_collection.update_one({"username": username}, {"$set": {"tokens": tokens}})

def update_user(username, fields):
    users_collection.update_one({"username": username}, {"$set": fields})

def count_words(text):
    return len(text.strip().split())

def check_blacklist(text, blacklist):
    words = text.split()
    masked = [('*' * len(word)) if word in blacklist else word for word in words]
    blacklisted = [word for word in words if word in blacklist]
    return ' '.join(masked), blacklisted

def submit_text(user, text):
    word_count = count_words(text)
    if user.type == "Free" and word_count > 20:
        return "Free users can't submit more than 20 words."
    if user.tokens < word_count:
        user.tokens //= 2
        update_tokens(user.username, user.tokens)
        return "Not enough tokens. Penalty applied."
    masked_text, blacklisted = check_blacklist(text, user.blacklist)
    token_cost = word_count + len(''.join(blacklisted))
    if user.tokens < token_cost:
        return "Insufficient tokens."
    user.tokens -= token_cost
    user.submissions.append({"text": text, "time": datetime.utcnow()})
    update_tokens(user.username, user.tokens)
    return masked_text

def llm_correction(text):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "tinyllama",
                "prompt": f"""Fix grammar and spelling only:

{text}""",
                "stream": False
            }
        )
        data = response.json()
        return data.get("response", "[No response received from LLM]").strip()
    except Exception as e:
        return f"[Error contacting LLM: {e}]"

def apply_correction(user, original, corrected):
    changes = []
    for o, c in zip(original.split(), corrected.split()):
        if o != c and o not in user.saved_words:
            changes.append((o, c))
    user.tokens -= len(changes)
    update_tokens(user.username, user.tokens)
    users_collection.update_one({"username": user.username}, {"$push": {"corrections": {"$each": changes}}})
    return corrected

def save_text_file(user, content):
    if user.tokens >= 5:
        user.tokens -= 5
        update_tokens(user.username, user.tokens)
        filename = f"{user.username}_text.txt"
        with open(filename, 'w') as f:
            f.write(content)
        return f"Saved to {filename}"
    return "Not enough tokens to save."

def purchase_tokens(username, amount):
    user = users_collection.find_one({"username": username})
    if user and user["user_type"] == "Paid":
        users_collection.update_one({"username": username}, {"$inc": {"tokens": amount}})
        return True
    return False

def suggest_blacklist_word(user, word):
    if word:
        blacklist_suggestions.insert_one({"word": word, "suggested_by": user.username, "status": "pending"})
        return "Word submitted for review."
    return "Invalid word."

def approve_blacklist_word(superuser, word):
    suggestion = blacklist_suggestions.find_one({"word": word, "status": "pending"})
    if suggestion:
        blacklist_suggestions.update_one({"_id": suggestion["_id"]}, {"$set": {"status": "approved", "reviewed_by": superuser}})
        users_collection.update_many({}, {"$addToSet": {"blacklist": word}})
        return True
    return False

def handle_complaint(from_user, to_user, reason):
    complaints_collection.insert_one({
        "from": from_user,
        "to": to_user,
        "reason": reason,
        "status": "pending",
        "submitted_at": datetime.utcnow()
    })
    return "Complaint submitted."

def invite_collaborator(inviter, invitee):
    if inviter == invitee:
        return "Cannot invite yourself."
    collab_collection.insert_one({
        "inviter": inviter,
        "invitee": invitee,
        "status": "pending"
    })
    return "Invitation sent."

def respond_invitation(invitee, accept):
    inv = collab_collection.find_one({"invitee": invitee, "status": "pending"})
    if not inv:
        return "No pending invitation."
    if accept:
        collab_collection.update_one({"_id": inv["_id"]}, {"$set": {"status": "accepted"}})
        return "You are now a collaborator."
    else:
        users_collection.update_one({"username": inv["inviter"]}, {"$inc": {"tokens": -3}})
        collab_collection.update_one({"_id": inv["_id"]}, {"$set": {"status": "rejected"}})
        return "Invitation rejected."

# -- SuperUser Management Functions --
def suspend_user(username):
    users_collection.update_one({"username": username}, {"$set": {"status": "suspended"}})

def fine_user(username, amount):
    users_collection.update_one({"username": username}, {"$inc": {"tokens": -abs(amount)}})

def terminate_user(username):
    users_collection.delete_one({"username": username})

def handle_pending_complaints():
    return list(complaints_collection.find({"status": "pending"}))

def update_complaint_status(complaint_id, decision):
    complaints_collection.update_one({"_id": ObjectId(complaint_id)}, {"$set": {"status": decision}})

# User Classes
class User:
    def __init__(self, doc):
        self.username = doc["username"]
        self.tokens = doc["tokens"]
        self.type = doc["user_type"]
        self.blacklist = doc.get("blacklist", [])
        self.saved_words = doc.get("saved_words", [])
        self.submissions = []

class FreeUser(User): pass
class PaidUser(User): pass
class SuperUser(User): pass
