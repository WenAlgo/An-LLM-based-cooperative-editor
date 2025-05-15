import sqlite3

def check_database():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    print("Checking users table:")
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    for user in users:
        print(f"ID: {user[0]}, Username: {user[1]}, Role: {user[3]}, Tokens: {user[4]}")
    
    print("\nChecking blacklist table:")
    cursor.execute("SELECT * FROM blacklist")
    blacklist = cursor.fetchall()
    for word in blacklist:
        print(f"ID: {word[0]}, Word: {word[1]}")
    
    print("\nChecking complaints table:")
    cursor.execute("SELECT * FROM complaints")
    complaints = cursor.fetchall()
    for complaint in complaints:
        print(f"ID: {complaint[0]}, Status: {complaint[4]}")
    
    conn.close()

if __name__ == "__main__":
    check_database() 