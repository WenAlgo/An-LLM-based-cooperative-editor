# Complaints and admin actions

import sqlite3
from datetime import datetime

def get_db():
    conn = sqlite3.connect('editor.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complainer_id INTEGER NOT NULL,
            complained_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            action_taken TEXT,
            penalty_tokens INTEGER DEFAULT 0
        )
    ''')
    return conn

def submit_complaint(complainer_id: int, complained_id: int, reason: str):
    """Submit a complaint about a collaborator"""
    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO complaints (complainer_id, complained_id, reason) VALUES (?, ?, ?)',
            (complainer_id, complained_id, reason)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error submitting complaint: {e}")
        return False
    finally:
        conn.close()

def resolve_complaint(complaint_id: int, action: str, penalty_tokens: int = 0):
    """Super user resolves a complaint and applies penalty if needed"""
    conn = get_db()
    try:
        conn.execute(
            '''UPDATE complaints 
               SET status = 'resolved', 
                   resolved_at = CURRENT_TIMESTAMP,
                   action_taken = ?,
                   penalty_tokens = ?
               WHERE id = ?''',
            (action, penalty_tokens, complaint_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error resolving complaint: {e}")
        return False
    finally:
        conn.close()

def get_complaints_for_user(user_id: int):
    """Get complaints involving a user (either as complainer or complained)"""
    conn = get_db()
    try:
        cursor = conn.execute(
            '''SELECT * FROM complaints 
               WHERE complainer_id = ? OR complained_id = ?
               ORDER BY created_at DESC''',
            (user_id, user_id)
        )
        return cursor.fetchall()
    except Exception as e:
        print(f"Error getting complaints: {e}")
        return []
    finally:
        conn.close()

def get_pending_complaints():
    """Get all pending complaints for admin review"""
    conn = get_db()
    try:
        cursor = conn.execute(
            'SELECT * FROM complaints WHERE status = "pending" ORDER BY created_at DESC'
        )
        return cursor.fetchall()
    except Exception as e:
        print(f"Error getting pending complaints: {e}")
        return []
    finally:
        conn.close() 