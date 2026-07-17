import os
from dotenv import load_dotenv

from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler
from decimal import Decimal
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
from functools import wraps

print("=" * 50)
print("APP.PY LOADED")
print("=" * 50)
print("APP STARTED")

# Load .env file
load_dotenv()
print("=" * 50)
print("APP.PY LOADED")
print("=" * 50)

print("APP STARTED")

load_dotenv()

# Test if .env is loaded
print("DB_HOST:", os.getenv("DB_HOST"))
print("DB_NAME:", os.getenv("DB_NAME"))

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

bcrypt = Bcrypt(app)

app = Flask(__name__)

# Read SECRET_KEY from .env
app.secret_key = os.getenv("SECRET_KEY")

bcrypt = Bcrypt(app)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "lab_id" not in session:
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function
def role_required(*roles):

    def decorator(f):

        @wraps(f)
        def decorated_function(*args, **kwargs):

            if "user_id" not in session:
                return redirect(url_for("login"))

            if session.get("role") not in roles:
                return "403 Forbidden - You don't have permission to access this page.", 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    
    

UPLOAD_LOGO = "static/uploads/logo"
UPLOAD_SIGNATURE = "static/uploads/signature"
UPLOAD_STAMP = "static/uploads/stamp"

app.config["UPLOAD_LOGO"] = UPLOAD_LOGO
app.config["UPLOAD_SIGNATURE"] = UPLOAD_SIGNATURE
app.config["UPLOAD_STAMP"] = UPLOAD_STAMP

os.makedirs(UPLOAD_LOGO, exist_ok=True)
os.makedirs(UPLOAD_SIGNATURE, exist_ok=True)
os.makedirs(UPLOAD_STAMP, exist_ok=True)







@app.route("/", methods=["GET", "POST"])
def login():

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    try:

        if request.method == "POST":

            lab_id = request.form["lab_id"].strip().upper()
            username = request.form["username"].strip()
            password = request.form["password"]

            cursor.execute("""
                SELECT *
                FROM laboratories
                WHERE lab_id=%s
                AND username=%s
                AND status='Active'
            """, (lab_id, username))

            lab = cursor.fetchone()

            if lab and bcrypt.check_password_hash(lab["password"], password):

                session.clear()

                session["lab_id"] = lab["lab_id"]
                session["lab_name"] = lab["lab_name"]
                session["owner_name"] = lab["owner_name"]
                session["username"] = lab["username"]
                session["user_id"] = lab["id"]
                session["role"] = lab["role"]

                return redirect(url_for("dashboard"))

            flash("Invalid Lab ID, Username or Password", "danger")
            return redirect(url_for("login"))

        return render_template("login.html")

    finally:
        cursor.close()
        db.close()

@app.route("/logout")
@login_required
def logout():

    session.clear()

    return redirect(url_for("login"))
@app.route("/register-lab", methods=["GET", "POST"])
def register_lab():

    if request.method == "POST":

        db = get_db()
        cursor = db.cursor(buffered=True)

        try:

            lab_name = request.form["lab_name"].strip()
            owner_name = request.form["owner_name"].strip()
            mobile = request.form["mobile"].strip()
            email = request.form["email"].strip().lower()
            address = request.form["address"].strip()
            username = request.form["username"].strip()
            password = request.form["password"]
            confirm_password = request.form["confirm_password"]

            # -----------------------------
            # Password Validation
            # -----------------------------

            if password != confirm_password:
                flash("Passwords do not match.", "danger")
                return redirect(url_for("register_lab"))

            if len(password) < 8:
                flash("Password must be at least 8 characters.", "danger")
                return redirect(url_for("register_lab"))

            hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

            # -----------------------------
            # Username Exists?
            # -----------------------------

            cursor.execute("""
                SELECT id
                FROM laboratories
                WHERE username=%s
            """, (username,))

            if cursor.fetchone():
                flash("Username already exists.", "danger")
                return redirect(url_for("register_lab"))

            # -----------------------------
            # Email Exists?
            # -----------------------------

            cursor.execute("""
                SELECT id
                FROM laboratories
                WHERE email=%s
            """, (email,))

            if cursor.fetchone():
                flash("Email already registered.", "danger")
                return redirect(url_for("register_lab"))

            # -----------------------------
            # Mobile Exists?
            # -----------------------------

            cursor.execute("""
                SELECT id
                FROM laboratories
                WHERE mobile=%s
            """, (mobile,))

            if cursor.fetchone():
                flash("Mobile number already registered.", "danger")
                return redirect(url_for("register_lab"))

            # -----------------------------
            # Generate Lab ID
            # -----------------------------

            cursor.execute("""
                SELECT lab_id
                FROM laboratories
                ORDER BY id DESC
                LIMIT 1
            """)

            row = cursor.fetchone()

            if row:
                next_no = int(row[0].replace("LAB", "")) + 1
            else:
                next_no = 1

            lab_id = f"LAB{next_no:04d}"

            # -----------------------------
            # Insert Laboratory
            # -----------------------------

            cursor.execute("""
                INSERT INTO laboratories
                (
                    lab_id,
                    lab_name,
                    owner_name,
                    mobile,
                    email,
                    address,
                    username,
                    password
                )
                VALUES
                (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                lab_id,
                lab_name,
                owner_name,
                mobile,
                email,
                address,
                username,
                hashed_password
            ))

            # -----------------------------
            # Default Settings
            # -----------------------------

            cursor.execute("""
                INSERT INTO lab_settings
                (
                    lab_id,
                    lab_name,
                    owner_name,
                    mobile,
                    email,
                    address,
                    patient_prefix,
                    receipt_prefix
                )
                VALUES
                (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                lab_id,
                lab_name,
                owner_name,
                mobile,
                email,
                address,
                "PAT",
                "RCPT"
            ))

            db.commit()

            return render_template(
                "registration_success.html",
                lab_id=lab_id,
                username=username
            )

        except Exception as e:

            db.rollback()
            raise e

        finally:

            cursor.close()
            db.close()

    return render_template("register_lab.html")


