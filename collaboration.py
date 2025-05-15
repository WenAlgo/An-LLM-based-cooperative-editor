# Collaboration features for paid users

import streamlit as st
import sqlite3
from datetime import datetime
import time
from user_manager import get_user, update_tokens

def get_db():
    return sqlite3.connect('llm_editor.db')

def init_collaboration_tables():
    conn = get_db()
    c = conn.cursor()
    
    # Table for collaboration invitations
    c.execute('''CREATE TABLE IF NOT EXISTS collaboration_invitations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inviter_id INTEGER,
        invitee_id INTEGER,
        text TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (inviter_id) REFERENCES users (id),
        FOREIGN KEY (invitee_id) REFERENCES users (id)
    )''')
    
    # Table for active collaborations
    c.execute('''CREATE TABLE IF NOT EXISTS collaborations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invitation_id INTEGER,
        text TEXT,
        last_edited_by INTEGER,
        last_edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (invitation_id) REFERENCES collaboration_invitations (id),
        FOREIGN KEY (last_edited_by) REFERENCES users (id)
    )''')
    
    conn.commit()
    conn.close()

def invite_user_to_collaborate(inviter_username: str, invitee_username: str, text: str) -> bool:
    inviter = get_user(inviter_username)
    invitee = get_user(invitee_username)
    
    if not inviter or not invitee:
        return False
    
    if invitee.role != 'paid':
        return False
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('''INSERT INTO collaboration_invitations 
                     (inviter_id, invitee_id, text)
                     VALUES (?, ?, ?)''',
                  (inviter.id, invitee.id, text))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error inviting user: {e}")
        return False
    finally:
        conn.close()

def list_invitations_for_user(username: str):
    user = get_user(username)
    if not user:
        return []
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT i.id, i.text, i.created_at, u.username as inviter
        FROM collaboration_invitations i
        JOIN users u ON i.inviter_id = u.id
        WHERE i.invitee_id = ? AND i.status = 'pending'
        ORDER BY i.created_at DESC
    ''', (user.id,))
    
    invitations = []
    for row in c.fetchall():
        invitations.append({
            'id': row[0],
            'text': row[1],
            'created_at': row[2],
            'inviter': row[3]
        })
    
    conn.close()
    return invitations

def accept_invitation(invitation_id: int) -> bool:
    conn = get_db()
    c = conn.cursor()
    
    try:
        # Get invitation details
        c.execute('SELECT inviter_id, invitee_id, text FROM collaboration_invitations WHERE id = ?', (invitation_id,))
        inv = c.fetchone()
        if not inv:
            return False
        
        # Update invitation status
        c.execute('UPDATE collaboration_invitations SET status = ? WHERE id = ?', ('accepted', invitation_id))
        
        # Create collaboration
        c.execute('''INSERT INTO collaborations 
                     (invitation_id, text, last_edited_by)
                     VALUES (?, ?, ?)''',
                  (invitation_id, inv[2], inv[1]))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error accepting invitation: {e}")
        return False
    finally:
        conn.close()

def reject_invitation(invitation_id: int) -> bool:
    conn = get_db()
    c = conn.cursor()
    
    try:
        # Get invitation details
        c.execute('SELECT inviter_id, invitee_id FROM collaboration_invitations WHERE id = ? AND status = ?', 
                 (invitation_id, 'pending'))
        inv = c.fetchone()
        if not inv:
            return False
        
        # Update invitation status
        c.execute('UPDATE collaboration_invitations SET status = ? WHERE id = ?', ('rejected', invitation_id))
        
        # Apply penalty to inviter
        update_tokens(inv[0], -3)  # 3 token penalty
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error rejecting invitation: {e}")
        return False
    finally:
        conn.close()

def list_collaborations_for_user(username: str):
    user = get_user(username)
    if not user:
        return []
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT c.id, c.text,
               CASE 
                   WHEN i.inviter_id = ? THEN u2.username
                   ELSE u1.username
               END as collaborator
        FROM collaborations c
        JOIN collaboration_invitations i ON c.invitation_id = i.id
        JOIN users u1 ON i.inviter_id = u1.id
        JOIN users u2 ON i.invitee_id = u2.id
        WHERE (i.inviter_id = ? OR i.invitee_id = ?)
        ORDER BY c.last_edited_at DESC
    ''', (user.id, user.id, user.id))
    
    collaborations = []
    for row in c.fetchall():
        collaborations.append({
            'id': row[0],
            'text': row[1],
            'collaborator': row[2]
        })
    
    conn.close()
    return collaborations

def update_collaboration(collaboration_id: int, user_id: int, new_text: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''UPDATE collaborations 
                     SET text = ?, last_edited_by = ?, last_edited_at = ?
                     WHERE id = ?''',
                  (new_text, user_id, current_time, collaboration_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating collaboration: {e}")
        return False
    finally:
        conn.close()

# Initialize collaboration tables
init_collaboration_tables()

def share_text_file(text_id: int, user_ids: list):
    """Share a text file with multiple users"""
    if 'shared_files' not in st.session_state:
        st.session_state['shared_files'] = {}
    
    # Initialize the sharing record if it doesn't exist
    if text_id not in st.session_state['shared_files']:
        st.session_state['shared_files'][text_id] = {
            'shared_with': set(),
            'permissions': {}
        }
    
    # Add new users to the sharing list
    for user_id in user_ids:
        st.session_state['shared_files'][text_id]['shared_with'].add(user_id)
        # Set default permissions (read-only)
        st.session_state['shared_files'][text_id]['permissions'][user_id] = 'read'
    
    return True

def get_shared_files_for_user(user_id: int):
    """Get all files shared with a user"""
    if 'shared_files' not in st.session_state:
        return []
    
    return [
        text_id for text_id, share_info in st.session_state['shared_files'].items()
        if user_id in share_info['shared_with']
    ]

def update_file_permissions(text_id: int, user_id: int, permission: str):
    """Update permissions for a shared file"""
    if 'shared_files' not in st.session_state or text_id not in st.session_state['shared_files']:
        return False
    
    if user_id not in st.session_state['shared_files'][text_id]['shared_with']:
        return False
    
    if permission not in ['read', 'write', 'admin']:
        return False
    
    st.session_state['shared_files'][text_id]['permissions'][user_id] = permission
    return True

def get_file_permissions(text_id: int, user_id: int):
    """Get permissions for a specific file and user"""
    if 'shared_files' not in st.session_state or text_id not in st.session_state['shared_files']:
        return None
    
    return st.session_state['shared_files'][text_id]['permissions'].get(user_id)

def get_user_collaborations(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT c.id, c.text,
               i.inviter_id, i.invitee_id,
               u1.username as inviter,
               u2.username as invitee
        FROM collaborations c
        JOIN collaboration_invitations i ON c.invitation_id = i.id
        JOIN users u1 ON i.inviter_id = u1.id
        JOIN users u2 ON i.invitee_id = u2.id
        WHERE (i.inviter_id = ? OR i.invitee_id = ?)
        AND i.status = 'accepted'
    ''', (user_id, user_id))
    collaborations = []
    for row in c.fetchall():
        collaborations.append({
            'id': row[0],
            'text': row[1],
            'inviter_id': row[2],
            'invitee_id': row[3],
            'inviter': row[4],
            'invitee': row[5]
        })
    conn.close()
    return collaborations 