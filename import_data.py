import sqlite3
import time
from init_db import init_db

def import_data():
    # Initialize database first
    init_db()
    
    # Connect to the database
    conn = sqlite3.connect('llm_editor.db')
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute('DELETE FROM complaints')
    cursor.execute('DELETE FROM blacklist')
    cursor.execute('DELETE FROM users')
    
    # Insert sample users
    users = [
        ('admin', 'admin123', 'super', 1000),
        ('paid_user1', '123456', 'paid', 200),
        ('paid_user2', '123456', 'paid', 200),
        ('free_user1', '123456', 'free', 20),
        ('free_user2', '123456', 'free', 20)
    ]
    
    for username, password, role, tokens in users:
        cursor.execute('''INSERT INTO users (username, password, role, tokens, last_login)
            VALUES (?, ?, ?, ?, ?)''',
            (username, password, role, tokens, time.time()))
    
    # Insert sample blacklist words
    blacklist_words = [
        ('badword1', 1),
        ('badword2', 1)
    ]
    
    for word, added_by in blacklist_words:
        cursor.execute('''INSERT INTO blacklist (word, added_by, status)
            VALUES (?, ?, ?)''',
            (word, added_by, 'active'))
    
    # Insert sample complaints
    complaints = [
        (2, 3, 'Inappropriate language in collaboration', 'pending'),
        (3, 4, 'Spamming in comments', 'resolved'),
        (4, 5, 'Violation of terms', 'pending')
    ]
    
    for complainer_id, complained_id, reason, status in complaints:
        cursor.execute('''INSERT INTO complaints (complainer_id, complained_id, reason, status)
            VALUES (?, ?, ?, ?)''',
            (complainer_id, complained_id, reason, status))
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    print("Data imported successfully!")

if __name__ == "__main__":
    import_data() 