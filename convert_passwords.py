import os
from pathlib import Path
from dotenv import load_dotenv

import pymysql
from flask_bcrypt import Bcrypt
from flask import Flask

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_SSL_CA = BASE_DIR / "aiven-ca.pem"

app = Flask(__name__)
bcrypt = Bcrypt(app)

ssl_config = {"ca": str(DB_SSL_CA)} if DB_SSL_CA.is_file() else None

db = pymysql.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "15054")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    ssl=ssl_config,
    connect_timeout=15
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