import sqlite3

def init_blacklist_tables():
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    
    # Create blacklist table
    c.execute('''CREATE TABLE IF NOT EXISTS blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT UNIQUE NOT NULL,
        added_by INTEGER,
        added_at REAL DEFAULT (strftime('%s', 'now')),
        status TEXT DEFAULT 'active',
        FOREIGN KEY (added_by) REFERENCES users (id)
    )''')
    
    conn.commit()
    conn.close()

def get_blacklist():
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    c.execute('SELECT word FROM blacklist WHERE status = "active"')
    words = [row[0] for row in c.fetchall()]
    conn.close()
    return words

def add_to_blacklist(word, user_id=None):
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO blacklist (word, added_by) VALUES (?, ?)',
                 (word.lower(), user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def is_blacklisted(word):
    conn = sqlite3.connect('llm_editor.db')
    c = conn.cursor()
    c.execute('SELECT 1 FROM blacklist WHERE word = ? AND status = "active"', (word.lower(),))
    result = c.fetchone() is not None
    conn.close()
    return result

# Initialize tables
init_blacklist_tables() 