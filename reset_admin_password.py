from flask import Flask
from flask_bcrypt import Bcrypt
import mysql.connector

app = Flask(__name__)
bcrypt = Bcrypt(app)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Aditya@2264",   # <-- Replace with your MySQL password
    database="smart_lab"
)

cursor = db.cursor()

new_password = bcrypt.generate_password_hash("admin123").decode("utf-8")

cursor.execute(
    "UPDATE users SET password=%s WHERE username=%s",
    (new_password, "admin")
)

db.commit()

print("Admin password reset successfully!")