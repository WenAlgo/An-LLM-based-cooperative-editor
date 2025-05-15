import sqlite3
import time

def init_db():
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()

    # Drop existing tables if they exist
    c.execute('DROP TABLE IF EXISTS collaborations')
    c.execute('DROP TABLE IF EXISTS collaboration_invitations')
    c.execute('DROP TABLE IF EXISTS complaints')
    c.execute('DROP TABLE IF EXISTS blacklist')
    c.execute('DROP TABLE IF EXISTS users')

    # Create users table
    c.execute('''CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        tokens INTEGER DEFAULT 0,
        last_login REAL,
        total_corrections INTEGER DEFAULT 0,
        total_tokens_used INTEGER DEFAULT 0
    )''')

    # Create blacklist table
    c.execute('''CREATE TABLE blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT UNIQUE NOT NULL,
        added_by INTEGER,
        added_at REAL DEFAULT (strftime('%s', 'now')),
        status TEXT DEFAULT 'active',
        FOREIGN KEY (added_by) REFERENCES users (id)
    )''')

    # Create complaints table
    c.execute('''CREATE TABLE complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complainer_id INTEGER NOT NULL,
        complained_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at REAL DEFAULT (strftime('%s', 'now')),
        resolved_at REAL,
        action_taken TEXT,
        FOREIGN KEY (complainer_id) REFERENCES users (id),
        FOREIGN KEY (complained_id) REFERENCES users (id)
    )''')

    # Create collaboration_invitations table
    c.execute('''CREATE TABLE collaboration_invitations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inviter_id INTEGER NOT NULL,
        invitee_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at REAL DEFAULT (strftime('%s', 'now')),
        FOREIGN KEY (inviter_id) REFERENCES users (id),
        FOREIGN KEY (invitee_id) REFERENCES users (id)
    )''')

    # Create collaborations table
    c.execute('''CREATE TABLE collaborations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invitation_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        last_edited_by INTEGER NOT NULL,
        last_edited_at REAL DEFAULT (strftime('%s', 'now')),
        FOREIGN KEY (invitation_id) REFERENCES collaboration_invitations (id),
        FOREIGN KEY (last_edited_by) REFERENCES users (id)
    )''')

    # Create super user
    c.execute('''INSERT INTO users (username, password, role, tokens, last_login)
        VALUES (?, ?, ?, ?, ?)''',
        ('super', 'super123', 'super', 1000, time.time()))

    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()