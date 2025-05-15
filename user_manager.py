import sqlite3
from typing import Optional
import time
import hashlib

DB_PATH = 'database.db'

class User:
    def __init__(self, user_id, username, role, tokens):
        self.id = user_id
        self.username = username
        self.role = role
        self.tokens = tokens

# Database setup (run once)
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        tokens INTEGER,
        last_login TIMESTAMP,
        total_corrections INTEGER DEFAULT 0,
        total_tokens_used INTEGER DEFAULT 0
    )''')
    
    # Create table for correction history
    c.execute('''CREATE TABLE IF NOT EXISTS correction_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        original_text TEXT,
        corrected_text TEXT,
        correction_type TEXT,
        tokens_used INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Create table for rejected corrections
    c.execute('''CREATE TABLE IF NOT EXISTS rejected_corrections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        original_text TEXT,
        rejected_correction TEXT,
        reason TEXT,
        status TEXT DEFAULT 'pending',
        reviewed_by INTEGER,
        review_timestamp TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (reviewed_by) REFERENCES users (id)
    )''')
    
    conn.commit()
    conn.close()

def init_user_tables():
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        tokens INTEGER DEFAULT 0,
        last_login REAL,
        total_corrections INTEGER DEFAULT 0,
        total_tokens_used INTEGER DEFAULT 0
    )''')
    
    # Create complaints table
    c.execute('''CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complainer_id INTEGER NOT NULL,
        complained_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        response TEXT,
        status TEXT DEFAULT 'pending',
        created_at REAL DEFAULT (strftime('%s', 'now')),
        responded_at REAL,
        resolved_at REAL,
        action_taken TEXT,
        penalty_tokens INTEGER DEFAULT 0,
        penalty_user_id INTEGER,
        FOREIGN KEY (complainer_id) REFERENCES users (id),
        FOREIGN KEY (complained_id) REFERENCES users (id),
        FOREIGN KEY (penalty_user_id) REFERENCES users (id)
    )''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def signup(username, password):
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password, role, tokens, last_login) VALUES (?, ?, ?, ?, ?)',
                 (username, password, 'user', 0, time.time()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login(username, password):
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    c.execute('SELECT id, username, role, tokens FROM users WHERE username = ? AND password = ?', (username, password))
    row = c.fetchone()
    if row:
        # Check if user is terminated
        if row[2] == 'terminated':
            conn.close()
            return None
        c.execute('UPDATE users SET last_login = ? WHERE id = ?', (time.time(), row[0]))
        conn.commit()
        return User(row[0], row[1], row[2], row[3])
    conn.close()
    return None

def get_user(username):
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    c.execute('SELECT id, username, role, tokens FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return User(row[0], row[1], row[2], row[3])
    return None

def update_tokens(user_id, amount):
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    c.execute('UPDATE users SET tokens = tokens + ?, total_tokens_used = total_tokens_used + ? WHERE id = ?',
             (amount, abs(amount) if amount < 0 else 0, user_id))
    conn.commit()
    conn.close()

def purchase_tokens(user_id, amount):
    if amount < 10:
        return False
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    c.execute('UPDATE users SET tokens = tokens + ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()
    return True

def get_all_users():
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    c.execute('''SELECT id, username, role, tokens, total_corrections, total_tokens_used 
                 FROM users ORDER BY username''')
    users = [{'id': row[0], 'username': row[1], 'role': row[2], 'tokens': row[3],
              'total_corrections': row[4], 'total_tokens_used': row[5]} for row in c.fetchall()]
    conn.close()
    return users

def suspend_user(user_id):
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    c.execute('UPDATE users SET role = ? WHERE id = ?', ('suspended', user_id))
    conn.commit()
    conn.close()

def terminate_user(user_id):
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    c.execute('UPDATE users SET role = ? WHERE id = ?', ('terminated', user_id))
    conn.commit()
    conn.close()

def get_pending_complaints():
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    c.execute('''SELECT c.id, c.complainer_id, c.complained_id, c.reason, c.created_at,
                        u1.username as complainer_username,
                        u2.username as complained_username
                 FROM complaints c
                 JOIN users u1 ON c.complainer_id = u1.id
                 JOIN users u2 ON c.complained_id = u2.id
                 WHERE c.status = 'pending'
                 ORDER BY c.created_at DESC''')
    complaints = [{'id': row[0], 'complainer_id': row[1], 'complained_id': row[2],
                  'reason': row[3], 'created_at': row[4],
                  'complainer_username': row[5], 'complained_username': row[6]}
                 for row in c.fetchall()]
    conn.close()
    return complaints

def resolve_complaint(complaint_id, action, penalty=0):
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    try:
        c.execute('SELECT complained_id FROM complaints WHERE id = ?', (complaint_id,))
        row = c.fetchone()
        if not row:
            return False
        
        complained_id = row[0]
        
        if action == "Token Penalty":
            c.execute('UPDATE users SET tokens = tokens - ? WHERE id = ?',
                     (penalty, complained_id))
        
        c.execute('''UPDATE complaints 
                    SET status = ?, resolved_at = ?, action_taken = ?
                    WHERE id = ?''',
                 ('resolved', time.time(), action, complaint_id))
        
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_user_statistics(user_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT total_corrections, total_tokens_used, tokens 
                 FROM users WHERE id = ?''', (user_id,))
    stats = c.fetchone()
    conn.close()
    return {
        'total_corrections': stats[0],
        'total_tokens_used': stats[1],
        'current_tokens': stats[2]
    }

def is_super_user(user: User) -> bool:
    return user.role == 'super'

def is_paid_user(user: User) -> bool:
    return user.role == 'paid'

def get_pending_rejected_corrections():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT r.id, r.user_id, r.original_text, r.rejected_correction, r.reason, r.status,
               u.username, r.review_timestamp
        FROM rejected_corrections r
        JOIN users u ON r.user_id = u.id
        WHERE r.status = 'pending'
        ORDER BY r.review_timestamp DESC
    ''')
    rejections = []
    for row in c.fetchall():
        rejections.append({
            'id': row[0],
            'user_id': row[1],
            'original_text': row[2],
            'rejected_correction': row[3],
            'reason': row[4],
            'status': row[5],
            'username': row[6],
            'review_timestamp': row[7]
        })
    conn.close()
    return rejections

def handle_rejected_correction(rejection_id: int, status: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE rejected_corrections 
                 SET status = ?, reviewed_by = ?, review_timestamp = ? 
                 WHERE id = ?''', 
              (status, st.session_state['user'].id, time.time(), rejection_id))
    conn.commit()
    conn.close()

def init_complaints_table():
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    
    # Drop existing complaints table to ensure clean schema
    c.execute('DROP TABLE IF EXISTS complaints')
    
    # Create complaints table with all required columns
    c.execute('''CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complainer_id INTEGER NOT NULL,
        complained_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        response TEXT,
        status TEXT DEFAULT 'pending',
        created_at REAL DEFAULT (strftime('%s', 'now')),
        responded_at REAL,
        resolved_at REAL,
        action_taken TEXT,
        penalty_tokens INTEGER DEFAULT 0,
        penalty_user_id INTEGER,
        FOREIGN KEY (complainer_id) REFERENCES users (id),
        FOREIGN KEY (complained_id) REFERENCES users (id),
        FOREIGN KEY (penalty_user_id) REFERENCES users (id)
    )''')
    
    conn.commit()
    conn.close()

def submit_complaint(complainer_id: int, complained_username: str, reason: str) -> bool:
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    try:
        # Get complained user's ID
        c.execute('SELECT id FROM users WHERE username = ?', (complained_username,))
        row = c.fetchone()
        if not row:
            return False
        
        complained_id = row[0]
        
        # Insert complaint
        c.execute('''INSERT INTO complaints 
                    (complainer_id, complained_id, reason, status)
                    VALUES (?, ?, ?, ?)''',
                 (complainer_id, complained_id, reason, 'pending'))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error submitting complaint: {e}")
        return False
    finally:
        conn.close()

def get_user_complaints(user_id: int) -> list:
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    c.execute('''
        SELECT c.id, c.reason, c.response, c.status, c.created_at, c.responded_at,
               u1.username as complainer_username,
               u2.username as complained_username
        FROM complaints c
        JOIN users u1 ON c.complainer_id = u1.id
        JOIN users u2 ON c.complained_id = u2.id
        WHERE c.complained_id = ? AND c.status = 'pending'
        ORDER BY c.created_at DESC
    ''', (user_id,))
    complaints = [{'id': row[0], 'reason': row[1], 'response': row[2],
                  'status': row[3], 'created_at': row[4], 'responded_at': row[5],
                  'complainer_username': row[6], 'complained_username': row[7]}
                 for row in c.fetchall()]
    conn.close()
    return complaints

def respond_to_complaint(complaint_id: int, response: str) -> bool:
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    try:
        c.execute('''UPDATE complaints 
                    SET response = ?, responded_at = ?
                    WHERE id = ?''',
                 (response, time.time(), complaint_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error responding to complaint: {e}")
        return False
    finally:
        conn.close()

def resolve_complaint(complaint_id: int, action: str, penalty: int, penalty_user_id: int) -> bool:
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    try:
        # Apply token penalty if specified
        if penalty > 0:
            c.execute('UPDATE users SET tokens = tokens - ? WHERE id = ?',
                     (penalty, penalty_user_id))
        
        c.execute('''UPDATE complaints 
                    SET status = ?, resolved_at = ?, action_taken = ?,
                        penalty_tokens = ?, penalty_user_id = ?
                    WHERE id = ?''',
                 ('resolved', time.time(), action, penalty, penalty_user_id, complaint_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error resolving complaint: {e}")
        return False
    finally:
        conn.close()

def get_complaint_details(complaint_id: int) -> Optional[dict]:
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    try:
        c.execute('''
            SELECT c.id, c.reason, c.response, c.status, c.created_at, c.responded_at,
                   u1.username as complainer_username,
                   u2.username as complained_username
            FROM complaints c
            JOIN users u1 ON c.complainer_id = u1.id
            JOIN users u2 ON c.complained_id = u2.id
            WHERE c.id = ?
        ''', (complaint_id,))
        row = c.fetchone()
        if row:
            return {
                'id': row[0],
                'reason': row[1],
                'response': row[2],
                'status': row[3],
                'created_at': row[4],
                'responded_at': row[5],
                'complainer_username': row[6],
                'complained_username': row[7]
            }
        return None
    finally:
        conn.close()

# Initialize all tables
def init_all_tables():
    init_db()
    init_complaints_table()
    init_user_tables()

# Initialize tables
init_all_tables() 