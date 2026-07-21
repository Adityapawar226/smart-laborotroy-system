import os
from dotenv import load_dotenv
from flask import Flask
from flask_bcrypt import Bcrypt
import mysql.connector

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

hashed = bcrypt.generate_password_hash("Tech123@").decode("utf-8")

cursor.execute("""
UPDATE users
SET password=%s
WHERE username='technician'
""", (hashed,))

db.commit()

cursor.close()
db.close()

print("Technician password created successfully.")