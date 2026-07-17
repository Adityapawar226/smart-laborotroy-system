import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Aditya@2264"
    )

    print("MySQL Connected Successfully")

except Exception as e:
    print("Error:", e)