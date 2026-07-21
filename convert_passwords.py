import os
from dotenv import load_dotenv

import mysql.connector
from flask_bcrypt import Bcrypt
from flask import Flask

# Load environment variables
load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)

db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)

cursor = db.cursor()

cursor.execute("SELECT id, password FROM users")
users = cursor.fetchall()

for user in users:
    user_id = user[0]
    plain_password = user[1]

    # Skip already hashed passwords
    if plain_password.startswith("$2b$") or plain_password.startswith("$2a$"):
        continue

    hashed = bcrypt.generate_password_hash(
        plain_password
    ).decode("utf-8")

    cursor.execute(
        "UPDATE users SET password=%s WHERE id=%s",
        (hashed, user_id)
    )

db.commit()

cursor.close()
db.close()

print("All passwords converted successfully!")