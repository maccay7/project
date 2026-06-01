# backend/insert_user.py
import pymysql
from werkzeug.security import generate_password_hash

# Database connection
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='businessmogul',
    database='duracapital',
    cursorclass=pymysql.cursors.DictCursor
)

cursor = conn.cursor()

# Your user details
email = "makanakakanyai@gmail.com"
password = "Business7mogul"
first_name = "Makanaka"
last_name = "Kanyai"

# Generate proper password hash
password_hash = generate_password_hash(password)

print(f"📧 Email: {email}")
print(f"🔑 Password: {password}")
print(f"🔐 Hash: {password_hash[:50]}...")

# Check if user exists
cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
existing = cursor.fetchone()

if existing:
    print(f"\n User already exists (ID: {existing['id']})")
    print("Updating password hash...")
    cursor.execute(
        "UPDATE users SET password_hash = %s WHERE email = %s",
        (password_hash, email)
    )
else:
    print(f"\n Creating new user...")
    cursor.execute(
        """INSERT INTO users (email, password_hash, first_name, last_name, role) 
           VALUES (%s, %s, %s, %s, 'Administrator')""",
        (email, password_hash, first_name, last_name)
    )
    user_id = cursor.lastrowid
    print(f" User created with ID: {user_id}")
    
    # Create user preferences
    cursor.execute(
        """INSERT INTO user_preferences (user_id, language, timezone, date_format, currency) 
           VALUES (%s, 'English', 'GMT+2', 'DD/MM/YYYY', 'USD')""",
        (user_id,)
    )
    print(" User preferences created")

conn.commit()
print("\n Done! User is ready.")

# Verify the user
cursor.execute("SELECT id, email, first_name, last_name, role FROM users WHERE email = %s", (email,))
user = cursor.fetchone()
print(f"\n Verification:")
print(f"   ID: {user['id']}")
print(f"   Email: {user['email']}")
print(f"   Name: {user['first_name']} {user['last_name']}")
print(f"   Role: {user['role']}")

cursor.close()
conn.close()