@app.route("/dashboard")
@login_required
@role_required("Developer", "Admin", "Technician")
def dashboard():

    db = get_db()
    cursor = db.cursor(buffered=True)

    try:

        lab_id = session["lab_id"]
        search = request.args.get("search", "").strip()

        # -----------------------------
        # Recent Registrations
        # -----------------------------

        if search == "":

            cursor.execute("""
        SELECT
            
            p.patient_id,
            p.name,
            p.age,
            GROUP_CONCAT(t.test_name SEPARATOR ', ') AS tests,
            pay.total_amount,
            pay.payment_mode,
            pay.payment_status
        FROM patients p
        JOIN patient_tests pt
            ON p.patient_id = pt.patient_id
            AND p.lab_id = pt.lab_id
        JOIN tests t
            ON pt.test_id = t.id
            AND pt.lab_id = t.lab_id
        JOIN payments pay
            ON p.patient_id = pay.patient_id
            AND p.lab_id = pay.lab_id
        WHERE p.lab_id=%s
        GROUP BY
            p.id,
            p.patient_id,
            p.name,
            p.age,
            pay.total_amount,
            pay.payment_mode,
            pay.payment_status
        
        LIMIT 10
        """, (lab_id,))

        else:

            cursor.execute("""
        SELECT
            p.patient_id,
            p.name,
            p.age,
            GROUP_CONCAT(t.test_name SEPARATOR ', ') AS tests,
            pay.total_amount,
            pay.payment_mode,
            pay.payment_status
        FROM patients p
        JOIN patient_tests pt
            ON p.patient_id = pt.patient_id
            AND p.lab_id = pt.lab_id
        JOIN tests t
            ON pt.test_id = t.id
            AND pt.lab_id = t.lab_id
        JOIN payments pay
            ON p.patient_id = pay.patient_id
            AND p.lab_id = pay.lab_id
        WHERE
            p.lab_id=%s
            AND (
                p.patient_id LIKE %s
                OR p.name LIKE %s
                OR p.mobile LIKE %s
            )
        GROUP BY
            p.id
            p.patient_id,
            p.name,
            p.age,
            pay.total_amount,
            pay.payment_mode,
            pay.payment_status
        
        """, (
                lab_id,
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            ))

        patients = cursor.fetchall()

        # -----------------------------
        # Latest Payments
        # -----------------------------

        cursor.execute("""
    SELECT
        p.receipt_no,
        pa.name,
        p.total_amount,
        p.payment_mode,
        p.payment_status
    FROM payments p
    JOIN patients pa
        ON p.patient_id = pa.patient_id
        AND p.lab_id = pa.lab_id
    WHERE p.lab_id=%s
    ORDER BY p.id DESC
    LIMIT 10
    """, (lab_id,))

        payments = cursor.fetchall()

            # -----------------------------
        # Today's Patient Count
        # -----------------------------
        cursor.execute("""
    SELECT COUNT(*)
    FROM patients
    WHERE DATE(created_at)=CURDATE()
    AND lab_id=%s
    """, (lab_id,))
        patient_count = cursor.fetchone()[0]

        # -----------------------------
        # Today's Income
        # -----------------------------
        cursor.execute("""
    SELECT IFNULL(SUM(amount),0)
    FROM payment_transactions
    WHERE DATE(payment_date)=CURDATE()
    AND lab_id=%s
    """, (lab_id,))
        total_income = cursor.fetchone()[0]

        # -----------------------------
        # Pending Amount
        # -----------------------------
        cursor.execute("""
    SELECT IFNULL(SUM(remaining_amount),0)
    FROM payments
    WHERE payment_status='Pending'
    AND lab_id=%s
    """, (lab_id,))
        pending_amount = cursor.fetchone()[0]

        # -----------------------------
        # Cash Collection
        # -----------------------------
        cursor.execute("""
    SELECT IFNULL(SUM(amount),0)
    FROM payment_transactions
    WHERE payment_mode='Cash'
    AND MONTH(payment_date)=MONTH(CURDATE())
    AND YEAR(payment_date)=YEAR(CURDATE())
    AND lab_id=%s
    """, (lab_id,))
        cash_total = cursor.fetchone()[0]

        # -----------------------------
        # UPI Collection
        # -----------------------------
        cursor.execute("""
    SELECT IFNULL(SUM(amount),0)
    FROM payment_transactions
    WHERE payment_mode='UPI'
    AND MONTH(payment_date)=MONTH(CURDATE())
    AND YEAR(payment_date)=YEAR(CURDATE())
    AND lab_id=%s
    """, (lab_id,))
        upi_total = cursor.fetchone()[0]

        # -----------------------------
        # Cash Count
        # -----------------------------
        cursor.execute("""
    SELECT COUNT(*)
    FROM payment_transactions
    WHERE payment_mode='Cash'
    AND MONTH(payment_date)=MONTH(CURDATE())
    AND YEAR(payment_date)=YEAR(CURDATE())
    AND lab_id=%s
    """, (lab_id,))
        cash_count = cursor.fetchone()[0]

        # -----------------------------
        # UPI Count
        # -----------------------------
        cursor.execute("""
    SELECT COUNT(*)
    FROM payment_transactions
    WHERE payment_mode='UPI'
    AND MONTH(payment_date)=MONTH(CURDATE())
    AND YEAR(payment_date)=YEAR(CURDATE())
    AND lab_id=%s
    """, (lab_id,))
        upi_count = cursor.fetchone()[0]

        # -----------------------------
        # Total Patients
        # -----------------------------
        cursor.execute("""
    SELECT COUNT(*)
    FROM patients
    WHERE lab_id=%s
    """, (lab_id,))
        total_patients = cursor.fetchone()[0]

        # -----------------------------
        # Grand Total Income
        # -----------------------------
        cursor.execute("""
    SELECT IFNULL(SUM(amount),0)
    FROM payment_transactions
    WHERE lab_id=%s
    """, (lab_id,))
        grand_total_income = cursor.fetchone()[0]

        # -----------------------------
        # Total Tests
        # -----------------------------
        cursor.execute("""
    SELECT COUNT(*)
    FROM patient_tests
    WHERE lab_id=%s
    """, (lab_id,))
        total_tests = cursor.fetchone()[0]

        # -----------------------------
        # Total Reports
        # -----------------------------
        cursor.execute("""
    SELECT COUNT(DISTINCT patient_id)
    FROM test_results
    WHERE lab_id=%s
    """, (lab_id,))
        total_reports = cursor.fetchone()[0]

        current_time = datetime.now().strftime("%d %B %Y | %I:%M %p")

        return render_template(
            "dashboard.html",
            patients=patients,
            search=search,
            payments=payments,
            patient_count=patient_count,
            total_income=total_income,
            pending_amount=pending_amount,
            cash_total=cash_total,
            upi_total=upi_total,
            cash_count=cash_count,
            upi_count=upi_count,
            current_time=current_time,
            total_patients=total_patients,
            grand_total_income=grand_total_income,
            total_tests=total_tests,
            total_reports=total_reports
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()
@app.route("/patient-registration", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin", "Technician")
def patient_registration():

    db = get_db()
    cursor = db.cursor( buffered=True)
    try:
       lab_id = session["lab_id"]

       if request.method == "POST":

        # -------------------------------
        # Patient Details
        # -------------------------------
        name = request.form["name"]

        age = request.form.get("age")
        age = int(age) if age else None

        gender = request.form["gender"]
        mobile = request.form["mobile"]
        address = request.form["address"]

        doctor_id = request.form["doctor_id"]

        cursor.execute("""
SELECT doctor_name
FROM doctors
WHERE id=%s
AND lab_id=%s
""", (doctor_id, lab_id))

        doctor_name = cursor.fetchone()[0]

        payment_mode = request.form["payment_mode"]

        paid_amount = float(request.form.get("paid_amount") or 0)

        selected_tests = request.form.getlist("tests")
        patient_prices = request.form.getlist("patient_price")

        # -------------------------------
        # Generate Patient ID
        # -------------------------------

        cursor.execute("""
SELECT patient_prefix
FROM lab_settings
WHERE lab_id=%s
LIMIT 1
""", (lab_id,))

        prefix = cursor.fetchone()

        patient_prefix = prefix[0] if prefix and prefix[0] else "PAT"

        cursor.execute("""
SELECT IFNULL(MAX(id),0)
FROM patients
WHERE lab_id=%s
""", (lab_id,))

        next_no = cursor.fetchone()[0] + 1

        current_year = datetime.now().year

        patient_id = f"{lab_id}-{patient_prefix}-{current_year}-{next_no:04d}"

        # -------------------------------
        # Save Patient
        # -------------------------------

        sample_types = set()

        for test_name in selected_tests:

            cursor.execute("""
SELECT sample_type
FROM tests
WHERE test_name=%s
AND lab_id=%s
""", (test_name, lab_id))

            row = cursor.fetchone()

            if row and row[0]:
                sample_types.add(row[0])

        collected_on = datetime.now()

        print("Selected Tests:", selected_tests)
        print("Collected On:", collected_on)

        cursor.execute("""
INSERT INTO patients
(
lab_id,
patient_id,
name,
age,
gender,
mobile,
address,
doctor_name,
doctor_id,
collected_on
)
VALUES
(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
""",
(
     lab_id,
    patient_id,
    name,
    age,
    gender,
    mobile,
    address,
    doctor_name,
    doctor_id,
    collected_on
))

        cursor.execute("""
SELECT collected_on
FROM patients
WHERE patient_id=%s
AND lab_id=%s
""", (patient_id, lab_id))

        print("Saved collected_on =", cursor.fetchone())
              # -------------------------------
        # Save Tests
        # -------------------------------

        total_amount = 0

        for i, test_name in enumerate(selected_tests):

            cursor.execute("""
SELECT id
FROM tests
WHERE test_name=%s
AND lab_id=%s
""", (test_name, lab_id))

            test = cursor.fetchone()

            if test:

                test_id = test[0]

                amount = float(patient_prices[i])

                total_amount += amount

                cursor.execute("""
INSERT INTO patient_tests
(
lab_id,
patient_id,
test_id,
amount
)
VALUES(%s,%s,%s,%s)
""",
(
    lab_id,
    patient_id,
    test_id,
    amount
))

        # -------------------------------
        # Payment Calculation
        # -------------------------------

        remaining_amount = total_amount - paid_amount

        if remaining_amount < 0:
            remaining_amount = 0

        payment_status = "Paid" if remaining_amount == 0 else "Pending"

        # -------------------------------
        # Save Payment
        # -------------------------------

        cursor.execute("""
INSERT INTO payments
(
lab_id,
patient_id,
mobile,
total_amount,
paid_amount,
remaining_amount,
payment_mode,
payment_status
)
VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
""",
(
    lab_id,
    patient_id,
    mobile,
    total_amount,
    paid_amount,
    remaining_amount,
    payment_mode,
    payment_status
))

        payment_id = cursor.lastrowid

        cursor.execute("""
SELECT receipt_prefix
FROM lab_settings
WHERE lab_id=%s
LIMIT 1
""", (lab_id,))

        prefix = cursor.fetchone()

        receipt_prefix = prefix[0] if prefix and prefix[0] else "RCPT"

        current_year = datetime.now().year

        receipt_no = f"{lab_id}-{receipt_prefix}-{current_year}-{payment_id:04d}"

        cursor.execute("""
UPDATE payments
SET receipt_no=%s
WHERE id=%s
AND lab_id=%s
""",
(
    receipt_no,
    payment_id,
    lab_id
))

        # -------------------------------
        # Save Payment Transaction
        # -------------------------------

        if paid_amount > 0:

            cursor.execute("""
INSERT INTO payment_transactions
(
    lab_id,
    patient_id,
    receipt_no,
    amount,
    payment_mode,
    remarks
)
VALUES(%s,%s,%s,%s,%s,%s)
""",
(
    lab_id,
    patient_id,
    receipt_no,
    paid_amount,
    payment_mode,
    "Registration Payment"
))

        # -------------------------------
        # Save Pending Payment
        # -------------------------------

        if payment_status == "Pending":

            cursor.execute("""
INSERT INTO pending_payments
(
    lab_id,
    receipt_no,
    patient_id,
    patient_name,
    mobile,
    report_date,
    due_date,
    pending_amount,
    paid_amount,
    total_amount,
    status
)
VALUES
(
    %s,
    %s,
    %s,
    %s,
    %s,
    CURDATE(),
    DATE_ADD(CURDATE(), INTERVAL 7 DAY),
    %s,
    %s,
    %s,
    'Pending'
)
""",
(
    lab_id,
    receipt_no,
    patient_id,
    name,
    mobile,
    remaining_amount,
    paid_amount,
    total_amount
))

        db.commit()

        return redirect("/dashboard")

    # -------------------------------
    # Load Tests
    # -------------------------------

       cursor.execute("""
SELECT
    id,
    test_name,
    price
FROM tests
WHERE lab_id=%s
ORDER BY test_name
""", (lab_id,))

       tests = cursor.fetchall()

    # -------------------------------
    # Load Doctors
    # -------------------------------

       cursor.execute("""
SELECT
    id,
    doctor_name
FROM doctors
WHERE status='Active'
AND lab_id=%s
ORDER BY doctor_name
""", (lab_id,))

       doctors = cursor.fetchall()

       return render_template(
        "patient_registration.html",
        tests=tests,
        doctors=doctors
    )
    except Exception:
       db.rollback()
       raise

    finally:
        cursor.close()
        db.close()
@app.route("/pending-payments")
@login_required
@role_required("Developer", "Admin", "Technician")
def pending_payments():

    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor(buffered=True)

    try:

        cursor.execute("""
        SELECT
            id,
            receipt_no,
            patient_id,
            patient_name,
            mobile,
            total_amount,
            paid_amount,
            pending_amount,
            report_date,
            due_date,
            status
        FROM pending_payments
        WHERE status='Pending'
        AND lab_id=%s
        ORDER BY id DESC
        """, (lab_id,))

        data = cursor.fetchall()

        return render_template(
            "pending_payments.html",
            data=data
        )

    finally:
        cursor.close()
        db.close()
@app.route("/mark-paid/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin", "Technician")
def mark_paid(id):

    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    try:

        # -----------------------------
        # Load Pending Payment
        # -----------------------------
        cursor.execute("""
            SELECT *
            FROM pending_payments
            WHERE id=%s
            AND lab_id=%s
        """, (id, lab_id))

        pending = cursor.fetchone()

        if not pending:
            return "Pending payment not found"

        if request.method == "POST":

            amount = float(request.form["amount"])
            payment_mode = request.form["payment_mode"]

            patient_id = pending["patient_id"]

            # -----------------------------
            # Load Current Payment
            # -----------------------------
            cursor.execute("""
                SELECT
                    paid_amount,
                    remaining_amount,
                    total_amount
                FROM payments
                WHERE patient_id=%s
                AND lab_id=%s
            """, (patient_id, lab_id))

            payment = cursor.fetchone()

            old_paid = float(payment["paid_amount"])
            old_remaining = float(payment["remaining_amount"])
            total_amount = float(payment["total_amount"])

            # -----------------------------
            # Validation
            # -----------------------------
            if amount <= 0:
                return "Invalid amount"

            if amount > old_remaining:
                return "Amount is greater than remaining balance"

            new_paid = old_paid + amount
            new_remaining = old_remaining - amount

            status = "Paid" if new_remaining == 0 else "Pending"

            # -----------------------------
            # Update Payments
            # -----------------------------
            cursor.execute("""
                UPDATE payments
                SET
                    paid_amount=%s,
                    remaining_amount=%s,
                    payment_status=%s,
                    payment_mode=%s
                WHERE patient_id=%s
                AND lab_id=%s
            """,
            (
                new_paid,
                new_remaining,
                status,
                payment_mode,
                patient_id,
                lab_id
            ))

            # -----------------------------
            # Update Pending Payments
            # -----------------------------
            cursor.execute("""
                UPDATE pending_payments
                SET
                    paid_amount=%s,
                    pending_amount=%s,
                    status=%s
                WHERE id=%s
                AND lab_id=%s
            """,
            (
                new_paid,
                new_remaining,
                status,
                id,
                lab_id
            ))

            # -----------------------------
            # Save Payment Transaction
            # -----------------------------
            cursor.execute("""
                INSERT INTO payment_transactions
                (
                    lab_id,
                    patient_id,
                    receipt_no,
                    amount,
                    payment_mode,
                    remarks
                )
                VALUES(%s,%s,%s,%s,%s,%s)
            """,
            (
                lab_id,
                patient_id,
                pending["receipt_no"],
                amount,
                payment_mode,
                "Pending Payment"
            ))

            db.commit()

            return redirect(url_for("pending_payments"))

        return render_template(
            "collect_payment.html",
            pending=pending
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()
    
@app.route("/collect-payment/<int:payment_id>", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin", "Technician")
def collect_payment(payment_id):

    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    try:

        # -----------------------------
        # Load Pending Payment
        # -----------------------------
        cursor.execute("""
            SELECT *
            FROM pending_payments
            WHERE id=%s
            AND lab_id=%s
        """, (payment_id, lab_id))

        payment = cursor.fetchone()

        if not payment:
            return "Payment not found."

        if request.method == "POST":

            receive_amount = Decimal(request.form["receive_amount"])
            payment_mode = request.form["payment_mode"]

            new_paid = payment["paid_amount"] + receive_amount
            new_remaining = payment["total_amount"] - new_paid

            if new_remaining <= Decimal("0.00"):
                new_remaining = Decimal("0.00")
                status = "Paid"
            else:
                status = "Pending"

            # -----------------------------
            # Update Payments
            # -----------------------------
            cursor.execute("""
                UPDATE payments
                SET
                    paid_amount=%s,
                    remaining_amount=%s,
                    payment_status=%s,
                    payment_mode=%s,
                    payment_date=NOW()
                WHERE patient_id=%s
                AND lab_id=%s
            """,
            (
                new_paid,
                new_remaining,
                status,
                payment_mode,
                payment["patient_id"],
                lab_id
            ))

            # -----------------------------
            # Update Pending Payments
            # -----------------------------
            cursor.execute("""
                UPDATE pending_payments
                SET
                    paid_amount=%s,
                    pending_amount=%s,
                    status=%s
                WHERE id=%s
                AND lab_id=%s
            """,
            (
                new_paid,
                new_remaining,
                status,
                payment_id,
                lab_id
            ))

            # -----------------------------
            # Save Payment Transaction
            # -----------------------------
            cursor.execute("""
                INSERT INTO payment_transactions
                (
                    lab_id,
                    patient_id,
                    receipt_no,
                    amount,
                    payment_mode,
                    remarks
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """,
            (
                lab_id,
                payment["patient_id"],
                payment["receipt_no"],
                receive_amount,
                payment_mode,
                "Pending Payment"
            ))

            db.commit()

            return redirect(url_for("pending_payments"))

        return render_template(
            "collect_payment.html",
            payment=payment
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()
@app.route("/reports-management")
@login_required
@role_required("Developer", "Admin", "Technician")
def reports_management():

    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor(buffered=True)

    try:

        cursor.execute("""
        SELECT
            p.patient_id,
            p.name,
            GROUP_CONCAT(DISTINCT t.test_name SEPARATOR ', ') AS tests,

            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM test_results tr
                    WHERE tr.patient_id = p.patient_id
                    AND tr.lab_id = p.lab_id
                )
                THEN 'Completed'
                ELSE 'Pending'
            END AS report_status

        FROM patients p

        LEFT JOIN patient_tests pt
            ON p.patient_id = pt.patient_id
            AND p.lab_id = pt.lab_id

        LEFT JOIN tests t
            ON pt.test_id = t.id
            AND pt.lab_id = t.lab_id

        WHERE p.lab_id=%s

       GROUP BY
            p.id,
            p.patient_id,
            p.name

        ORDER BY p.id DESC
        """, (lab_id,))

        reports = cursor.fetchall()

        total_reports = len(reports)

        completed_reports = sum(
            1 for r in reports if r[3] == "Completed"
        )

        pending_reports = sum(
            1 for r in reports if r[3] != "Completed"
        )

        today_reports = completed_reports

        return render_template(
            "reports_management.html",
            reports=reports,
            total_reports=total_reports,
            completed_reports=completed_reports,
            pending_reports=pending_reports,
            today_reports=today_reports
        )

    finally:
        cursor.close()
        db.close()
@app.route("/enter-results/<patient_id>", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin", "Technician")
def enter_results(patient_id):

    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor(buffered=True)

    try:

        if request.method == "POST":

            # Delete old results
            cursor.execute("""
                DELETE FROM test_results
                WHERE patient_id=%s
                AND lab_id=%s
            """, (patient_id, lab_id))

            for key, value in request.form.items():

                if value.strip() == "":
                    continue

                test_name, parameter_name = key.rsplit("_", 1)

                cursor.execute("""
                    SELECT
                        unit,
                        reference_range
                    FROM test_parameters
                    WHERE test_name=%s
                    AND parameter_name=%s
                    AND lab_id=%s
                """, (
                    test_name,
                    parameter_name,
                    lab_id
                ))

                param_data = cursor.fetchone()

                if param_data is None:
                    print("Parameter not found:", test_name, parameter_name)
                    continue

                unit = param_data[0]
                reference_range = param_data[1]

                cursor.execute("""
                    INSERT INTO test_results
                    (
                        lab_id,
                        patient_id,
                        test_name,
                        parameter_name,
                        result_value,
                        unit,
                        reference_range,
                        entry_mode
                    )
                    VALUES
                    (%s,%s,%s,%s,%s,%s,%s,'Manual')
                """,
                (
                    lab_id,
                    patient_id,
                    test_name,
                    parameter_name,
                    value,
                    unit,
                    reference_range
                ))

            db.commit()

            print("RESULTS SAVED")

            return redirect(url_for("reports_management"))

        # -----------------------------
        # Patient Details
        # -----------------------------

        cursor.execute("""
            SELECT
                patient_id,
                name
            FROM patients
            WHERE patient_id=%s
            AND lab_id=%s
        """, (
            patient_id,
            lab_id
        ))

        patient = cursor.fetchone()

        if patient is None:
            return "Patient not found", 404

        # -----------------------------
        # Patient Tests
        # -----------------------------

        cursor.execute("""
            SELECT
                t.test_name
            FROM patient_tests pt

            JOIN tests t
                ON pt.test_id=t.id
                AND pt.lab_id=t.lab_id

            WHERE pt.patient_id=%s
            AND pt.lab_id=%s
        """, (
            patient_id,
            lab_id
        ))

        tests = cursor.fetchall()

        all_parameters = {}

        for test in tests:

            test_name = test[0]

            cursor.execute("""
                SELECT
                    parameter_name,
                    unit,
                    reference_range
                FROM test_parameters
                WHERE test_name=%s
                AND lab_id=%s
            """, (
                test_name,
                lab_id
            ))

            all_parameters[test_name] = cursor.fetchall()

        # -----------------------------
        # Update Report Generated Date
        # -----------------------------

        cursor.execute("""
            UPDATE patients
            SET report_generated_on=NOW()
            WHERE patient_id=%s
            AND lab_id=%s
        """, (
            patient_id,
            lab_id
        ))

        db.commit()

        return render_template(
            "enter_results.html",
            patient=patient,
            parameters=all_parameters
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()
@app.route("/view-report/<patient_id>")
@login_required
@role_required("Developer", "Admin", "Technician")
def view_report(patient_id):

    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor(buffered=True)

    try:

        # -----------------------------
        # Patient Details
        # -----------------------------
        cursor.execute("""
        SELECT
            name,
            age,
            gender,
            doctor_name,
            collected_on,
            report_generated_on
        FROM patients
        WHERE patient_id=%s
        AND lab_id=%s
        LIMIT 1
        """, (patient_id, lab_id))

        patient = cursor.fetchone()

        if patient is None:
            return "Patient not found", 404

        # -----------------------------
        # Report Results
        # -----------------------------
        cursor.execute("""
        SELECT
            tr.patient_id,
            tr.test_name,
            tr.parameter_name,
            tr.result_value,
            tr.unit,
            tr.reference_range,
            tp.section,
            tp.display_order,
            t.department,
            t.sample_type

        FROM test_results tr

        LEFT JOIN test_parameters tp
            ON tr.test_name = tp.test_name
            AND tr.parameter_name = tp.parameter_name
            AND tr.lab_id = tp.lab_id

        LEFT JOIN tests t
            ON tr.test_name = t.test_name
            AND tr.lab_id = t.lab_id

        WHERE tr.patient_id=%s
        AND tr.lab_id=%s

        ORDER BY
            t.department,
            tr.test_name,
            tp.section,
            tp.display_order
        """, (patient_id, lab_id))

        db_results = cursor.fetchall()

        grouped_results = {}

        for row in db_results:

            pid = row[0]
            test_name = row[1]
            parameter = row[2]
            result = row[3]
            unit = row[4]
            reference = row[5]

            section = row[6]
            display_order = row[7]
            department = row[8]
            sample_type = row[9]

            display_result = result
            status = "normal"

            try:

                value = float(result)

                if "-" in reference:

                    low, high = reference.split("-")

                    low = float(low.strip())
                    high = float(high.strip())

                    if value < low:
                        display_result = f"↓ {result}"
                        status = "low"

                    elif value > high:
                        display_result = f"↑ {result}"
                        status = "high"

            except:
                pass

            if test_name not in grouped_results:

                grouped_results[test_name] = {
                    "department": department,
                    "sample_type": sample_type,
                    "section": section,
                    "rows": []
                }

            grouped_results[test_name]["rows"].append({

                "parameter": parameter,
                "section": section,
                "result": display_result,
                "unit": unit,
                "reference": reference,
                "status": status

            })

        return render_template(
            "view_report.html",
            patient_id=patient_id,
            patient_name=patient[0],
            age_gender=f"{patient[1]} Years / {patient[2]}",
            doctor_name=patient[3],
            collection_date=patient[4],
            report_date=patient[5],
            results=grouped_results
        )

    finally:
        cursor.close()
        db.close()
@app.route("/edit-report/<patient_id>", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin")
def edit_report(patient_id):

    db = get_db()
    cursor = db.cursor(buffered=True)
    lab_id = session["lab_id"]

    try:

        if request.method == "POST":

            # ---------------- Existing Result IDs ----------------
            cursor.execute("""
                SELECT id
                FROM test_results
                WHERE patient_id=%s
                AND lab_id=%s
                ORDER BY test_name
            """, (patient_id, lab_id))

            ids = cursor.fetchall()

            for i, row in enumerate(ids, start=1):

                new_value = request.form.get(f"result_{i}")

                cursor.execute("""
                    UPDATE test_results
                    SET result_value=%s
                    WHERE id=%s
                    AND lab_id=%s
                """, (
                    new_value,
                    row[0],
                    lab_id
                ))

            db.commit()

            return redirect(url_for(
                "view_report",
                patient_id=patient_id
            ))

        # ---------------- Patient Details ----------------

        cursor.execute("""
            SELECT
                name,
                age,
                gender,
                doctor_name
            FROM patients
            WHERE patient_id=%s
            AND lab_id=%s
        """, (
            patient_id,
            lab_id
        ))

        patient = cursor.fetchone()

        if patient is None:
            return "Patient not found", 404

        # ---------------- Existing Results ----------------

        cursor.execute("""
            SELECT
                id,
                patient_id,
                test_name,
                parameter_name,
                result_value,
                unit,
                reference_range
            FROM test_results
            WHERE patient_id=%s
            AND lab_id=%s
            ORDER BY test_name
        """, (
            patient_id,
            lab_id
        ))

        results = cursor.fetchall()

        return render_template(
            "edit_report.html",
            patient=patient,
            patient_id=patient_id,
            results=results
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()
@app.route("/delete-report/<patient_id>", methods=["POST"])
@login_required
@role_required("Developer", "Admin")
def delete_report(patient_id):

    db = get_db()
    cursor = db.cursor(buffered=True)
    lab_id = session["lab_id"]

    try:

        cursor.execute("""
            DELETE FROM test_results
            WHERE patient_id=%s
            AND lab_id=%s
        """, (
            patient_id,
            lab_id
        ))

        db.commit()

        return redirect(url_for("reports_management"))

    except Exception as e:

        db.rollback()

        return f"Error deleting report: {e}"

    finally:

        cursor.close()
        db.close()
@app.route("/analytics")
@login_required
@role_required("Developer", "Admin", "Technician")
def analytics():

    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor(buffered=True)

    try:

        from_date = request.args.get("from_date")
        to_date = request.args.get("to_date")
    # -----------------------------
    # Total Income
    # -----------------------------
        if from_date and to_date:

         cursor.execute("""
        SELECT IFNULL(SUM(paid_amount),0)
        FROM payments
        WHERE lab_id=%s
        AND DATE(payment_date) BETWEEN %s AND %s
        """, (
            lab_id,
            from_date,
            to_date
        ))

        else:

           cursor.execute("""
        SELECT IFNULL(SUM(paid_amount),0)
        FROM payments
        WHERE lab_id=%s
        """, (lab_id,))

        total_income = cursor.fetchone()[0]

    # -----------------------------
    # Cash Income
    # -----------------------------
        if from_date and to_date:

         cursor.execute("""
        SELECT IFNULL(SUM(paid_amount),0)
        FROM payments
        WHERE lab_id=%s
        AND payment_mode='Cash'
        
        AND DATE(payment_date) BETWEEN %s AND %s
        """, (
            lab_id,
            from_date,
            to_date
        ))

        else:

         cursor.execute("""
        SELECT IFNULL(SUM(paid_amount),0)
        FROM payments
        WHERE lab_id=%s
        AND payment_mode='Cash'
        
        """, (lab_id,))

        cash_income = cursor.fetchone()[0]

    # -----------------------------
    # UPI Income
    # -----------------------------
        if from_date and to_date:

         cursor.execute("""
        SELECT IFNULL(SUM(paid_amount),0)
        FROM payments
        WHERE lab_id=%s
        AND payment_mode='UPI'
       
        AND DATE(payment_date) BETWEEN %s AND %s
        """, (
            lab_id,
            from_date,
            to_date
        ))

        else:

         cursor.execute("""
        SELECT IFNULL(SUM(paid_amount),0)
        FROM payments
        WHERE lab_id=%s
        AND payment_mode='UPI'
        
        """, (lab_id,))

        upi_income = cursor.fetchone()[0]

    # Daily Income Graph
       # -----------------------------
    # Daily Income Graph
    # -----------------------------
        if from_date and to_date:

          cursor.execute("""
        SELECT
            DATE(payment_date),
            SUM(paid_amount)
        FROM payments
        WHERE lab_id=%s
        AND DATE(payment_date) BETWEEN %s AND %s
        GROUP BY DATE(payment_date)
        ORDER BY DATE(payment_date)
        """, (
            lab_id,
            from_date,
            to_date
        ))

        else:

         cursor.execute("""
        SELECT
            DATE(payment_date),
            SUM(paid_amount)
        FROM payments
        WHERE lab_id=%s
        GROUP BY DATE(payment_date)
        ORDER BY DATE(payment_date)
        """, (lab_id,))

        daily_data = cursor.fetchall()

        dates = [str(row[0]) for row in daily_data]
        amounts = [float(row[1]) for row in daily_data]

    # -----------------------------
    # Monthly Income
    # -----------------------------
        cursor.execute("""
    SELECT
        DATE_FORMAT(payment_date,'%Y-%m'),
        SUM(paid_amount)
    FROM payments
    WHERE lab_id=%s
    GROUP BY DATE_FORMAT(payment_date,'%Y-%m')
    ORDER BY DATE_FORMAT(payment_date,'%Y-%m')
    """, (lab_id,))

        monthly_data = cursor.fetchall()

        monthly_income = monthly_data

    # -----------------------------
    # Top Revenue Tests
    # -----------------------------
        cursor.execute("""
    SELECT
        t.test_name,
        SUM(pt.amount) AS revenue
    FROM patient_tests pt

    JOIN tests t
        ON pt.test_id=t.id
        AND pt.lab_id=t.lab_id

    WHERE pt.lab_id=%s

    GROUP BY t.test_name

    ORDER BY revenue DESC

    LIMIT 5
    """, (lab_id,))

        top_tests = cursor.fetchall()

        test_names = [row[0] for row in top_tests]
        test_revenue = [float(row[1]) for row in top_tests]

    # -----------------------------
    # Patient Trend
    # -----------------------------
        cursor.execute("""
    SELECT
        DATE(created_at),
        COUNT(*)
    FROM patients
    WHERE lab_id=%s
    GROUP BY DATE(created_at)
    ORDER BY DATE(created_at)
    """, (lab_id,))

        patient_trend = cursor.fetchall()
  
        patient_dates = [str(row[0]) for row in patient_trend]
        patient_counts = [row[1] for row in patient_trend]
  
        return render_template(
            "analytics.html",
            total_income=total_income,
            cash_income=cash_income,
            upi_income=upi_income,
            dates=dates,
            amounts=amounts,
            from_date=from_date,
            to_date=to_date,
            monthly_income=monthly_income,
            test_names=test_names,
            test_revenue=test_revenue,
            patient_dates=patient_dates,
            patient_counts=patient_counts,
        )

    finally:
        cursor.close()
        db.close()
    

@app.route("/billing")
@login_required
@role_required("Developer", "Admin", "Technician")
def billing():

    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor(buffered=True)

    try:

        cursor.execute("""
        SELECT
            p.receipt_no,
            pa.patient_id,
            pa.name,
            p.total_amount,
            p.payment_mode,
            p.payment_status,
            p.payment_date

        FROM payments p

        JOIN patients pa
            ON p.patient_id = pa.patient_id
            AND p.lab_id = pa.lab_id

        WHERE p.lab_id=%s

        ORDER BY p.id DESC
        """, (lab_id,))

        bills = cursor.fetchall()

        return render_template(
            "billing.html",
            bills=bills
        )

    finally:
        cursor.close()
        db.close()

@app.route("/view-bill/<patient_id>")
@login_required
@role_required("Developer", "Admin", "Technician")
def view_bill(patient_id):

    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor(buffered=True)

    try:

        # -------- Bill Details --------
        cursor.execute("""
        SELECT
            p.receipt_no,
            pa.patient_id,
            pa.name,
            pa.age,
            pa.gender,
            pa.doctor_name,
            p.total_amount,
            p.paid_amount,
            p.remaining_amount,
            p.payment_mode,
            p.payment_status,
            p.payment_date

        FROM payments p

        JOIN patients pa
            ON p.patient_id = pa.patient_id
            AND p.lab_id = pa.lab_id

        WHERE pa.patient_id=%s
        AND pa.lab_id=%s
        """, (
            patient_id,
            lab_id
        ))

        bill = cursor.fetchone()

        if bill is None:
            return "Bill not found"

        # -------- Test Details --------
        cursor.execute("""
        SELECT
            t.test_name,
            pt.amount

        FROM patient_tests pt

        JOIN tests t
            ON pt.test_id=t.id
            AND pt.lab_id=t.lab_id

        WHERE pt.patient_id=%s
        AND pt.lab_id=%s
        """, (
            patient_id,
            lab_id
        ))

        tests = cursor.fetchall()

        print("\n===== BILL =====")
        print(bill)

        print("\n===== TESTS =====")
        for t in tests:
            print(t)

        return render_template(
            "view_bill.html",
            bill=bill,
            tests=tests
        )

    finally:
        cursor.close()
        db.close()
@app.route("/patient-search")
@login_required
@role_required("Developer", "Admin", "Technician")
def patient_search():

    db = get_db()
    cursor = db.cursor(buffered=True)
    lab_id = session["lab_id"]

    try:

        search = request.args.get("search", "").strip()

        if search == "":

            cursor.execute("""
                SELECT
                    patient_id,
                    name,
                    age,
                    gender,
                    mobile,
                    doctor_name
                FROM patients
                WHERE lab_id=%s
                ORDER BY id DESC
                LIMIT 20
            """, (lab_id,))

        else:

            cursor.execute("""
                SELECT
                    patient_id,
                    name,
                    age,
                    gender,
                    mobile,
                    doctor_name
                FROM patients
                WHERE lab_id=%s
                AND
                (
                    patient_id LIKE %s
                    OR name LIKE %s
                    OR mobile LIKE %s
                )
                ORDER BY id DESC
            """,
            (
                lab_id,
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            ))

        patients = cursor.fetchall()

        return render_template(
            "patient_search.html",
            patients=patients,
            search=search
        )

    finally:
        cursor.close()
        db.close()
@app.route("/test-management")
@login_required
@role_required("Developer", "Admin", "Technician")
def test_management():

    db = get_db()
    cursor = db.cursor(buffered=True)

    lab_id = session["lab_id"]

    try:

        search = request.args.get("search", "").strip()

        if search:

            cursor.execute("""
            SELECT *
            FROM tests
            WHERE lab_id=%s
            AND
            (
                LOWER(test_name) LIKE LOWER(%s)
                OR LOWER(category) LIKE LOWER(%s)
                OR LOWER(sample_type) LIKE LOWER(%s)
                OR LOWER(status) LIKE LOWER(%s)
            )
            ORDER BY test_name
            """,
            (
                lab_id,
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            ))

        else:

            cursor.execute("""
            SELECT *
            FROM tests
            WHERE lab_id=%s
            ORDER BY test_name
            """, (lab_id,))

        tests = cursor.fetchall()

        return render_template(
            "test_management.html",
            tests=tests,
            search=search
        )

    finally:
        cursor.close()
        db.close()

@app.route("/add-test", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin")
def add_test():

    db = get_db()
    cursor = db.cursor(buffered=True)
    lab_id = session["lab_id"]

    try:

        if request.method == "POST":

            test_name = request.form["test_name"]
            category = request.form["category"]
            price = request.form["price"]
            sample_type = request.form["sample_type"]
            report_time = request.form["report_time"]
            description = request.form["description"]
            status = request.form["status"]

            cursor.execute("""
            INSERT INTO tests
            (
                lab_id,
                test_name,
                price,
                description,
                category,
                sample_type,
                report_time,
                status
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                lab_id,
                test_name,
                price,
                description,
                category,
                sample_type,
                report_time,
                status
            ))

            db.commit()

            return redirect(url_for("test_management"))

        return render_template("add_test.html")

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()
@app.route("/edit-test/<int:test_id>", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin")
def edit_test(test_id):

    db = get_db()
    cursor = db.cursor(buffered=True)
    lab_id = session["lab_id"]

    try:

        if request.method == "POST":

            test_name = request.form["test_name"]
            category = request.form["category"]
            price = request.form["price"]
            sample_type = request.form["sample_type"]
            report_time = request.form["report_time"]
            description = request.form["description"]
            status = request.form["status"]

            cursor.execute("""
            UPDATE tests
            SET
                test_name=%s,
                category=%s,
                price=%s,
                sample_type=%s,
                report_time=%s,
                description=%s,
                status=%s
            WHERE id=%s
            AND lab_id=%s
            """,
            (
                test_name,
                category,
                price,
                sample_type,
                report_time,
                description,
                status,
                test_id,
                lab_id
            ))

            db.commit()

            return redirect(url_for("test_management"))

        cursor.execute("""
        SELECT *
        FROM tests
        WHERE id=%s
        AND lab_id=%s
        """, (
            test_id,
            lab_id
        ))

        test = cursor.fetchone()

        return render_template(
            "edit_test.html",
            test=test
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()

@app.route("/delete-test/<int:test_id>")
@login_required
@role_required("Developer", "Admin")
def delete_test(test_id):

    db = get_db()
    cursor = db.cursor(buffered=True)
    lab_id = session["lab_id"]

    try:

        # Delete parameters of this test first
        cursor.execute("""
        DELETE FROM test_parameters
        WHERE test_name = (
            SELECT test_name
            FROM tests
            WHERE id=%s
            AND lab_id=%s
        )
        AND lab_id=%s
        """, (
            test_id,
            lab_id,
            lab_id
        ))

        # Delete the test
        cursor.execute("""
        DELETE FROM tests
        WHERE id=%s
        AND lab_id=%s
        """, (
            test_id,
            lab_id
        ))

        db.commit()

        return redirect(url_for("test_management"))

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()
@app.route("/test/<int:test_id>/parameters", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin")
def manage_parameters(test_id):

    db = get_db()
    cursor = db.cursor(buffered=True)
    lab_id = session["lab_id"]

    try:

        # ---------------- ADD PARAMETER ----------------

        if request.method == "POST":

            parameter_name = request.form["parameter_name"]
            unit = request.form["unit"]
            reference_range = request.form["reference_range"]
            section = request.form["section"]
            display_order = request.form["display_order"]

            # Get Test Name
            cursor.execute("""
            SELECT test_name
            FROM tests
            WHERE id=%s
            AND lab_id=%s
            """, (
                test_id,
                lab_id
            ))

            row = cursor.fetchone()

            if row is None:
                return "Test not found"

            test_name = row[0]

            cursor.execute("""
            INSERT INTO test_parameters
            (
                lab_id,
                test_name,
                test_id,
                section,
                parameter_name,
                unit,
                reference_range,
                display_order
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                lab_id,
                test_name,
                test_id,
                section,
                parameter_name,
                unit,
                reference_range,
                display_order
            ))

            db.commit()

            return redirect(url_for(
                "manage_parameters",
                test_id=test_id
            ))

        # ---------------- LOAD TEST ----------------

        cursor.execute("""
        SELECT *
        FROM tests
        WHERE id=%s
        AND lab_id=%s
        """, (
            test_id,
            lab_id
        ))

        test = cursor.fetchone()

        # ---------------- LOAD PARAMETERS ----------------

        cursor.execute("""
        SELECT *
        FROM test_parameters
        WHERE test_id=%s
        AND lab_id=%s
        ORDER BY
            section,
            display_order
        """, (
            test_id,
            lab_id
        ))

        parameters = cursor.fetchall()

        return render_template(
            "manage_parameters.html",
            test=test,
            parameters=parameters
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()

@app.route("/edit-parameter/<int:parameter_id>/<int:test_id>", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin")
def edit_parameter(parameter_id, test_id):

    db = get_db()
    cursor = db.cursor(buffered=True)
    lab_id = session["lab_id"]

    try:

        # ---------------- UPDATE ----------------

        if request.method == "POST":

            parameter_name = request.form["parameter_name"]
            unit = request.form["unit"]
            reference_range = request.form["reference_range"]

            cursor.execute("""
            UPDATE test_parameters
            SET
                parameter_name=%s,
                unit=%s,
                reference_range=%s
            WHERE id=%s
            AND lab_id=%s
            """,
            (
                parameter_name,
                unit,
                reference_range,
                parameter_id,
                lab_id
            ))

            db.commit()

            return redirect(
                url_for(
                    "manage_parameters",
                    test_id=test_id
                )
            )

        # ---------------- LOAD PARAMETER ----------------

        cursor.execute("""
        SELECT *
        FROM test_parameters
        WHERE id=%s
        AND lab_id=%s
        """, (
            parameter_id,
            lab_id
        ))

        parameter = cursor.fetchone()

        if parameter is None:
            return "Parameter not found"

        return render_template(
            "edit_parameter.html",
            parameter=parameter,
            test_id=test_id
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()
@app.route("/delete-parameter/<int:parameter_id>/<int:test_id>")
@login_required
@role_required("Developer", "Admin")
def delete_parameter(parameter_id, test_id):

    db = get_db()
    cursor = db.cursor(buffered=True)
    lab_id = session["lab_id"]

    try:

        cursor.execute("""
            DELETE FROM test_parameters
            WHERE id=%s
            AND lab_id=%s
        """, (
            parameter_id,
            lab_id
        ))

        db.commit()

        return redirect(
            url_for(
                "manage_parameters",
                test_id=test_id
            )
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()
@app.route("/expenses", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin")
def expenses():

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    lab_id = session["lab_id"]

    try:

        doctor = request.args.get("doctor", "")
        month = request.args.get("month", "")
        year = request.args.get("year", "")

        # ---------------- Load Available Years ----------------

        cursor.execute("""
            SELECT DISTINCT YEAR(payment_date) AS year
            FROM payments
            WHERE lab_id=%s
            ORDER BY year DESC
        """, (lab_id,))

        years = cursor.fetchall()

        # ---------------- Add Doctor ----------------

        if request.method == "POST":

            doctor_name = request.form["doctor_name"]
            commission = request.form["commission_percent"]

            cursor.execute("""
            INSERT INTO doctors
            (
                lab_id,
                doctor_name,
                commission_percent
            )
            VALUES(%s,%s,%s)
            """,
            (
                lab_id,
                doctor_name,
                commission
            ))

            db.commit()

            return redirect(url_for("expenses"))

        # ---------------- Doctor List ----------------

        cursor.execute("""
        SELECT
            id,
            doctor_name,
            commission_percent,
            status
        FROM doctors
        WHERE lab_id=%s
        ORDER BY doctor_name
        """, (lab_id,))

        doctors = cursor.fetchall()

        # ---------------- Doctor Commission Summary ----------------

        cursor.execute("""
        SELECT

            d.id,
            d.doctor_name,
            d.commission_percent,

            COUNT(DISTINCT p.patient_id) AS total_patients,

            COALESCE(SUM(pay.total_amount),0) AS total_business,

            COALESCE(
                SUM(pay.total_amount) * d.commission_percent / 100,
                0
            ) AS total_commission,

            d.status

        FROM doctors d

        LEFT JOIN patients p
            ON d.id = p.doctor_id
            AND d.lab_id = p.lab_id

        LEFT JOIN payments pay
            ON p.patient_id = pay.patient_id
            AND p.lab_id = pay.lab_id

        WHERE d.lab_id=%s

        GROUP BY
            d.id,
            d.doctor_name,
            d.commission_percent,
            d.status

        ORDER BY d.doctor_name
        """, (lab_id,))

        summary = cursor.fetchall()

        return render_template(
            "expenses.html",
            doctors=doctors,
            doctor_summary=summary,
            years=years
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()

@app.route("/doctor-patients/<int:doctor_id>")
@login_required
@role_required("Developer", "Admin")
def doctor_patients(doctor_id):

    db = get_db()
    cursor = db.cursor(buffered=True)
    lab_id = session["lab_id"]

    try:

        # ---------------- Doctor Information ----------------

        cursor.execute("""
        SELECT
            doctor_name,
            commission_percent
        FROM doctors
        WHERE id=%s
        AND lab_id=%s
        """, (
            doctor_id,
            lab_id
        ))

        doctor = cursor.fetchone()

        if not doctor:
            return "Doctor not found"

        doctor_name = doctor[0]
        commission_percent = float(doctor[1])

        # ---------------- Patients ----------------

        cursor.execute("""
        SELECT
            p.patient_id,
            p.name,
            p.mobile,
            p.created_at,
            pay.total_amount,
            pay.paid_amount,
            pay.remaining_amount,
            pay.payment_status

        FROM patients p

        JOIN payments pay
            ON p.patient_id = pay.patient_id
            AND p.lab_id = pay.lab_id

        WHERE p.doctor_id=%s
        AND p.lab_id=%s

        ORDER BY p.created_at DESC
        """, (
            doctor_id,
            lab_id
        ))

        patients = cursor.fetchall()

        total_patients = len(patients)

        total_business = sum(float(row[4]) for row in patients)

        total_commission = (
            total_business * commission_percent
        ) / 100

        return render_template(
            "doctor_patients.html",
            doctor_name=doctor_name,
            commission_percent=commission_percent,
            patients=patients,
            total_patients=total_patients,
            total_business=total_business,
            total_commission=total_commission
        )

    finally:
        cursor.close()
        db.close()
@app.route("/toggle-doctor-status/<int:doctor_id>")
@login_required
@role_required("Developer", "Admin", "Technician")
def toggle_doctor_status(doctor_id):

    db = get_db()
    cursor = db.cursor(buffered=True)
    lab_id = session["lab_id"]

    try:

        cursor.execute("""
            SELECT status
            FROM doctors
            WHERE id=%s
            AND lab_id=%s
        """, (
            doctor_id,
            lab_id
        ))

        doctor = cursor.fetchone()

        if not doctor:
            return "Doctor not found"

        status = doctor[0]

        new_status = "Inactive" if status == "Active" else "Active"

        cursor.execute("""
            UPDATE doctors
            SET status=%s
            WHERE id=%s
            AND lab_id=%s
        """, (
            new_status,
            doctor_id,
            lab_id
        ))

        db.commit()

        return redirect(url_for("expenses"))

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()

@app.route("/edit-doctor/<int:doctor_id>", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin", "Technician")
def edit_doctor(doctor_id):

    db = get_db()
    cursor = db.cursor(buffered=True)
    lab_id = session["lab_id"]

    try:

        if request.method == "POST":

            cursor.execute("""
                UPDATE doctors
                SET
                    doctor_name=%s,
                    commission_percent=%s
                WHERE id=%s
                AND lab_id=%s
            """,
            (
                request.form["doctor_name"],
                request.form["commission_percent"],
                doctor_id,
                lab_id
            ))

            db.commit()

            return redirect(url_for("expenses"))

        cursor.execute("""
            SELECT *
            FROM doctors
            WHERE id=%s
            AND lab_id=%s
        """,
        (
            doctor_id,
            lab_id
        ))

        doctor = cursor.fetchone()

        if doctor is None:
            return "Doctor not found"

        return render_template(
            "edit_doctor.html",
            doctor=doctor
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()
@app.route("/payment-entries")
@login_required
@role_required("Developer", "Admin", "Technician")
def payment_entries():

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    lab_id = session["lab_id"]

    try:

        search = request.args.get("search", "").strip().lower()

        if search:

            cursor.execute("""
            SELECT
                p.id,
                p.receipt_no,
                p.patient_id,
                pa.name,
                pa.mobile,
                p.total_amount,
                p.paid_amount,
                p.remaining_amount,
                p.payment_mode,
                p.payment_status,
                p.payment_date

            FROM payments p

            JOIN patients pa
                ON p.patient_id = pa.patient_id
                AND p.lab_id = pa.lab_id

            WHERE p.lab_id=%s
            AND
            (
                LOWER(p.receipt_no) LIKE %s
                OR LOWER(p.patient_id) LIKE %s
                OR LOWER(pa.name) LIKE %s
                OR LOWER(pa.mobile) LIKE %s
                OR LOWER(p.payment_status) LIKE %s
            )

            ORDER BY p.payment_date DESC
            """,
            (
                lab_id,
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            ))

        else:

            cursor.execute("""
            SELECT
                p.id,
                p.receipt_no,
                p.patient_id,
                pa.name,
                pa.mobile,
                p.total_amount,
                p.paid_amount,
                p.remaining_amount,
                p.payment_mode,
                p.payment_status,
                p.payment_date

            FROM payments p

            JOIN patients pa
                ON p.patient_id = pa.patient_id
                AND p.lab_id = pa.lab_id

            WHERE p.lab_id=%s

            ORDER BY p.payment_date DESC
            """, (lab_id,))

        payments = cursor.fetchall()

        return render_template(
            "payment_entries.html",
            payments=payments
        )

    finally:
        cursor.close()
        db.close()

@app.route("/payment-details/<receipt_no>")
@login_required
@role_required("Developer", "Admin", "Technician")
def payment_details(receipt_no):

    db = get_db()
    cursor = db.cursor(buffered=True)
    lab_id = session["lab_id"]

    try:

        # -----------------------------
        # Bill Summary
        # -----------------------------
        cursor.execute("""
        SELECT
            p.receipt_no,
            p.patient_id,
            pa.name,
            pa.mobile,
            pa.doctor_name,
            p.total_amount,
            p.paid_amount,
            p.remaining_amount,
            p.payment_status,
            p.payment_date

        FROM payments p

        JOIN patients pa
            ON p.patient_id = pa.patient_id
            AND p.lab_id = pa.lab_id

        WHERE p.receipt_no=%s
        AND p.lab_id=%s
        """, (
            receipt_no,
            lab_id
        ))

        payment = cursor.fetchone()

        if not payment:
            return "Receipt not found"

        # -----------------------------
        # Payment History
        # -----------------------------
        cursor.execute("""
        SELECT
            payment_date,
            amount,
            payment_mode,
            remarks
        FROM payment_transactions
        WHERE receipt_no=%s
        AND lab_id=%s
        ORDER BY payment_date ASC
        """, (
            receipt_no,
            lab_id
        ))

        history = cursor.fetchall()

        # -----------------------------
        # Tests Included in Bill
        # -----------------------------
        cursor.execute("""
        SELECT
            t.test_name,
            t.price AS original_price,
            pt.amount AS patient_price

        FROM patient_tests pt

        JOIN tests t
            ON pt.test_id = t.id
            AND pt.lab_id = t.lab_id

        WHERE pt.patient_id=%s
        AND pt.lab_id=%s

        ORDER BY t.test_name
        """, (
            payment["patient_id"],
            lab_id
        ))

        tests = cursor.fetchall()

        return render_template(
            "payment_details.html",
            payment=payment,
            history=history,
            tests=tests
        )

    finally:
        cursor.close()
        db.close()

@app.route("/settings", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Developer")
def settings():

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    lab_id = session["lab_id"]

    try:

        if request.method == "POST":

            cursor.execute("""
            SELECT id
            FROM lab_settings
            WHERE lab_id=%s
            LIMIT 1
            """, (lab_id,))

            existing = cursor.fetchone()

            logo = request.files.get("logo")
            signature = request.files.get("signature")
            stamp = request.files.get("stamp")

            logo_name = None
            signature_name = None
            stamp_name = None

            if logo and logo.filename:
                logo_name = secure_filename(logo.filename)
                logo.save(
                    os.path.join(
                        app.config["UPLOAD_LOGO"],
                        logo_name
                    )
                )

            if signature and signature.filename:
                signature_name = secure_filename(signature.filename)
                signature.save(
                    os.path.join(
                        app.config["UPLOAD_SIGNATURE"],
                        signature_name
                    )
                )

            if stamp and stamp.filename:
                stamp_name = secure_filename(stamp.filename)
                stamp.save(
                    os.path.join(
                        app.config["UPLOAD_STAMP"],
                        stamp_name
                    )
                )

            data = (
                request.form["lab_name"],
                request.form["owner_name"],
                request.form["registration_no"],
                request.form["gst_no"],
                request.form["nabl_no"],
                request.form["address"],
                request.form["city"],
                request.form["state"],
                request.form["pincode"],
                request.form["mobile"],
                request.form["alt_mobile"],
                request.form["email"],
                request.form["website"],
                request.form["receipt_prefix"],
                request.form["patient_prefix"]
            )

            if existing:

                cursor.execute("""
                UPDATE lab_settings SET

                    lab_name=%s,
                    owner_name=%s,
                    registration_no=%s,
                    gst_no=%s,
                    nabl_no=%s,
                    address=%s,
                    city=%s,
                    state=%s,
                    pincode=%s,
                    mobile=%s,
                    alt_mobile=%s,
                    email=%s,
                    website=%s,
                    receipt_prefix=%s,
                    patient_prefix=%s,
                    logo=COALESCE(%s,logo),
                    signature=COALESCE(%s,signature),
                    stamp=COALESCE(%s,stamp)

                WHERE lab_id=%s
                """,
                data +
                (
                    logo_name,
                    signature_name,
                    stamp_name,
                    lab_id
                ))

            else:

                cursor.execute("""
                INSERT INTO lab_settings
                (
                    lab_id,
                    lab_name,
                    owner_name,
                    registration_no,
                    gst_no,
                    nabl_no,
                    address,
                    city,
                    state,
                    pincode,
                    mobile,
                    alt_mobile,
                    email,
                    website,
                    receipt_prefix,
                    patient_prefix,
                    logo,
                    signature,
                    stamp
                )
                VALUES
                (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    lab_id,
                ) +
                data +
                (
                    logo_name,
                    signature_name,
                    stamp_name
                ))

            db.commit()

            return redirect(url_for("settings"))

        cursor.execute("""
        SELECT *
        FROM lab_settings
        WHERE lab_id=%s
        LIMIT 1
        """, (lab_id,))

        settings = cursor.fetchone()

        return render_template(
            "settings.html",
            settings=settings
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()
@app.context_processor
def inject_lab_settings():

    if "lab_id" not in session:
        return dict(lab_settings=None)

    db = get_db()
    cursor = db.cursor(buffered=True)

    try:
        cursor.execute("""
            SELECT *
            FROM lab_settings
            WHERE lab_id=%s
            LIMIT 1
        """, (session["lab_id"],))

        settings = cursor.fetchone()

        return dict(lab_settings=settings)

    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    print("APP STARTED")
    app.run(debug=True, use_reloader=False)