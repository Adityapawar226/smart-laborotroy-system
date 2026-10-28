import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from flask_bcrypt import Bcrypt
import pymysql

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