import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pymysql
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler
from decimal import Decimal
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
from functools import wraps
from modules.test_builder import test_builder_bp
import uuid
import math
import cloudinary
import cloudinary.uploader
import cloudinary.api
from database import get_db
from modules.patient_loader import load_patient
from modules.reference_loader import apply_reference_status
from modules.report_merger import merge_results
import qrcode
import io

import base64
import os
from pathlib import Path
from modules.analyzer_management import analyzer_management_bp
from itsdangerous import URLSafeSerializer
from modules.report_loader import (
    build_report_structure,
)
from modules.result_loader import (
    load_saved_results,
    load_component_results
)
import base64
import logging


import qrcode
from io import BytesIO
from flask import send_file
from modules.result_loader import (
    load_saved_results,
    load_component_results
)
from modules.result_saver import (
    delete_old_results,
    save_signatories,
    save_manual_results,
    save_formula_results,
    save_dictionary_results
)
from modules.signatory_loader import load_signatories
from modules.formula_handler import (
    calculate_formula_results,
)
import os
import redis
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ["REDIS_PORT"]),
    username=os.getenv("REDIS_USERNAME", "default"),
    password=os.environ["REDIS_PASSWORD"],
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
)

r = redis.Redis.from_url('redis://default:AnonAOegzaHSdcohnXnYvC2svtyy6FdU@plot-flattering-pull-10400.db.redis.io:13756')
import json
def get_cached_dashboard_data(lab_id):
    cache_key = f"lab_{lab_id}_stats"
    
    # Check if cached data exists
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Replace this with your actual database query logic or thread/fetch execution
    data = {"lab_id": lab_id, "status": "fetched_from_db"} 
    
    # Store in Redis with a 60-second expiration
    r.setex(cache_key, 60, json.dumps(data))
    return data
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)


from flask_compress import Compress

app = Flask(__name__)
compress = Compress(app)  # Enables automatic gzip/brotli compression for routes
from datetime import timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import time
import bcrypt
import smtplib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("DIAGNOSTIC: app.py imports started")
from email.message import EmailMessage



load_dotenv()

logger.info("DIAGNOSTIC: Creating Flask application")

app = Flask(__name__)

logger.info("DIAGNOSTIC: Flask application created")
app.register_blueprint(analyzer_management_bp)

bcrypt = Bcrypt(app)

app.register_blueprint(test_builder_bp)

# Read SECRET_KEY from .env
# Read SECRET_KEY from .env
app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("SECRET_KEY is missing from .env")

app.config["SECRET_KEY"] = app.secret_key

# Session security. Set SESSION_COOKIE_SECURE=true in HTTPS production.
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv(
    "SESSION_COOKIE_SECURE",
    "true" if (os.getenv("VERCEL") or os.getenv("RENDER")) else "false"
).strip().lower() in {"1", "true", "yes", "on"}

# ============================================================
# CLOUDINARY CONFIGURATION
# ============================================================

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


# ============================================================
# PASSWORD RESET EMAIL CONFIGURATION
# ============================================================



def get_db():
    """
    Connect to database using PyMySQL.
    """
    start_time = time.perf_counter()

    try:
        connection = pymysql.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "15054")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            connect_timeout=10
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        app.logger.info("PERF | PyMySQL connection established | %.2f ms", elapsed_ms)
        return connection

    except Exception:
        app.logger.exception("PERF | PyMySQL connection failed")
        raise

  
def execute_timed(cursor, query_name, sql, params=None):
    """Execute an SQL query and log its execution time."""
    start_time = time.perf_counter()

    try:
        cursor.execute(sql, params or ())
    finally:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        app.logger.info(
            "PERF | SQL | %s | %.2f ms",
            query_name,
            elapsed_ms
        )



# Email configuration
app.config["MAIL_HOST"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_FROM"] = os.getenv("MAIL_FROM")
def get_reset_serializer():

    return URLSafeTimedSerializer(
        app.config["SECRET_KEY"],
        salt="smart-lab-password-reset"
    )


def generate_reset_token(user_id, lab_id):

    serializer = get_reset_serializer()

    return serializer.dumps({
        "user_id": user_id,
        "lab_id": lab_id
    })


def verify_reset_token(token):

    serializer = get_reset_serializer()

    try:

        data = serializer.loads(
            token,
            salt="smart-lab-password-reset",
            max_age=900
        )

        return data

    except (BadSignature, SignatureExpired):

        return None
def send_password_reset_email(recipient_email, username, reset_url):

    msg = EmailMessage()

    msg["Subject"] = "Smart Laboratory - Password Reset"
    msg["From"] = app.config["MAIL_FROM"]
    msg["To"] = recipient_email

    msg.set_content(
        f"""
Hello {username},

A password reset was requested for your
Smart Laboratory Management System account.

Reset your password using this link:

{reset_url}

This link is valid for 15 minutes.

If you did not request this password reset,
please ignore this message.

Regards,
Smart Laboratory Management System
"""
    )

    with smtplib.SMTP_SSL(
        app.config["MAIL_HOST"],
        app.config["MAIL_PORT"]
    ) as server:

        server.login(
            app.config["MAIL_USERNAME"],
            app.config["MAIL_PASSWORD"]
        )

        server.send_message(msg)

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

            # Avoid logging session identifiers and tenant/user details.
            app.logger.debug("Role authorization check for endpoint=%s", f.__name__)

            if "user_id" not in session:
                return redirect(url_for("login"))

            if session.get("role") not in roles:
                return "403 Forbidden", 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator

# ============================================================
# SECURE REPORT QR TOKEN
# ============================================================

# ============================================================
# SECURE REPORT QR TOKEN
# ============================================================

def create_report_qr_token(patient_id, lab_id):

    serializer = URLSafeSerializer(
        app.secret_key,
        salt="smart-lab-report"
    )

    return serializer.dumps({
        "patient_id": patient_id,
        "lab_id": lab_id
    })


def read_report_qr_token(token):

    try:

        serializer = URLSafeSerializer(
            app.secret_key,
            salt="smart-lab-report"
        )

        data = serializer.loads(token)

        return (
            data.get("patient_id"),
            data.get("lab_id")
        )

    except Exception:

        return None, None
    
def get_component_settings(cursor, component_id):
    """
    Return component settings as a dictionary.
    """

    cursor.execute("""
        SELECT
            setting_key,
            setting_value
        FROM report_component_settings
        WHERE component_id = %s
    """, (component_id,))

    rows = cursor.fetchall()

    settings = {}

    for row in rows:
        settings[row[0]] = row[1]

    return settings 




BASE_DIR = Path(__file__).resolve().parent

# Vercel has a read-only application filesystem.
# Use /tmp for temporary local uploads on Vercel.
if os.environ.get("VERCEL"):
    UPLOAD_BASE_DIR = Path("/tmp/smart_lab_uploads")
else:
    UPLOAD_BASE_DIR = BASE_DIR / "static" / "uploads"

UPLOAD_LOGO = str(UPLOAD_BASE_DIR / "logo")
UPLOAD_SIGNATURE = str(UPLOAD_BASE_DIR / "signature")
UPLOAD_STAMP = str(UPLOAD_BASE_DIR / "stamp")
UPLOAD_SIGNATORY = str(UPLOAD_BASE_DIR / "signatories")

# Register upload paths
app.config["UPLOAD_LOGO"] = UPLOAD_LOGO
app.config["UPLOAD_SIGNATURE"] = UPLOAD_SIGNATURE
app.config["UPLOAD_STAMP"] = UPLOAD_STAMP
app.config["UPLOAD_SIGNATORY"] = UPLOAD_SIGNATORY

# Create directories in a writable location
for upload_dir in (
    UPLOAD_LOGO,
    UPLOAD_SIGNATURE,
    UPLOAD_STAMP,
    UPLOAD_SIGNATORY,
):
    os.makedirs(upload_dir, exist_ok=True)




# ------------------------------------
# Landing Page
# ------------------------------------


@app.route("/setup-developer", methods=["GET", "POST"])
def setup_developer():
    """Disabled: provision the initial Developer account out-of-band.

    Do not create privileged accounts through a public, unauthenticated route.
    Use a one-time administrative script or a protected deployment procedure.
    """
    return "Not Found", 404

@app.route("/", methods=["GET", "POST"])
def login():

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:

        if request.method == "POST":

            lab_id = request.form["lab_id"].strip().upper()
            username = request.form["username"].strip().lower()
            password = request.form["password"]

            # ------------------------------------------------
            # Remember Me
            # ------------------------------------------------

            remember_me = (
                request.form.get("remember_me") == "1"
            )

            # ------------------------------------------------
            # STEP 1 : Verify User
            # ------------------------------------------------

            cursor.execute("""
                SELECT *
                FROM users
                WHERE lab_id = %s
                  AND username = %s
                  AND status = 'Active'
            """, (
                lab_id,
                username
            ))

            user = cursor.fetchone()

            if not user:

                flash(
                    "Invalid Lab ID, Username or Password",
                    "danger"
                )

                return redirect(url_for("login"))

            # ------------------------------------------------
            # STEP 2 : Verify Password
            # ------------------------------------------------

            if not bcrypt.check_password_hash(
                user["password"],
                password
            ):

                flash(
                    "Invalid Lab ID, Username or Password",
                    "danger"
                )

                return redirect(url_for("login"))

            # ------------------------------------------------
            # STEP 3 : Create Session
            # ------------------------------------------------

            session.clear()

            # Remember Me
            session.permanent = remember_me

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["lab_id"] = user["lab_id"]

            # ------------------------------------------------
            # STEP 4 : Developer
            # ------------------------------------------------

            if user["role"] == "Developer":

                session["lab_name"] = "System Administrator"
                session["owner_name"] = "Master Account"
                session["lab_settings"] = None  # Developers don't require lab settings

            # ------------------------------------------------
            # STEP 5 : Normal Laboratory User
            # ------------------------------------------------

            else:

                cursor.execute("""
                    SELECT *
                    FROM laboratories
                    WHERE lab_id = %s
                      AND status = 'Active'
                """, (
                    lab_id,
                ))

                lab = cursor.fetchone()

                if not lab:

                    session.clear()

                    flash(
                        "Laboratory not found.",
                        "danger"
                    )

                    return redirect(url_for("login"))

                session["lab_id"] = lab["lab_id"]
                session["lab_name"] = lab["lab_name"]
                session["owner_name"] = lab["owner_name"]

                # OPTIMIZATION: Fetch lab settings once upon login and save to session
                cursor.execute("""
                    SELECT *
                    FROM lab_settings
                    WHERE lab_id = %s
                    LIMIT 1
                """, (lab_id,))
                session["lab_settings"] = cursor.fetchone()

            # ------------------------------------------------
            # DEBUG
            # ------------------------------------------------

            app.logger.info("Successful login; role=%s", session.get("role"))

            return redirect(
                url_for("dashboard")
            )

        return render_template("login.html")

    except Exception:

        db.rollback()
        raise

    finally:

        cursor.close()
        db.close()
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        lab_id = request.form["lab_id"].strip().upper()
        username = request.form["username"].strip().lower()

        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)

        try:

            # ====================================================
            # FIND USER + REGISTERED CONTACT DETAILS
            # ====================================================

            cursor.execute("""
                SELECT
                    id AS user_id,
                    lab_id,
                    username,
                    status,
                    email,
                    mobile
                FROM users
                WHERE lab_id = %s
                  AND username = %s
                  AND status = 'Active'
            """, (
                lab_id,
                username
            ))

            user = cursor.fetchone()

            # ====================================================
            # DO NOT REVEAL WHETHER ACCOUNT EXISTS
            # ====================================================

            if user:

                email = user.get("email")
                mobile = user.get("mobile")

                # ------------------------------------------------
                # Generate secure reset token
                # ------------------------------------------------

                token = generate_reset_token(
                    user["user_id"],
                    user["lab_id"]
                )

                reset_url = url_for(
                    "reset_password",
                    token=token,
                    _external=True
                )

                # =================================================
                # SEND RESET LINK TO REGISTERED EMAIL
                # =================================================

                if email:

                    try:

                        send_password_reset_email(
                            email,
                            user["username"],
                            reset_url
                        )

                        print(
                            "Password reset email sent successfully."
                        )

                    except Exception as e:

                        print(
                            "Email sending failed:",
                            e
                        )

                # =================================================
                # SMS
                # =================================================

                # SMS provider is not configured yet.
                # Registered mobile is available in the users table.
                # Do not send SMS until an SMS provider is configured.

                if mobile:
                    print("Registered mobile is available.")

            # ====================================================
            # SAME MESSAGE FOR SECURITY
            # ====================================================

            flash(
                "If the account exists, a password reset link "
                "has been sent to the registered email.",
                "info"
            )

            return redirect(
                url_for("forgot_password")
            )

        except Exception:

            db.rollback()
            raise

        finally:

            cursor.close()
            db.close()

    return render_template(
        "forgot_password.html"
    )
@app.route(
    "/reset-password/<token>",
    methods=["GET", "POST"]
)
def reset_password(token):

    data = verify_reset_token(token)

    if not data:

        return render_template(
            "reset_password.html",
            invalid_token=True
        )

    user_id = data["user_id"]
    lab_id = data["lab_id"]

    if request.method == "POST":

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # ------------------------------------------------
        # Password validation
        # ------------------------------------------------

        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )

            return render_template(
                "reset_password.html",
                invalid_token=False
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return render_template(
                "reset_password.html",
                invalid_token=False
            )

        # ------------------------------------------------
        # Hash new password
        # ------------------------------------------------

        hashed_password = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

        db = get_db()
        cursor = db.cursor()

        try:

            cursor.execute("""
                UPDATE users
                SET password = %s
                WHERE id = %s
                  AND lab_id = %s
                  AND status = 'Active'
            """, (
                hashed_password,
                user_id,
                lab_id
            ))

            db.commit()

            flash(
                "Password reset successfully. "
                "You can now login with your new password.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except Exception:

            db.rollback()
            raise

        finally:

            cursor.close()
            db.close()

    return render_template(
        "reset_password.html",
        invalid_token=False
    )

@app.route("/logout")
@login_required
def logout():

    session.clear()

    return redirect(url_for("login"))
@app.route("/register-lab", methods=["GET", "POST"])
def register_lab():

    if request.method == "POST":

        db = get_db()
        cursor = db.cursor()

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
    WHERE email = %s
    AND lab_name = %s
""", (email, lab_name))

            if cursor.fetchone():
             flash("This laboratory is already registered with this email.", "danger")
             return redirect(url_for("register_lab"))

            # -----------------------------
            # Mobile Exists?
            # -----------------------------

            cursor.execute("""
    SELECT id
    FROM laboratories
    WHERE mobile = %s
    AND lab_name = %s
""", (mobile, lab_name))

            if cursor.fetchone():
             flash("This laboratory is already registered with this mobile number.", "danger")
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
            
            cursor.execute("""
    INSERT INTO users
    (
        lab_id,
        username,
        password,
        email,
        mobile,
        role,
        status
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s)
""", (
    lab_id,
    username.lower(),
    hashed_password,
    email,
    mobile,
    "Admin",
    "Active"
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


from concurrent.futures import ThreadPoolExecutor

@app.route("/dashboard")
@login_required
@role_required("Developer", "Admin", "Technician")
def dashboard():
    """Render the dashboard using Redis cache for stats and ThreadPoolExecutor for fresh data."""
    route_start = time.perf_counter()

    if session.get("role") == "Developer":
        return redirect(url_for("super_admin_dashboard"))

    try:
        lab_id = session["lab_id"]
        search = request.args.get("search", "").strip()

        # 1. Try to fetch summary stats from Redis cache (skips heavy queries if cached)
        cache_key = f"lab_{lab_id}_dashboard_stats"
        cached_stats = r.get(cache_key)
        
        if cached_stats and not search:
            # If cached and no active search filter is applied, load data from cache
            stats_data = json.loads(cached_stats)
            patients = stats_data["patients"]
            payments = stats_data["payments"]
            total_patients = stats_data["total_patients"]
            patient_count = stats_data["patient_count"]
            total_income = stats_data["total_income"]
            cash_total = stats_data["cash_total"]
            upi_total = stats_data["upi_total"]
            cash_count = stats_data["cash_count"]
            upi_count = stats_data["upi_count"]
            grand_total_income = stats_data["grand_total_income"]
            pending_amount = stats_data["pending_amount"]
            total_tests = stats_data["total_tests"]
            total_reports = stats_data["total_reports"]
        else:
            # 2. Fallback to parallel execution if cache misses or a search query is active
            def fetch_patients():
                conn = get_db()
                cur = conn.cursor()
                try:
                    if not search:
                        cur.execute("""
                            SELECT
                                p.patient_id, p.name, p.age,
                                GROUP_CONCAT(DISTINCT t.test_name ORDER BY t.test_name SEPARATOR ', ') AS tests,
                                pay.total_amount, pay.payment_mode, pay.payment_status
                            FROM patients p
                            JOIN patient_tests pt ON pt.patient_id = p.patient_id AND pt.lab_id = p.lab_id
                            JOIN tests t ON t.id = pt.test_id AND (t.lab_id IS NULL OR t.lab_id = pt.lab_id)
                            JOIN payments pay ON pay.patient_id = p.patient_id AND pay.lab_id = p.lab_id
                            WHERE p.lab_id = %s
                              AND p.created_at >= CURDATE()
                              AND p.created_at < CURDATE() + INTERVAL 1 DAY
                            GROUP BY p.id, p.patient_id, p.name, p.age, pay.total_amount, pay.payment_mode, pay.payment_status, p.created_at
                            ORDER BY p.created_at DESC
                            LIMIT 10
                        """, (lab_id,))
                    else:
                        cur.execute("""
                            SELECT
                                p.patient_id, p.name, p.age,
                                GROUP_CONCAT(DISTINCT t.test_name ORDER BY t.test_name SEPARATOR ', ') AS tests,
                                pay.total_amount, pay.payment_mode, pay.payment_status
                            FROM patients p
                            JOIN patient_tests pt ON pt.patient_id = p.patient_id AND pt.lab_id = p.lab_id
                            JOIN tests t ON t.id = pt.test_id AND (t.lab_id IS NULL OR t.lab_id = pt.lab_id)
                            JOIN payments pay ON pay.patient_id = p.patient_id AND pay.lab_id = p.lab_id
                            WHERE p.lab_id = %s
                              AND (
                                  p.patient_id LIKE %s
                                  OR p.name LIKE %s
                                  OR p.mobile LIKE %s
                              )
                            GROUP BY p.id, p.patient_id, p.name, p.age, pay.total_amount, pay.payment_mode, pay.payment_status, p.created_at
                            ORDER BY p.created_at DESC
                        """, (lab_id, f"%{search}%", f"%{search}%", f"%{search}%"))
                    return cur.fetchall()
                finally:
                    cur.close()
                    conn.close()

            def fetch_payments():
                conn = get_db()
                cur = conn.cursor(pymysql.cursors.DictCursor)
                try:
                    cur.execute("""
                        SELECT p.receipt_no, pa.name, p.total_amount, p.payment_mode, p.payment_status
                        FROM payments p
                        JOIN patients pa ON pa.patient_id = p.patient_id AND pa.lab_id = p.lab_id
                        WHERE p.lab_id = %s
                        ORDER BY p.id DESC
                        LIMIT 10
                    """, (lab_id,))
                    return cur.fetchall()
                finally:
                    cur.close()
                    conn.close()

            def fetch_patient_stats():
                conn = get_db()
                cur = conn.cursor(pymysql.cursors.DictCursor)
                try:
                    cur.execute("""
                        SELECT
                            COUNT(*) AS total_patients,
                            COALESCE(
                                SUM(
                                    CASE
                                        WHEN created_at >= CURDATE()
                                         AND created_at < CURDATE() + INTERVAL 1 DAY
                                        THEN 1 ELSE 0
                                    END
                                ), 0
                            ) AS patient_count
                        FROM patients
                        WHERE lab_id = %s
                    """, (lab_id,))
                    return cur.fetchone()
                finally:
                    cur.close()
                    conn.close()

            def fetch_transaction_stats():
                conn = get_db()
                cur = conn.cursor(pymysql.cursors.DictCursor)
                try:
                    cur.execute("""
                        SELECT
                            COALESCE(
                                SUM(
                                    CASE
                                        WHEN payment_date >= CURDATE()
                                         AND payment_date < CURDATE() + INTERVAL 1 DAY
                                        THEN amount ELSE 0
                                    END
                                ), 0
                            ) AS total_income,
                            COALESCE(
                                SUM(
                                    CASE
                                        WHEN payment_mode = 'Cash'
                                         AND payment_date >= DATE_FORMAT(CURDATE(), '%%Y-%%m-01')
                                         AND payment_date < DATE_FORMAT(CURDATE() + INTERVAL 1 MONTH, '%%Y-%%m-01')
                                        THEN amount ELSE 0
                                    END
                                ), 0
                            ) AS cash_total,
                            COALESCE(
                                SUM(
                                    CASE
                                        WHEN payment_mode = 'UPI'
                                         AND payment_date >= DATE_FORMAT(CURDATE(), '%%Y-%%m-01')
                                         AND payment_date < DATE_FORMAT(CURDATE() + INTERVAL 1 MONTH, '%%Y-%%m-01')
                                        THEN amount ELSE 0
                                    END
                                ), 0
                            ) AS upi_total,
                            COALESCE(
                                SUM(
                                    CASE
                                        WHEN payment_mode = 'Cash'
                                         AND payment_date >= DATE_FORMAT(CURDATE(), '%%Y-%%m-01')
                                         AND payment_date < DATE_FORMAT(CURDATE() + INTERVAL 1 MONTH, '%%Y-%%m-01')
                                        THEN 1 ELSE 0
                                    END
                                ), 0
                            ) AS cash_count,
                            COALESCE(
                                SUM(
                                    CASE
                                        WHEN payment_mode = 'UPI'
                                         AND payment_date >= DATE_FORMAT(CURDATE(), '%%Y-%%m-01')
                                         AND payment_date < DATE_FORMAT(CURDATE() + INTERVAL 1 MONTH, '%%Y-%%m-01')
                                        THEN 1 ELSE 0
                                    END
                                ), 0
                            ) AS upi_count,
                            COALESCE(SUM(amount), 0) AS grand_total_income
                        FROM payment_transactions
                        WHERE lab_id = %s
                    """, (lab_id,))
                    return cur.fetchone()
                finally:
                    cur.close()
                    conn.close()

            def fetch_pending_payments():
                conn = get_db()
                cur = conn.cursor()  # Standard tuple cursor
                try:
                    cur.execute("""
                        SELECT COALESCE(SUM(remaining_amount), 0)
                        FROM payments
                        WHERE payment_status = 'Pending' AND lab_id = %s
                    """, (lab_id,))
                    res = cur.fetchone()
                    return res[0] if res else 0
                finally:
                    cur.close()
                    conn.close()

            def fetch_test_report_stats():
                conn = get_db()
                cur = conn.cursor()  # Use standard tuple cursor
                try:
                    cur.execute("""
                        SELECT
                            (SELECT COUNT(*) FROM patient_tests WHERE lab_id = %s) AS total_tests,
                            (SELECT COUNT(DISTINCT patient_id) FROM test_results WHERE lab_id = %s) AS total_reports
                    """, (lab_id, lab_id))
                    return cur.fetchone()
                finally:
                    cur.close()
                    conn.close()

            with ThreadPoolExecutor(max_workers=6) as executor:
                future_patients = executor.submit(fetch_patients)
                future_payments = executor.submit(fetch_payments)
                future_p_stats = executor.submit(fetch_patient_stats)
                future_t_stats = executor.submit(fetch_transaction_stats)
                future_pending = executor.submit(fetch_pending_payments)
                future_test_stats = executor.submit(fetch_test_report_stats)

                patients = future_patients.result()
                payments = future_payments.result()
                
                patient_stats = future_p_stats.result()
                total_patients = patient_stats["total_patients"]
                patient_count = patient_stats["patient_count"]
                transaction_stats = future_t_stats.result()
                total_income = transaction_stats["total_income"]
                cash_total = transaction_stats["cash_total"]
                upi_total = transaction_stats["upi_total"]
                cash_count = transaction_stats["cash_count"]
                upi_count = transaction_stats["upi_count"]
                grand_total_income = transaction_stats["grand_total_income"]

                pending_amount = future_pending.result()

                test_stats = future_test_stats.result()
                total_tests = test_stats[0]
                total_reports = test_stats[1]

            # Save to Redis cache for 60 seconds if no search query was passed
            if not search:
                payload = {
                    "patients": patients,
                    "payments": payments,
                    "total_patients": total_patients,
                    "patient_count": patient_count,
                    "total_income": total_income,
                    "cash_total": cash_total,
                    "upi_total": upi_total,
                    "cash_count": cash_count,
                    "upi_count": upi_count,
                    "grand_total_income": grand_total_income,
                    "pending_amount": pending_amount,
                    "total_tests": total_tests,
                    "total_reports": total_reports
                }
                r.setex(cache_key, 60, json.dumps(payload, default=str))

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

    finally:
        app.logger.info(
            "PERF | Dashboard total route processing | %.2f ms",
            (time.perf_counter() - route_start) * 1000
        )
@app.route("/api/dashboard-stats")
@login_required
@role_required("Developer", "Admin", "Technician")
def dashboard_stats_api():
    """Lightweight API endpoint to serve dashboard stats asynchronously."""
    lab_id = session["lab_id"]
    cache_key = f"lab_{lab_id}_dashboard_stats"
    
    # Check cache first
    cached_stats = r.get(cache_key)
    if cached_stats:
        return jsonify(json.loads(cached_stats))
    
    # If not cached, fetch quickly or return default structure
    # (We can use a single pooled connection for quick fetching)
    conn = get_db()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("SELECT COUNT(*) AS total_patients FROM patients WHERE lab_id = %s", (lab_id,))
        p_res = cursor.fetchone()
        
        payload = {
            "total_patients": p_res["total_patients"] if p_res else 0,
            "patient_count": 0,
            "total_income": 0,
            "pending_amount": 0,
            "total_tests": 0,
            "total_reports": 0
        }
        
        # Cache for 60 seconds
        r.set(cache_key, json.dumps(payload, default=str), ex=60)
        return jsonify(payload)
    finally:
        cursor.close()
        conn.close()
# Add this import with the other imports at the top of your Flask application:
# import uuid

@app.route(
    "/patient-registration",
    methods=["GET", "POST"]
)
@login_required
@role_required(
    "Developer",
    "Admin",
    "Technician"
)
def patient_registration():
    lab_id = session["lab_id"]

    # ==================================================
    # GET NUMERIC LAB ID FOR lab_test_overrides (Initial Check)
    # ==================================================
    db_init = get_db()
    cursor_init = db_init.cursor()
    try:
        cursor_init.execute("""
            SELECT id
            FROM laboratories
            WHERE lab_id = %s
            LIMIT 1
        """, (lab_id,))
        lab_row = cursor_init.fetchone()
        if not lab_row:
            raise ValueError(f"Laboratory not found: {lab_id}")
        numeric_lab_id = lab_row[0]
    finally:
        cursor_init.close()
        db_init.close()

    # ==================================================
    # POST REQUEST (Patient Registration Handling)
    # ==================================================
    if request.method == "POST":
        db = get_db()
        cursor = db.cursor()

        try:
            # -----------------------------------------------
            # Patient Details
            # -----------------------------------------------
            name = request.form["name"].strip()

            age_raw = request.form.get("age", "").strip()
            age = int(age_raw) if age_raw else None

            gender = request.form["gender"]
            mobile = request.form["mobile"].strip()
            address = request.form.get("address", "").strip()
            doctor_id = request.form.get("doctor_id") or None

            # -----------------------------------------------
            # Get Doctor
            # -----------------------------------------------
            doctor_name = "Self"

            if doctor_id:
                cursor.execute("""
                    SELECT doctor_name
                    FROM doctors
                    WHERE id = %s
                      AND lab_id = %s
                """, (doctor_id, lab_id))

                doctor = cursor.fetchone()

                if doctor:
                    doctor_name = doctor[0]
                else:
                    doctor_id = None

            # -----------------------------------------------
            # Payment Details
            # -----------------------------------------------
            payment_mode = request.form["payment_mode"]

            try:
                paid_amount = Decimal(
                    request.form.get("paid_amount") or "0"
                )
                if not paid_amount.is_finite():
                    paid_amount = Decimal("0")
            except Exception:
                paid_amount = Decimal("0")

            if paid_amount < 0:
                paid_amount = Decimal("0")

            selected_test_ids = request.form.getlist("tests")

            if not selected_test_ids:
                flash("Please select at least one test.", "warning")
                return redirect(url_for("patient_registration"))

            # -----------------------------------------------
            # Patient ID Prefix
            # -----------------------------------------------
            cursor.execute("""
                SELECT patient_prefix
                FROM lab_settings
                WHERE lab_id = %s
                LIMIT 1
            """, (lab_id,))

            prefix_row = cursor.fetchone()

            patient_prefix = (
                prefix_row[0]
                if prefix_row and prefix_row[0]
                else "PAT"
            )

            # -----------------------------------------------
            # Generate Patient ID
            # -----------------------------------------------
            cursor.execute("""
                SELECT patient_id
                FROM patients
                WHERE lab_id = %s
                ORDER BY id DESC
                LIMIT 1
            """, (lab_id,))

            last_patient = cursor.fetchone()

            try:
                last_no = (
                    int(last_patient[0].split("-")[-1])
                    if last_patient and last_patient[0]
                    else 0
                )
            except (ValueError, IndexError):
                last_no = 0

            next_no = last_no + 1
            year = datetime.now().year

            patient_id = (
                f"{patient_prefix}-{year}-{next_no:04d}"
            )

            collected_on = datetime.now()

            # -----------------------------------------------
            # Save Patient
            # -----------------------------------------------
            cursor.execute("""
                INSERT INTO patients (
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
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

            # -----------------------------------------------
            # Save Selected Tests With Patient-Specific Prices
            # -----------------------------------------------
            total_amount = Decimal("0.00")
            sample_ids_by_type = {}

            submitted_prices = request.form.getlist("patient_price")

            if len(selected_test_ids) != len(submitted_prices):
                raise ValueError(
                    "Selected tests and prices do not match. "
                    "Please refresh the page and try again."
                )

            for selected_id, submitted_price in zip(
                selected_test_ids,
                submitted_prices
            ):
                try:
                    test_id = int(selected_id)
                except (ValueError, TypeError):
                    raise ValueError("Invalid selected test ID.")

                try:
                    patient_price = Decimal(
                        str(submitted_price).strip()
                    )
                except Exception:
                    raise ValueError(
                        "Invalid patient price submitted."
                    )

                if (
                    not patient_price.is_finite()
                    or patient_price < 0
                    or patient_price > Decimal("99999999.99")
                ):
                    raise ValueError(
                        "Patient price must be a valid non-negative amount."
                    )

                patient_price = patient_price.quantize(
                    Decimal("0.01")
                )

                # Fetch Original Price and verify test availability
                cursor.execute("""
                    SELECT
                        t.id,
                        t.test_name,
                        t.price AS original_price,
                        t.sample_type
                    FROM tests t

                    LEFT JOIN lab_test_settings lts
                        ON lts.test_id = t.id
                       AND lts.lab_id = %s

                    WHERE t.id = %s
                      AND (
                            t.lab_id IS NULL
                            OR t.lab_id = %s
                      )
                      AND COALESCE(
                            lts.is_deleted,
                            FALSE
                      ) = FALSE
                      AND COALESCE(
                            lts.status,
                            t.status
                      ) = 'Active'

                    LIMIT 1
                """, (
                    lab_id,
                    test_id,
                    lab_id
                ))

                test = cursor.fetchone()

                if not test:
                    raise ValueError(
                        f"Selected test ID {test_id} is unavailable "
                        "for this laboratory."
                    )

                test_id = test[0]
                test_name = test[1]
                test_sample_type = (test[3] or "Unknown").strip()
                if not test_sample_type:
                    test_sample_type = "Unknown"

                if test_sample_type not in sample_ids_by_type:
                    sample_id = None

                    for _ in range(5):
                        candidate_sample_id = (
                            f"SMP-{year}-{uuid.uuid4().hex[:8].upper()}"
                        )
                        cursor.execute(
                            "SELECT 1 FROM samples WHERE sample_id = %s LIMIT 1",
                            (candidate_sample_id,)
                        )
                        if not cursor.fetchone():
                            sample_id = candidate_sample_id
                            break

                    if not sample_id:
                        raise RuntimeError(
                            "Could not generate a unique Sample ID. Please retry."
                        )

                    cursor.execute("""
                        INSERT INTO samples (
                            sample_id,
                            patient_id,
                            sample_type,
                            collected_on,
                            status,
                            lab_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        sample_id,
                        patient_id,
                        test_sample_type,
                        collected_on,
                        "Pending",
                        lab_id
                    ))

                    sample_ids_by_type[test_sample_type] = sample_id
                else:
                    sample_id = sample_ids_by_type[test_sample_type]

                total_amount += patient_price

                cursor.execute("""
                    INSERT INTO patient_tests (
                        lab_id,
                        patient_id,
                        test_id,
                        sample_id,
                        sample_type,
                        collected_on,
                        amount,
                        analyzer_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    lab_id,
                    patient_id,
                    test_id,
                    sample_id,
                    test_sample_type,
                    collected_on,
                    patient_price,
                    "Pending"
                ))

            total_amount = total_amount.quantize(
                Decimal("0.01")
            )
            remaining_amount = max(
                Decimal("0.00"),
                total_amount - paid_amount
            ).quantize(Decimal("0.01"))

            payment_status = (
                "Paid"
                if remaining_amount == Decimal("0.00")
                else "Pending"
            )

            # -----------------------------------------------
            # Save Payment
            # -----------------------------------------------
            cursor.execute("""
                INSERT INTO payments (
                    lab_id,
                    patient_id,
                    mobile,
                    total_amount,
                    paid_amount,
                    remaining_amount,
                    payment_mode,
                    payment_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
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

            # -----------------------------------------------
            # Generate Receipt Number
            # -----------------------------------------------
            cursor.execute("""
                SELECT receipt_prefix
                FROM lab_settings
                WHERE lab_id = %s
                LIMIT 1
            """, (lab_id,))

            receipt_row = cursor.fetchone()

            receipt_prefix = (
                receipt_row[0]
                if receipt_row and receipt_row[0]
                else "RCPT"
            )

            receipt_no = (
                f"{receipt_prefix}-{year}-{payment_id:04d}"
            )

            cursor.execute("""
                UPDATE payments
                SET receipt_no = %s
                WHERE id = %s
                  AND lab_id = %s
            """, (
                receipt_no,
                payment_id,
                lab_id
            ))

            # -----------------------------------------------
            # Save Payment Transaction
            # -----------------------------------------------
            if paid_amount > 0:
                cursor.execute("""
                    INSERT INTO payment_transactions (
                        lab_id,
                        patient_id,
                        receipt_no,
                        amount,
                        payment_mode,
                        remarks
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    lab_id,
                    patient_id,
                    receipt_no,
                    paid_amount,
                    payment_mode,
                    "Registration Payment"
                ))

            # -----------------------------------------------
            # Save Pending Payment
            # -----------------------------------------------
            if payment_status == "Pending":
                cursor.execute("""
                    INSERT INTO pending_payments (
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
                    VALUES (
                        %s, %s, %s, %s, %s,
                        CURDATE(),
                        DATE_ADD(CURDATE(), INTERVAL 7 DAY),
                        %s, %s, %s,
                        'Pending'
                    )
                """, (
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

            flash(
                f"Patient registered successfully. "
                f"Total: ₹{total_amount:.2f}",
                "success"
            )

            return redirect("/dashboard")

        except Exception:
            db.rollback()
            raise
        finally:
            cursor.close()
            db.close()

    # ==================================================
    # GET REQUEST: PARALLEL FETCHING (Tests, Doctors, Settings)
    # ==================================================
    def fetch_tests():
        conn = get_db()
        cur = conn.cursor()  # Use standard tuple cursor
        try:
            cur.execute("""
                SELECT
                    t.id,
                    t.test_name,
                    COALESCE(
                        lto.price,
                        lts.price,
                        t.price
                    ) AS price,
                    CASE
                        WHEN t.lab_id IS NULL
                        THEN 'Global Master'
                        ELSE 'Custom Lab Test'
                    END AS test_type
                FROM tests t

                LEFT JOIN lab_test_overrides lto
                    ON lto.test_id = t.id
                   AND lto.lab_id = %s
                   AND t.lab_id IS NULL

                LEFT JOIN lab_test_settings lts
                    ON lts.test_id = t.id
                   AND lts.lab_id = %s

                WHERE (
                        t.lab_id IS NULL
                        OR t.lab_id = %s
                      )
                  AND COALESCE(
                        lts.is_deleted,
                        FALSE
                      ) = FALSE
                  AND COALESCE(
                        lts.status,
                        t.status
                      ) = 'Active'

                ORDER BY t.test_name
            """, (
                numeric_lab_id,
                lab_id,
                lab_id
            ))
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()

    def fetch_doctors():
         conn = get_db()
         cur = conn.cursor()  # Standard tuple cursor
         try:
            cur.execute("""
                SELECT id, doctor_name
                FROM doctors
                WHERE status = 'Active'
                  AND lab_id = %s
                ORDER BY doctor_name
            """, (lab_id,))
            return cur.fetchall()
         finally:
            cur.close()
            conn.close()

    def fetch_lab_settings():
        conn = get_db()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        try:
            cur.execute("""
                SELECT lab_name, upi_id
                FROM lab_settings
                WHERE lab_id = %s
                LIMIT 1
            """, (lab_id,))
            return cur.fetchone()
        finally:
            cur.close()
            conn.close()

    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            f_tests = executor.submit(fetch_tests)
            f_doctors = executor.submit(fetch_doctors)
            f_settings = executor.submit(fetch_lab_settings)

            tests = f_tests.result()
            doctors = f_doctors.result()
            lab_settings = f_settings.result()

        return render_template(
            "patient_registration.html",
            tests=tests,
            doctors=doctors,
            lab_settings=lab_settings
        )
    except Exception:
        raise
@app.route("/generate-upi-qr")
@login_required
@role_required("Developer", "Admin", "Technician")
def generate_upi_qr():

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:

        lab_id = session["lab_id"]

        # -----------------------------------------
        # Get laboratory settings
        # -----------------------------------------

        cursor.execute("""
            SELECT
                lab_name,
                upi_id
            FROM lab_settings
            WHERE lab_id=%s
            LIMIT 1
        """, (lab_id,))

        settings = cursor.fetchone()

        if not settings:
            return "Laboratory settings not found", 404

        upi_id = settings.get("upi_id")

        lab_name = settings.get("lab_name") or "Laboratory"

        if not upi_id:
            return "UPI ID is not configured in Settings", 400

        # -----------------------------------------
        # Get amount
        # -----------------------------------------

        amount = request.args.get("amount", "0")

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            amount = 0

        if amount <= 0:
            return "Invalid payment amount", 400

        # -----------------------------------------
        # Optional transaction note
        # -----------------------------------------

        note = request.args.get(
            "note",
            "Laboratory Payment"
        )

        # -----------------------------------------
        # Create UPI URI
        # -----------------------------------------

        from urllib.parse import urlencode

        upi_params = urlencode({
            "pa": upi_id,
            "pn": lab_name,
            "am": f"{amount:.2f}",
            "cu": "INR",
            "tn": note
        })

        upi_uri = f"upi://pay?{upi_params}"

        print("=" * 60)
        print("UPI QR")
        print("UPI ID:", upi_id)
        print("Lab:", lab_name)
        print("Amount:", amount)
        print("UPI URI:", upi_uri)
        print("=" * 60)

        # -----------------------------------------
        # Generate QR
        # -----------------------------------------

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4
        )

        qr.add_data(upi_uri)
        qr.make(fit=True)

        img = qr.make_image(
            fill_color="black",
            back_color="white"
        )

        # -----------------------------------------
        # Convert image to memory
        # -----------------------------------------

        img_io = BytesIO()

        img.save(
            img_io,
            format="PNG"
        )

        img_io.seek(0)

        return send_file(
            img_io,
            mimetype="image/png"
        )

    except Exception as e:

        print(
            "UPI QR ERROR:",
            str(e)
        )

        return "Unable to generate UPI QR", 500

    finally:

        cursor.close()
        db.close()
@app.route("/pending-payments")
@login_required
@role_required("Developer", "Admin", "Technician")
def pending_payments():

    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor()

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
    cursor = db.cursor(pymysql.cursors.DictCursor)

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
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:

        # =====================================================
        # Load Pending Payment
        # =====================================================

        cursor.execute("""
            SELECT *
            FROM pending_payments
            WHERE id=%s
            AND lab_id=%s
        """, (payment_id, lab_id))

        payment = cursor.fetchone()

        if not payment:
            return "Payment not found.", 404


        # =====================================================
        # POST - COLLECT PAYMENT
        # =====================================================

        if request.method == "POST":

            # ---------------------------------------------
            # Get Amount
            # ---------------------------------------------

            try:

                receive_amount = Decimal(
                    request.form.get("receive_amount", "0")
                )

            except Exception:

                return "Invalid payment amount", 400


            payment_mode = request.form.get(
                "payment_mode"
            )


            # ---------------------------------------------
            # Validate Payment Mode
            # ---------------------------------------------

            if payment_mode not in [
                "Cash",
                "UPI"
            ]:

                return "Invalid payment mode", 400


            # ---------------------------------------------
            # Current Payment Values
            # ---------------------------------------------

            old_paid = Decimal(
                str(payment["paid_amount"] or 0)
            )

            total_amount = Decimal(
                str(payment["total_amount"] or 0)
            )

            remaining_amount = Decimal(
                str(payment["pending_amount"] or 0)
            )


            # =================================================
            # VALIDATION
            # =================================================

            if receive_amount <= Decimal("0.00"):

                return (
                    "Payment amount must be greater than zero",
                    400
                )


            if receive_amount > remaining_amount:

                return (
                    "Payment amount is greater than remaining balance",
                    400
                )


            # =================================================
            # CALCULATE NEW PAYMENT
            # =================================================

            new_paid = (
                old_paid +
                receive_amount
            )


            new_remaining = (
                total_amount -
                new_paid
            )


            if new_remaining < Decimal("0.00"):

                new_remaining = Decimal("0.00")


            # ---------------------------------------------
            # Payment Status
            # ---------------------------------------------

            if new_remaining == Decimal("0.00"):

                status = "Paid"

            else:

                status = "Pending"


            # =================================================
            # UPDATE PAYMENTS TABLE
            # =================================================

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


            # =================================================
            # UPDATE PENDING PAYMENTS TABLE
            # =================================================

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


            # =================================================
            # SAVE PAYMENT TRANSACTION
            # =================================================

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


            # =================================================
            # COMMIT
            # =================================================

            db.commit()


            print("=" * 60)
            print("PENDING PAYMENT COLLECTED")
            print("Patient ID:", payment["patient_id"])
            print("Receipt No:", payment["receipt_no"])
            print("Received:", receive_amount)
            print("Payment Mode:", payment_mode)
            print("New Paid:", new_paid)
            print("New Remaining:", new_remaining)
            print("Status:", status)
            print("=" * 60)


            return redirect(
                url_for("pending_payments")
            )


        # =====================================================
        # GET - SHOW COLLECT PAYMENT PAGE
        # =====================================================

        return render_template(
            "collect_payment.html",
            payment=payment
        )


    except Exception as e:

        db.rollback()

        print(
            "COLLECT PAYMENT ERROR:",
            str(e)
        )

        raise


    finally:

        cursor.close()
        db.close()
@app.route("/reports-management")
@login_required
@role_required("Developer", "Admin", "Technician")
def reports_management():
    lab_id = session["lab_id"]

    def fetch_reports():
        conn = get_db()
        cur = conn.cursor()  # Use standard tuple cursor
        try:
            cur.execute("""
                SELECT
                    p.patient_id,
                    p.name,
                    GROUP_CONCAT(
                        DISTINCT t.test_name
                        ORDER BY t.test_name
                        SEPARATOR ', '
                    ) AS tests,

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
                    AND (
                        t.lab_id IS NULL
                        OR t.lab_id = pt.lab_id
                    )

                WHERE p.lab_id = %s

                GROUP BY
                    p.id,
                    p.patient_id,
                    p.name,
                    p.lab_id

                ORDER BY p.id DESC
            """, (lab_id,))
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()
    def fetch_today_reports():
     conn = get_db()
     cur = conn.cursor()  # Standard tuple cursor
     try:
        cur.execute("""
            SELECT COUNT(*)
            FROM patients p
            WHERE p.lab_id = %s
              AND p.report_generated_on >= CURDATE()
              AND p.report_generated_on < CURDATE() + INTERVAL 1 DAY
        """, (lab_id,))
        res = cur.fetchone()
        return res[0] if res else 0
     finally:
        cur.close()
        conn.close()

    try:
        # Run both independent database tasks concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_reports = executor.submit(fetch_reports)
            future_today = executor.submit(fetch_today_reports)

            reports = future_reports.result()
            today_reports = future_today.result()

        # Calculate statistics in memory from fetched reports data
        total_reports = len(reports)

        completed_reports = sum(
            1 for report in reports
            if report[3] == "Completed"
        )

        pending_reports = sum(
            1 for report in reports
            if report[3] != "Completed"
        )

        return render_template(
            "reports_management.html",
            reports=reports,
            total_reports=total_reports,
            completed_reports=completed_reports,
            pending_reports=pending_reports,
            today_reports=today_reports
        )

    except Exception as e:
        print("=" * 60)
        print("[ERROR] reports_management()")
        print(str(e))
        print("=" * 60)
        raise
@app.route("/enter-results/<patient_id>", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin", "Technician")
def enter_results(patient_id):

    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor()

    try:
        # ==================================================
        # 1. LOAD PATIENT
        # ==================================================

        patient = load_patient(
            cursor,
            patient_id,
            lab_id
        )

        if not patient:
            flash("Patient not found.", "danger")
            return redirect(url_for("reports_management"))

        # ==================================================
        # 2. HANDLE POST REQUEST
        # ==================================================

        if request.method == "POST":

            # ----------------------------------------------
            # Report description
            # ----------------------------------------------

            report_description = request.form.get(
                "report_description", ""
            ).strip()

            # ----------------------------------------------
            # Selected signatories
            # ----------------------------------------------

            primary_signatory_id = request.form.get(
                "primary_signatory_id"
            )

            secondary_signatory_id = request.form.get(
                "secondary_signatory_id"
            )

            # ----------------------------------------------
            # Delete previous results
            # ----------------------------------------------

            delete_old_results(
                cursor,
                patient_id,
                lab_id
            )

            # ----------------------------------------------
            # Save selected signatories
            # ----------------------------------------------

            save_signatories(
                cursor,
                patient_id,
                lab_id,
                primary_signatory_id,
                secondary_signatory_id
            )

            # ----------------------------------------------
            # Save report description
            # ----------------------------------------------

            cursor.execute(
                """
                UPDATE patients
                SET report_description = %s
                WHERE patient_id = %s
                  AND lab_id = %s
                """,
                (
                    report_description,
                    patient_id,
                    lab_id
                )
            )

            # ----------------------------------------------
            # Get submitted parameter values
            # ----------------------------------------------

            parameter_values = request.form.to_dict()

            # ----------------------------------------------
            # Load parameter definitions
            # ----------------------------------------------

            cursor.execute(
                """
                SELECT
                    pd.id,
                    pd.display_name,
                    pd.short_name,
                    pd.parameter_code
                FROM parameter_definition pd

                JOIN report_components rc
                    ON pd.component_id = rc.id

                JOIN test_sections ts
                    ON rc.section_id = ts.id

                JOIN tests t
                    ON ts.test_id = t.id

                JOIN patient_tests pt
                    ON pt.test_id = t.id

                WHERE pt.patient_id = %s
                  AND pt.lab_id = %s
                  AND pd.status = 'active'

                ORDER BY pd.display_order
                """,
                (
                    patient_id,
                    lab_id
                )
            )

            parameter_rows = cursor.fetchall()

            # ----------------------------------------------
            # Normalize parameter values for formulas
            # ----------------------------------------------

            for row in parameter_rows:

                parameter_id = row[0]
                display_name = row[1]
                short_name = row[2]
                parameter_code = row[3]

                form_key = f"param_{parameter_id}"

                if form_key not in parameter_values:
                    continue

                value = parameter_values[form_key]

                if value in ("", None):
                    continue

                if parameter_code:
                    parameter_values[parameter_code] = value

                if short_name:
                    parameter_values[short_name] = value

                if display_name:
                    parameter_values[display_name] = value

            

           
            # ----------------------------------------------
            # Save manual results
            # ----------------------------------------------

            manual_values = save_manual_results(
                cursor,
                patient_id,
                lab_id,
                request.form
            )

            # ----------------------------------------------
            # Prepare values for formula calculations
            # ----------------------------------------------

            parameter_values.update(manual_values or {})

            print("=" * 60)
            print("[FORMULA INPUT VALUES]")
            print(parameter_values)
            print("=" * 60)

            # ----------------------------------------------
            # Calculate and save formula results ONCE
            # ----------------------------------------------

            save_formula_results(
                cursor,
                patient_id,
                lab_id,
                parameter_values
            )

            # ----------------------------------------------
            # Save dictionary/dropdown results
            # ----------------------------------------------

            save_dictionary_results(
                cursor,
                patient_id,
                lab_id,
                request.form
            )


            # ----------------------------------------------
            # Save dictionary/dropdown results
            # ----------------------------------------------

            save_dictionary_results(
                cursor,
                patient_id,
                lab_id,
                request.form
            )

            # ----------------------------------------------
            # Update report generation date
            # ----------------------------------------------

            # Update report generation date
            cursor.execute(
    """
    UPDATE patients
    SET report_generated_on = COALESCE(report_generated_on, NOW())
    WHERE patient_id = %s
      AND lab_id = %s
    """,
    (patient_id, lab_id)
)

            # ----------------------------------------------
            # Commit all changes
            # ----------------------------------------------

            db.commit()

            flash(
                "Report results saved successfully.",
                "success"
            )

            return redirect(
                url_for("reports_management")
            )

        # ==================================================
        # 3. LOAD SAVED REPORT DESCRIPTION
        # ==================================================

        cursor.execute(
            """
            SELECT report_description
            FROM patients
            WHERE patient_id = %s
              AND lab_id = %s
            LIMIT 1
            """,
            (
                patient_id,
                lab_id
            )
        )

        description_row = cursor.fetchone()

        report_description = (
            description_row[0]
            if description_row and description_row[0]
            else ""
        )

        # ==================================================
        # 4. BUILD REPORT STRUCTURE
        # ==================================================

        
# ==================================================
# 4. BUILD REPORT STRUCTURE
#    USING PATIENT AGE AND GENDER
# ==================================================

        patient_age = patient.get("age")
        patient_gender = patient.get("gender")

        print("=" * 60)
        print("[REFERENCE RANGE DEBUG]")
        print("Patient ID:", patient_id)
        print("Patient Age:", repr(patient_age))
        print("Patient Gender:", repr(patient_gender))
        print("=" * 60)

        report_structure = build_report_structure(
     cursor,
    patient_id=patient_id,
    patient_age=patient_age,
    patient_gender=patient_gender
)



        # ==================================================
        # 5. LOAD SAVED RESULTS
        # ==================================================

        saved_results = load_saved_results(
            cursor,
            patient_id,
            lab_id
        )

        component_results = load_component_results(
            cursor,
            patient_id,
            lab_id
        )

        report_structure = merge_results(
            report_structure,
            saved_results,
            component_results
        )

        # ==================================================
        # 6. LOAD SIGNATORIES
        # ==================================================

        cursor.execute(
            """
            SELECT
                rs.id,
                rs.name
            FROM report_signatories rs

            JOIN laboratories l
                ON rs.lab_id = l.id

            WHERE l.lab_id = %s
              AND rs.status = 'Active'

            ORDER BY rs.name
            """,
            (lab_id,)
        )

        signatories = cursor.fetchall()

        print("DEBUG lab_id:", repr(lab_id))
        print("DEBUG signatories:", repr(signatories))
        print("DEBUG signatory count:", len(signatories))

        # ==================================================
        # 7. RENDER PAGE
        # ==================================================

        return render_template(
            "enter_results.html",
            patient=patient,
            report_structure=report_structure,
            report_description=report_description,
            signatories=signatories
        )

    except Exception as e:

        db.rollback()

        print("Error in enter_results:", repr(e))

        raise

    finally:

        cursor.close()
        db.close()
# ============================================================
# VIEW REPORT
# ============================================================


# ============================================================
# VIEW REPORT
# ============================================================

@app.route("/view-report/<patient_id>")
@login_required
@role_required("Developer", "Admin", "Technician")
def view_report(patient_id):

    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor()

    try:
        # ====================================================
        # 1. LOAD PATIENT
        # ====================================================

        patient = load_patient(
            cursor,
            patient_id,
            lab_id
        )

        if not patient:
            return "Patient not found", 404

        # Get the patient's actual age and gender.
        patient_age = patient.get("age")
        patient_gender = patient.get("gender")

        print("=" * 60)
        print("VIEW REPORT DEBUG")
        print("Patient ID:", patient_id)
        print("Patient age:", patient_age)
        print("Patient gender:", patient_gender)
        print("Lab ID:", lab_id)
        print("=" * 60)

        # ====================================================
        # 2. LOAD REPORT DESCRIPTION
        # ====================================================

        cursor.execute(
            """
            SELECT report_description
            FROM patients
            WHERE patient_id = %s
              AND lab_id = %s
            LIMIT 1
            """,
            (patient_id, lab_id)
        )

        description_row = cursor.fetchone()

        report_description = (
            description_row[0]
            if description_row and description_row[0]
            else ""
        )

        # ====================================================
        # 3. LOAD LAB SETTINGS
        # ====================================================

        settings_cursor = db.cursor(pymysql.cursors.DictCursor)

        try:
            settings_cursor.execute(
                """
                SELECT
                    lab_name,
                    logo,
                    signature,
                    stamp,
                    report_header,
                    report_footer
                FROM lab_settings
                WHERE lab_id = %s
                LIMIT 1
                """,
                (lab_id,)
            )

            lab_settings = settings_cursor.fetchone()

        finally:
            settings_cursor.close()

        # ====================================================
        # 4. BUILD REPORT STRUCTURE
        #    USING PATIENT-SPECIFIC REFERENCE RANGES
        # ====================================================

        report_structure = build_report_structure(
            cursor,
            patient_id=patient_id,
            patient_age=patient_age,
            patient_gender=patient_gender
        )

        # ====================================================
        # 5. LOAD SAVED PARAMETER RESULTS
        # ====================================================

        saved_results = load_saved_results(
            cursor,
            patient_id,
            lab_id
        )

        # ====================================================
        # 6. LOAD DICTIONARY / COMPONENT RESULTS
        # ====================================================

        component_results = load_component_results(
            cursor,
            patient_id,
            lab_id
        )

        # ====================================================
        # 7. MERGE ALL RESULTS
        # ====================================================

        report_structure = merge_results(
            report_structure,
            saved_results,
            component_results
        )

        # ====================================================
        # 8. APPLY REFERENCE RANGE STATUS
        # ====================================================

        report_structure = apply_reference_status(
            report_structure
        )

        # ====================================================
        # 9. LOAD REPORT SIGNATORIES
        # ====================================================

        signatories = load_signatories(
            cursor,
            patient_id,
            lab_id
        )

        # ====================================================
        # 10. GENERATE SECURE QR TOKEN
        # ====================================================

        qr_token = create_report_qr_token(
            patient_id,
            lab_id
        )

        # ====================================================
        # 11. CREATE PUBLIC REPORT URL
        # ====================================================

        public_report_url = (
            f"http://10.194.109.107:5000"
            f"/public-report/{qr_token}"
        )

        # ====================================================
        # 12. GENERATE QR IMAGE
        # ====================================================

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2
        )

        qr.add_data(public_report_url)
        qr.make(fit=True)

        qr_image = qr.make_image()

        # ====================================================
        # 13. CONVERT QR IMAGE TO BASE64
        # ====================================================

        buffer = io.BytesIO()

        qr_image.save(
            buffer,
            format="PNG"
        )

        qr_base64 = base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")

        # ====================================================
        # 14. DEBUG INFORMATION
        # ====================================================

        print("=" * 60)
        print("VIEW REPORT DEBUG")
        print("Patient ID:", patient_id)
        print("Patient age:", patient_age)
        print("Patient gender:", patient_gender)
        print("Report description:", repr(report_description))
        print("Signatories:", signatories)
        print("Lab settings:", lab_settings)
        print("=" * 60)

        # ====================================================
        # 15. RENDER REPORT
        # ====================================================

        return render_template(
            "view_report.html",

            # PATIENT
            patient=patient,

            # REPORT STRUCTURE
            report_structure=report_structure,

            # REPORT DESCRIPTION
            report_description=report_description,

            # SIGNATORIES
            signatories=signatories,

            # LAB SETTINGS
            lab_settings=lab_settings,

            # REPORT DATES
            report_date=patient.get("report_date"),
            collection_date=patient.get("collection_date"),

            # QR CODE
            qr_code=qr_base64,

            # REPORT MODE
            public_view=False
        )

    except Exception as e:
        db.rollback()

        print("Error in view_report:", repr(e))

        raise

    finally:
        cursor.close()
        db.close()


# ============================================================
# PUBLIC REPORT - QR CODE ACCESS
# ============================================================


@app.route("/public-report/<token>")
def public_report(token):

    # ============================================================
    # READ SECURE QR TOKEN
    # ============================================================

    patient_id, lab_id = read_report_qr_token(token)

    if not patient_id or not lab_id:
        return "Invalid or expired report QR code.", 403

    db = get_db()
    cursor = db.cursor()

    try:

        # ========================================================
        # LOAD PATIENT
        # ========================================================

        patient = load_patient(
            cursor,
            patient_id,
            lab_id
        )

        if not patient:
            return "Report not found.", 404

        # ========================================================
        # LOAD TESTS USING TOKEN LAB_ID
        # ========================================================
        # IMPORTANT:
        # Do NOT use load_patient_tests() here.
        # That function uses session["lab_id"].
        # Public QR reports do not have a login session.

        cursor.execute("""
            SELECT
                pt.test_id,
                t.test_name
            FROM patient_tests pt
            JOIN tests t
                ON pt.test_id = t.id
            WHERE pt.patient_id = %s
            AND pt.lab_id = %s
            ORDER BY t.test_name
        """, (
            patient_id,
            lab_id
        ))

        tests = cursor.fetchall()

        # ========================================================
        # BUILD REPORT STRUCTURE
        # ========================================================

        report_structure = build_report_structure(
            cursor,
            tests=tests
        )

        # ========================================================
        # LOAD SAVED PARAMETER RESULTS
        # ========================================================

        saved_results = load_saved_results(
            cursor,
            patient_id,
            lab_id
        )

        # ========================================================
        # LOAD DICTIONARY / COMPONENT RESULTS
        # ========================================================

        component_results = load_component_results(
            cursor,
            patient_id,
            lab_id
        )

        # ========================================================
        # MERGE RESULTS
        # ========================================================

        report_structure = merge_results(
            report_structure,
            saved_results,
            component_results
        )

        # ========================================================
        # APPLY REFERENCE STATUS
        # ========================================================

        report_structure = apply_reference_status(
            report_structure
        )

        # ========================================================
        # LOAD SIGNATORIES
        # ========================================================

        signatories = load_signatories(
            cursor,
            patient_id,
            lab_id
        )

        # ========================================================
        # RENDER PUBLIC REPORT
        # ========================================================

        return render_template(
            "view_report.html",
            patient=patient,
            report_structure=report_structure,
            signatories=signatories,
            report_date=patient.get("report_date"),
            collection_date=patient.get("collection_date"),
            qr_code=None,
            public_view=True
        )

    finally:

        cursor.close()
        db.close()
@app.route("/edit-report/<patient_id>", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin")
def edit_report(patient_id):

    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor()

    try:
        # =========================================
        # LOAD PATIENT
        # =========================================
        patient = load_patient(
            cursor,
            patient_id,
            lab_id
        )

        if not patient:
            flash("Patient not found.", "danger")
            return redirect(url_for("reports_management"))

        # =========================================
        # LOAD ACTIVE SIGNATORIES
        # =========================================
        cursor.execute(
            """
            SELECT
                rs.id,
                rs.name
            FROM report_signatories rs
            JOIN laboratories l
                ON rs.lab_id = l.id
            WHERE l.lab_id = %s
              AND rs.status = 'Active'
            ORDER BY rs.name
            """,
            (lab_id,)
        )

        signatories = cursor.fetchall()

        # =========================================
        # POST: UPDATE REPORT
        # =========================================
        if request.method == "POST":

            try:
                primary_signatory_id = request.form.get(
                    "primary_signatory_id"
                )

                secondary_signatory_id = request.form.get(
                    "secondary_signatory_id"
                )

                # Remove old results.
                delete_old_results(
                    cursor,
                    patient_id,
                    lab_id
                )

                # Save selected signatories.
                save_signatories(
                    cursor,
                    patient_id,
                    lab_id,
                    primary_signatory_id,
                    secondary_signatory_id
                )

                # Save manual parameter results.
                parameter_values = save_manual_results(
                    cursor,
                    patient_id,
                    lab_id,
                    request.form
                )

                if parameter_values is None:
                    parameter_values = {}

                # Calculate and save formula results.
                save_formula_results(
                    cursor,
                    patient_id,
                    lab_id,
                    parameter_values
                )

                # Save dictionary/dropdown results.
                save_dictionary_results(
                    cursor,
                    patient_id,
                    lab_id,
                    request.form
                )

                # Update report generated date.
                cursor.execute(
                    """
                    UPDATE patients
                    SET report_generated_on = NOW()
                    WHERE patient_id = %s
                      AND lab_id = %s
                    """,
                    (patient_id, lab_id)
                )

                db.commit()

                flash(
                    "Report updated successfully.",
                    "success"
                )

                return redirect(
                    url_for(
                        "view_report",
                        patient_id=patient_id
                    )
                )

            except Exception:
                db.rollback()
                raise

        # =========================================
        # GET: LOAD EXISTING REPORT
        # =========================================

        # Build report structure.
        report_structure = build_report_structure(
            cursor,
            patient_id
        )

        # Load saved parameter results.
        saved_results = load_saved_results(
            cursor,
            patient_id,
            lab_id
        )

        # Load saved component results.
        component_results = load_component_results(
            cursor,
            patient_id,
            lab_id
        )

        # Merge saved results into the report structure.
        report_structure = merge_results(
            report_structure,
            saved_results,
            component_results
        )

        # Apply reference-range status.
        report_structure = apply_reference_status(
            report_structure
        )

        # =========================================
        # RENDER EDIT REPORT
        # =========================================
        return render_template(
            "edit_report.html",
            patient=patient,
            patient_id=patient_id,
            report_structure=report_structure,
            signatories=signatories
        )

    except Exception as e:
        db.rollback()

        print("=" * 60)
        print("[ERROR] edit_report()")
        print(str(e))
        print("=" * 60)

        raise

    finally:
        cursor.close()
        db.close()
@app.route("/delete-report/<patient_id>", methods=["POST"])
@login_required
@role_required("Developer", "Admin")
def delete_report(patient_id):
    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor()

    try:
        # Verify that this patient belongs to the current laboratory.
        patient = load_patient(cursor, patient_id, lab_id)

        if not patient:
            flash("Patient not found.", "danger")
            return redirect(url_for("reports_management"))

        # Delete parameter results for this patient and laboratory.
        cursor.execute(
            """
            DELETE FROM test_results
            WHERE patient_id = %s
              AND lab_id = %s
            """,
            (patient_id, lab_id)
        )

        # Delete saved component results if your application stores them
        # in a separate table. Add that deletion only after confirming
        # the actual table name and its schema.

        db.commit()
        flash("Report results deleted successfully.", "success")

    except Exception as e:
        db.rollback()
        print("[DELETE REPORT ERROR]", str(e))
        flash("Unable to delete report results.", "danger")

    finally:
        cursor.close()
        db.close()

    return redirect(url_for("reports_management"))
@app.route("/analytics")
@login_required
@role_required("Developer", "Admin")
def analytics():

    lab_id = session["lab_id"]

    db = get_db()
    cursor = db.cursor()

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
   
        cursor.execute("""
        SELECT
            DATE_FORMAT(payment_date, '%%Y-%%m'),
            SUM(paid_amount)
        FROM payments
        WHERE lab_id = %s
        GROUP BY DATE_FORMAT(payment_date, '%%Y-%%m')
        ORDER BY DATE_FORMAT(payment_date, '%%Y-%%m')
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
    cursor = db.cursor()

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
    cursor = db.cursor()

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


        # -------- Load Lab Settings --------
        settings_cursor = db.cursor(pymysql.cursors.DictCursor)

        settings_cursor.execute("""
            SELECT
                lab_name,
                logo,
                signature,
                stamp,
                report_header,
                report_footer

            FROM lab_settings

            WHERE lab_id=%s

            LIMIT 1
        """, (lab_id,))

        lab_settings = settings_cursor.fetchone()

        settings_cursor.close()


        # -------- Debug --------
        print("\n===== BILL =====")
        print(bill)

        print("\n===== TESTS =====")
        for t in tests:
            print(t)

        print("\n===== LAB SETTINGS =====")
        print(lab_settings)


        # -------- Render Bill --------
        return render_template(
            "view_bill.html",
            bill=bill,
            tests=tests,
            lab_settings=lab_settings
        )


    finally:
        cursor.close()
        db.close()
@app.route("/patient-search")
@login_required
@role_required("Developer", "Admin", "Technician")
def patient_search():
    db = get_db()
    cursor = db.cursor()

    lab_id = session["lab_id"]

    try:
        search = request.args.get("search", "").strip()
        is_live_search = request.args.get("live") == "1"

        if search:
            cursor.execute(
                """
                SELECT
                    patient_id,
                    name,
                    age,
                    gender,
                    mobile,
                    doctor_name
                FROM patients
                WHERE lab_id = %s
                  AND (
                      patient_id LIKE %s
                      OR name LIKE %s
                      OR mobile LIKE %s
                      OR doctor_name LIKE %s
                  )
                ORDER BY id DESC
                LIMIT 100
                """,
                (
                    lab_id,
                    f"%{search}%",
                    f"%{search}%",
                    f"%{search}%",
                    f"%{search}%"
                )
            )
        else:
            cursor.execute(
                """
                SELECT
                    patient_id,
                    name,
                    age,
                    gender,
                    mobile,
                    doctor_name
                FROM patients
                WHERE lab_id = %s
                ORDER BY id DESC
                LIMIT 20
                """,
                (lab_id,)
            )

        rows = cursor.fetchall()

        # Return JSON for live-search requests.
        if is_live_search:
            patients = [
                {
                    "patient_id": row[0],
                    "name": row[1],
                    "age": row[2],
                    "gender": row[3],
                    "mobile": row[4],
                    "doctor_name": row[5]
                }
                for row in rows
            ]

            return jsonify({
                "success": True,
                "patients": patients,
                "count": len(patients)
            })

        # Preserve normal page rendering.
        return render_template(
            "patient_search.html",
            patients=rows,
            search=search
        )

    except Exception:
        app.logger.exception("Patient search failed")
        raise

    finally:
        cursor.close()
        db.close()

@app.route("/add-test/<int:department_id>", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin")
def add_test(department_id):

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    role = session["role"]

    # ==========================================================
    # LAB ID
    # ==========================================================

    if role == "Developer":
        lab_id = None
    else:
        lab_id = session["lab_id"]

    try:

        # ==========================================================
        # 1. GET DEPARTMENT
        # ==========================================================

        cursor.execute("""
            SELECT
                id,
                department_name,
                department_code
            FROM departments
            WHERE id = %s
        """, (department_id,))

        department = cursor.fetchone()

        if not department:

            flash("Department not found.", "danger")

            return redirect(
                url_for("test_builder.department_list")
            )

        # ==========================================================
        # 2. GENERATE GLOBALLY UNIQUE TEST CODE
        # ==========================================================
        #
        # test_code has a UNIQUE constraint in your database.
        #
        # Therefore we CANNOT generate the number separately
        # for each lab.
        #
        # Example:
        # LAB0001 -> HEM-0001
        # LAB0002 -> HEM-0002
        #
        # ==========================================================

        cursor.execute("""
            SELECT
                MAX(
                    CAST(
                        SUBSTRING_INDEX(test_code, '-', -1)
                        AS UNSIGNED
                    )
                ) AS max_number
            FROM tests
            WHERE department_id = %s
        """, (department_id,))

        code_result = cursor.fetchone()

        max_number = code_result["max_number"]

        if max_number is None:
            next_no = 1
        else:
            next_no = max_number + 1

        test_code = (
            f"{department['department_code']}-{next_no:04d}"
        )

        # ==========================================================
        # 3. POST REQUEST
        # ==========================================================

        if request.method == "POST":

            print("\n" + "=" * 60)
            print("ADD TEST REQUEST")
            print("Role:", role)
            print("Lab ID:", lab_id)
            print("Department ID:", department_id)
            print("Generated Test Code:", test_code)
            print("=" * 60)

            # ======================================================
            # GET FORM DATA
            # ======================================================

            test_name = request.form.get(
                "test_name", ""
            ).strip()

            short_name = request.form.get(
                "short_name", ""
            ).strip()

            price = request.form.get(
                "price", ""
            ).strip()

            sample_type = request.form.get(
                "sample_type", ""
            ).strip()

            report_time = request.form.get(
                "report_time", ""
            ).strip()

            description = request.form.get(
                "description", ""
            ).strip()

            # ======================================================
            # VALIDATION
            # ======================================================

            if not test_name:

                flash(
                    "Test name is required.",
                    "danger"
                )

                return render_template(
                    "test_builder/test_form.html",
                    department=department,
                    test_code=test_code
                )

            if not short_name:

                flash(
                    "Short name is required.",
                    "danger"
                )

                return render_template(
                    "test_builder/test_form.html",
                    department=department,
                    test_code=test_code
                )

            if not price:

                flash(
                    "Price is required.",
                    "danger"
                )

                return render_template(
                    "test_builder/test_form.html",
                    department=department,
                    test_code=test_code
                )

            if not sample_type:

                flash(
                    "Sample type is required.",
                    "danger"
                )

                return render_template(
                    "test_builder/test_form.html",
                    department=department,
                    test_code=test_code
                )

            if not report_time:

                flash(
                    "Report time is required.",
                    "danger"
                )

                return render_template(
                    "test_builder/test_form.html",
                    department=department,
                    test_code=test_code
                )

            # ==========================================================
            # 4. DUPLICATE TEST NAME CHECK
            # ==========================================================
            #
            # Test name is allowed to exist in different labs.
            #
            # Therefore:
            #
            # LAB0001 + Hematology + CBC -> allowed
            # LAB0002 + Hematology + CBC -> allowed
            #
            # But:
            #
            # LAB0002 + Hematology + CBC
            # LAB0002 + Hematology + CBC
            #
            # -> NOT allowed
            #
            # ==========================================================

            if role == "Developer":

                cursor.execute("""
                    SELECT id
                    FROM tests
                    WHERE LOWER(test_name) = LOWER(%s)
                    AND department_id = %s
                    AND lab_id IS NULL
                    LIMIT 1
                """, (
                    test_name,
                    department_id
                ))

            else:

                cursor.execute("""
                    SELECT id
                    FROM tests
                    WHERE LOWER(test_name) = LOWER(%s)
                    AND department_id = %s
                    AND lab_id = %s
                    LIMIT 1
                """, (
                    test_name,
                    department_id,
                    lab_id
                ))

            existing_test = cursor.fetchone()

            if existing_test:

                flash(
                    "This test already exists in this laboratory.",
                    "warning"
                )

                return redirect(
                    url_for(
                        "add_test",
                        department_id=department_id
                    )
                )
            department_code = department["department_code"]

            if role == "Developer":
             code_prefix = f"DEV-{department_code}"
            else:
             code_prefix = f"{lab_id}-{department_code}"

            cursor.execute("""
    SELECT
        MAX(
            CAST(
                SUBSTRING_INDEX(test_code, '-', -1)
                AS UNSIGNED
            )
        ) AS max_number
    FROM tests
    WHERE department_id = %s
      AND test_code LIKE %s
""", (
    department_id,
    f"{code_prefix}-%"
))

            code_result = cursor.fetchone()
            max_number = code_result["max_number"]

            next_no = (max_number or 0) + 1

            test_code = f"{code_prefix}-{next_no:04d}"
            # ==========================================================
            # 5. INSERT INTO tests
            # ==========================================================

            cursor.execute("""
                INSERT INTO tests
                (
                    lab_id,
                    department_id,
                    department,
                    test_code,
                    test_name,
                    short_name,
                    price,
                    description,
                    sample_type,
                    report_time,
                    status
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    'Active'
                )
            """, (
                lab_id,
                department_id,
                department["department_name"],
                test_code,
                test_name,
                short_name,
                price,
                description,
                sample_type,
                report_time
            ))

            test_id = cursor.lastrowid

            print("Test inserted.")
            print("Test ID:", test_id)

            # ==========================================================
            # 6. CREATE DEFAULT TEST SECTION
            # ==========================================================

            cursor.execute("""
                INSERT INTO test_sections
                (
                    test_id,
                    lab_id,
                    section_name,
                    description,
                    display_order,
                    is_visible
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    1,
                    1
                )
            """, (
                test_id,
                lab_id,
                department["department_name"],
                ""
            ))

            print("Test section created.")

            # ==========================================================
            # 7. CREATE LAB TEST SETTINGS
            # ==========================================================

            if role != "Developer":

                cursor.execute("""
                    INSERT INTO lab_test_settings
                    (
                        lab_id,
                        test_id,
                        price,
                        status,
                        customized
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        'Active',
                        1
                    )
                """, (
                    lab_id,
                    test_id,
                    price
                ))

                print("Lab test settings created.")

            # ==========================================================
            # 8. COMMIT EVERYTHING
            # ==========================================================

            db.commit()

            print("\n" + "=" * 60)
            print("TEST ADDED SUCCESSFULLY")
            print("Test ID:", test_id)
            print("Test Code:", test_code)
            print("Test Name:", test_name)
            print("Lab ID:", lab_id)
            print("=" * 60)

            flash(
                "Test added successfully.",
                "success"
            )

            # ==========================================================
            # 9. REDIRECT TO DEPARTMENT TESTS
            # ==========================================================

            return redirect(
                url_for(
                    "test_builder.department_tests",
                    department_id=department_id
                )
            )

        # ==========================================================
        # 10. GET REQUEST
        # ==========================================================

        return render_template(
            "test_builder/test_form.html",
            department=department,
            test_code=test_code
        )

    # ==============================================================
    # ERROR HANDLING
    # ==============================================================

    except Exception as e:

        db.rollback()

        print("\n" + "=" * 60)
        print("❌ ERROR WHILE ADDING TEST")
        print("Error:", str(e))
        print("=" * 60)

        flash(
            f"Unable to add test: {str(e)}",
            "danger"
        )

        return render_template(
            "test_builder/test_form.html",
            department=department,
            test_code=test_code
        )

    # ==============================================================
    # CLOSE DATABASE
    # ==============================================================

    finally:

        cursor.close()
        db.close()

from concurrent.futures import ThreadPoolExecutor

@app.route("/expenses", methods=["GET", "POST"])
@login_required
@role_required("Developer", "Admin")
def expenses():
    lab_id = session["lab_id"]

    # =========================================================
    # ADD DOCTOR (POST REQUEST)
    # =========================================================
    if request.method == "POST":
        doctor_name = request.form["doctor_name"].strip()
        commission = request.form["commission_percent"]

        conn = get_db()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        try:
            cur.execute("""
                INSERT INTO doctors
                (
                    lab_id,
                    doctor_name,
                    commission_percent
                )
                VALUES (%s, %s, %s)
            """, (
                lab_id,
                doctor_name,
                commission
            ))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

        return redirect(url_for("expenses"))

    # =========================================================
    # GET REQUEST: DATE FILTERS & PARALLEL FETCHING
    # =========================================================
    from_date = request.args.get("from_date", "").strip()
    to_date = request.args.get("to_date", "").strip()

    def fetch_doctors_list():
        conn = get_db()
        cur = None
        try:
            cur = conn.cursor(pymysql.cursors.DictCursor)
            cur.execute("""
                SELECT
                    id,
                    doctor_name,
                    commission_percent,
                    status
                FROM doctors
                WHERE lab_id = %s
                ORDER BY doctor_name
            """, (lab_id,))
            return cur.fetchall()
        finally:
            if cur:
                cur.close()
            conn.close()

    def fetch_doctor_summary():
        conn = get_db()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        try:
            query = """
                SELECT
                    d.id,
                    d.doctor_name,
                    d.commission_percent,
                    COUNT(DISTINCT p.patient_id) AS total_patients,
                    COALESCE(SUM(pay.total_amount), 0) AS total_business,
                    COALESCE(SUM(pay.total_amount * d.commission_percent / 100), 0) AS total_commission,
                    d.status
                FROM doctors d
                LEFT JOIN patients p
                    ON d.id = p.doctor_id
                    AND d.lab_id = p.lab_id
                LEFT JOIN payments pay
                    ON p.patient_id = pay.patient_id
                    AND p.lab_id = pay.lab_id
                WHERE d.lab_id = %s
            """
            params = [lab_id]

            if from_date and to_date:
                query += """
                    AND pay.payment_date >= %s
                    AND pay.payment_date < DATE_ADD(%s, INTERVAL 1 DAY)
                """
                params.extend([from_date, to_date])
            elif from_date:
                query += """
                    AND pay.payment_date >= %s
                """
                params.append(from_date)
            elif to_date:
                query += """
                    AND pay.payment_date < DATE_ADD(%s, INTERVAL 1 DAY)
                """
                params.append(to_date)

            query += """
                GROUP BY
                    d.id,
                    d.doctor_name,
                    d.commission_percent,
                    d.status
                ORDER BY d.doctor_name
            """

            cur.execute(query, tuple(params))
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()

    # Run both independent database tasks concurrently in background threads
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_doctors = executor.submit(fetch_doctors_list)
            future_summary = executor.submit(fetch_doctor_summary)

            doctors = future_doctors.result()
            summary = future_summary.result()

        return render_template(
            "expenses.html",
            doctors=doctors,
            doctor_summary=summary,
            from_date=from_date,
            to_date=to_date
        )
    except Exception:
        raise

@app.route("/doctor-patients/<int:doctor_id>")
@login_required
@role_required("Developer", "Admin")
def doctor_patients(doctor_id):

    db = get_db()
    cursor = db.cursor()
    lab_id = session["lab_id"]

    try:

        # =========================================================
        # DATE FILTER
        # =========================================================

        from_date = request.args.get("from_date", "").strip()
        to_date = request.args.get("to_date", "").strip()

        # Validate date range
        if from_date and to_date and from_date > to_date:
            return "From Date cannot be greater than To Date", 400

        # =========================================================
        # DOCTOR INFORMATION
        # =========================================================

        cursor.execute("""
            SELECT
                doctor_name,
                commission_percent
            FROM doctors
            WHERE id = %s
              AND lab_id = %s
        """, (
            doctor_id,
            lab_id
        ))

        doctor = cursor.fetchone()

        if not doctor:
            return "Doctor not found", 404

        doctor_name = doctor[0]
        commission_percent = float(doctor[1])

        # =========================================================
        # PATIENTS
        # =========================================================

        query = """
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

            WHERE p.doctor_id = %s
              AND p.lab_id = %s
        """

        params = [
            doctor_id,
            lab_id
        ]

        # =========================================================
        # DATE RANGE FILTER
        # =========================================================

        if from_date and to_date:

            query += """
                AND p.created_at >= %s
                AND p.created_at < DATE_ADD(%s, INTERVAL 1 DAY)
            """

            params.extend([
                from_date,
                to_date
            ])

        elif from_date:

            query += """
                AND p.created_at >= %s
            """

            params.append(from_date)

        elif to_date:

            query += """
                AND p.created_at < DATE_ADD(%s, INTERVAL 1 DAY)
            """

            params.append(to_date)

        # =========================================================
        # ORDER
        # =========================================================

        query += """
            ORDER BY p.created_at DESC
        """

        cursor.execute(
            query,
            tuple(params)
        )

        patients = cursor.fetchall()

        # =========================================================
        # CALCULATE TOTALS FROM FILTERED PATIENTS
        # =========================================================

        total_patients = len(patients)

        total_business = sum(
            float(row[4] or 0)
            for row in patients
        )

        total_commission = (
            total_business * commission_percent
        ) / 100

        # =========================================================
        # RENDER
        # =========================================================

        return render_template(
            "doctor_patients.html",

            doctor_id=doctor_id,
            doctor_name=doctor_name,
            commission_percent=commission_percent,

            patients=patients,

            total_patients=total_patients,
            total_business=total_business,
            total_commission=total_commission,

            from_date=from_date,
            to_date=to_date
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()
@app.route("/toggle-doctor-status/<int:doctor_id>")
@login_required
@role_required("Developer", "Admin", "Technician")
def toggle_doctor_status(doctor_id):

    db = get_db()
    cursor = db.cursor()
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
    cursor = db.cursor()
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
    cursor = db.cursor(pymysql.cursors.DictCursor)
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
    cursor = db.cursor(pymysql.cursors.DictCursor)
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

        cursor.execute("""
    SELECT
        t.test_name AS test_name,
        COALESCE(lto.price, t.price) AS original_price,
        pt.amount AS patient_price
    FROM patient_tests pt
    JOIN tests t
        ON t.id = pt.test_id
    LEFT JOIN lab_test_overrides lto
        ON lto.test_id = t.id
       AND lto.lab_id = (
            SELECT id
            FROM laboratories
            WHERE lab_id = pt.lab_id
       )
       AND t.lab_id IS NULL
    WHERE pt.patient_id = %s
      AND pt.lab_id = %s
    ORDER BY t.test_name
""", (payment["patient_id"], lab_id))

        tests = cursor.fetchall()
        print("\n========== PAYMENT DETAILS DEBUG ==========")
        print("Receipt:", receipt_no)
        print("Patient:", payment["patient_id"])
        print("Tests returned from database:")

        for test in tests:
            print({
                "test_name": test["test_name"],
                "original_price": test["original_price"],
                "patient_price": test["patient_price"]
            })

        print("============================================\n")
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
@role_required("Developer", "Admin")
def settings():
    db = None
    cursor = None

    try:
        # --------------------------------------------------
        # 1. Validate session and connect to database
        # --------------------------------------------------
        lab_id = session.get("lab_id")

        if not lab_id:
            flash("Your session has expired. Please log in again.", "warning")
            return redirect(url_for("login"))

        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)

        # --------------------------------------------------
        # 2. Get internal integer laboratory ID
        # --------------------------------------------------
        cursor.execute(
            """
            SELECT id
            FROM laboratories
            WHERE lab_id = %s
            LIMIT 1
            """,
            (lab_id,)
        )

        lab = cursor.fetchone()

        if not lab:
            flash("Laboratory not found.", "danger")
            return redirect(url_for("dashboard"))

        laboratory_id = lab["id"]

        # --------------------------------------------------
        # 3. Ensure upload directories exist
        # --------------------------------------------------
        upload_dirs = {
            "logo": app.config.get("UPLOAD_LOGO"),
            "signature": app.config.get("UPLOAD_SIGNATURE"),
            "stamp": app.config.get("UPLOAD_STAMP"),
            "signatory": app.config.get("UPLOAD_SIGNATORY"),
        }

        for directory in upload_dirs.values():
            if directory:
                os.makedirs(directory, exist_ok=True)

        report_header_dir = os.path.join(
            str(UPLOAD_BASE_DIR), "report_header"
        )
        report_footer_dir = os.path.join(
            str(UPLOAD_BASE_DIR), "report_footer"
        )

        os.makedirs(report_header_dir, exist_ok=True)
        os.makedirs(report_footer_dir, exist_ok=True)

        # --------------------------------------------------
        # 4. Handle POST request
        # --------------------------------------------------
        if request.method == "POST":

            # Fetch existing settings
            cursor.execute(
                """
                SELECT id
                FROM lab_settings
                WHERE lab_id = %s
                LIMIT 1
                """,
                (lab_id,)
            )

            existing = cursor.fetchone()

            # Get uploaded files ONLY inside the request
            logo = request.files.get("logo")
            signature = request.files.get("signature")
            stamp = request.files.get("stamp")
            report_header = request.files.get("report_header")
            report_footer = request.files.get("report_footer")
            signatory_signature = request.files.get(
                "signatory_signature"
            )

            # --------------------------------------------------
            # 5. Save uploaded files
            # --------------------------------------------------
            def save_upload(file, directory, prefix=None):
                if not file or not file.filename:
                    return None

                safe_name = secure_filename(file.filename)

                if not safe_name:
                    raise ValueError("Invalid uploaded filename.")

                filename = (
                    f"{prefix}_{uuid.uuid4().hex}_{safe_name}"
                    if prefix
                    else f"{uuid.uuid4().hex}_{safe_name}"
                )

                os.makedirs(directory, exist_ok=True)
                upload_result = cloudinary.uploader.upload(
    file,
    folder="medilens/lab-assets",
    resource_type="image"
)

                image_url = upload_result["secure_url"]

                return image_url

            logo_name = save_upload(
                logo, upload_dirs["logo"]
            ) if logo and logo.filename and upload_dirs["logo"] else None

            signature_name = save_upload(
                signature, upload_dirs["signature"]
            ) if signature and signature.filename and upload_dirs["signature"] else None

            stamp_name = save_upload(
                stamp, upload_dirs["stamp"]
            ) if stamp and stamp.filename and upload_dirs["stamp"] else None

            report_header_name = save_upload(
                report_header, report_header_dir, "header"
            )

            report_footer_name = save_upload(
                report_footer, report_footer_dir, "footer"
            )

            # --------------------------------------------------
            # 6. Collect settings form data
            # --------------------------------------------------
            data = (
                request.form.get("lab_name", "").strip(),
                request.form.get("owner_name", "").strip(),
                request.form.get("registration_no", "").strip(),
                request.form.get("gst_no", "").strip(),
                request.form.get("nabl_no", "").strip(),
                request.form.get("address", "").strip(),
                request.form.get("city", "").strip(),
                request.form.get("state", "").strip(),
                request.form.get("pincode", "").strip(),
                request.form.get("mobile", "").strip(),
                request.form.get("alt_mobile", "").strip(),
                request.form.get("email", "").strip(),
                request.form.get("website", "").strip(),
                request.form.get("receipt_prefix", "RCPT").strip(),
                request.form.get("patient_prefix", "PAT").strip(),
                request.form.get("upi_id", "").strip(),
            )

            # --------------------------------------------------
            # 7. Update or insert laboratory settings
            # --------------------------------------------------
            if existing:
                cursor.execute(
                    """
                    UPDATE lab_settings
                    SET
                        lab_name = %s,
                        owner_name = %s,
                        registration_no = %s,
                        gst_no = %s,
                        nabl_no = %s,
                        address = %s,
                        city = %s,
                        state = %s,
                        pincode = %s,
                        mobile = %s,
                        alt_mobile = %s,
                        email = %s,
                        website = %s,
                        receipt_prefix = %s,
                        patient_prefix = %s,
                        upi_id = %s,
                        logo = COALESCE(%s, logo),
                        signature = COALESCE(%s, signature),
                        stamp = COALESCE(%s, stamp),
                        report_header = COALESCE(%s, report_header),
                        report_footer = COALESCE(%s, report_footer)
                    WHERE lab_id = %s
                    """,
                    data + (
                        logo_name,
                        signature_name,
                        stamp_name,
                        report_header_name,
                        report_footer_name,
                        lab_id,
                    )
                )

            else:
                cursor.execute(
                    """
                    INSERT INTO lab_settings (
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
                        upi_id,
                        logo,
                        signature,
                        stamp,
                        report_header,
                        report_footer
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        lab_id,
                    ) + data + (
                        logo_name,
                        signature_name,
                        stamp_name,
                        report_header_name,
                        report_footer_name,
                    )
                )

            # --------------------------------------------------
            # 8. Save report signatory when submitted
            # --------------------------------------------------
            signatory_name = request.form.get(
                "signatory_name", ""
            ).strip()

            signatory_designation = request.form.get(
                "signatory_designation", ""
            ).strip()

            if (
                signatory_name
                and signatory_designation
                and signatory_signature
                and signatory_signature.filename
            ):
                if not upload_dirs["signatory"]:
                    raise RuntimeError(
                        "UPLOAD_SIGNATORY is not configured."
                    )

                sign_filename = save_upload(
                    signatory_signature,
                    upload_dirs["signatory"],
                    "signatory",
                )

                cursor.execute(
                    """
                    INSERT INTO report_signatories (
                        lab_id,
                        name,
                        designation,
                        signature,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        laboratory_id,
                        signatory_name,
                        signatory_designation,
                        sign_filename,
                        "Active",
                    )
                )

            # --------------------------------------------------
            # 9. Commit changes
            # --------------------------------------------------
            db.commit()

            flash("Settings saved successfully.", "success")
            return redirect(url_for("settings"))

        # --------------------------------------------------
        # 10. Load settings for GET request
        # --------------------------------------------------
        cursor.execute(
            """
            SELECT *
            FROM lab_settings
            WHERE lab_id = %s
            LIMIT 1
            """,
            (lab_id,)
        )
        settings_data = cursor.fetchone()

        # --------------------------------------------------
        # 11. Load laboratory users
        # --------------------------------------------------
        cursor.execute(
            """
            SELECT username, role, status
            FROM users
            WHERE lab_id = %s
            ORDER BY role
            """,
            (lab_id,)
        )
        users = cursor.fetchall()

        # --------------------------------------------------
        # 12. Load report signatories
        # --------------------------------------------------
        cursor.execute(
            """
            SELECT *
            FROM report_signatories
            WHERE lab_id = %s
            ORDER BY name
            """,
            (laboratory_id,)
        )
        signatories = cursor.fetchall()

        # --------------------------------------------------
        # 13. Render page
        # --------------------------------------------------
        return render_template(
            "settings.html",
            settings=settings_data,
            users=users,
            signatories=signatories,
        )

    except Exception:
        if db:
            try:
                db.rollback()
            except Exception:
                app.logger.exception(
                    "Rollback failed in settings route."
                )

        app.logger.exception("Error in /settings route.")
        flash(
            "Unable to process settings. Please check the application logs.",
            "danger",
        )

        return redirect(url_for("dashboard"))

    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                app.logger.exception(
                    "Failed to close settings cursor."
                )

        if db:
            try:
                db.close()
            except Exception:
                app.logger.exception(
                    "Failed to close settings database connection."
                )


@app.context_processor
def inject_lab_settings():
    """Inject lab settings instantly from session cache, avoiding database overhead."""
    if "lab_id" not in session:
        return dict(lab_settings=None)
        
    # Read directly from session cache
    settings = session.get("lab_settings")
    return dict(lab_settings=settings)

@app.route("/update-user-access", methods=["POST"])
@login_required
@role_required("Admin")
def update_user_access():

    db = get_db()
    cursor = db.cursor()

    try:

        username = request.form["username"].strip().lower()
        password = request.form["password"]
        role = request.form["role"]
        status = request.form["status"]

        if password:

            hashed = bcrypt.generate_password_hash(password).decode("utf-8")

            cursor.execute("""
                UPDATE users
                SET
                    username=%s,
                    password=%s,
                    status=%s
                WHERE
                    lab_id=%s
                    AND role=%s
            """, (
                username,
                hashed,
                status,
                session["lab_id"],
                role
            ))

        else:

            cursor.execute("""
                UPDATE users
                SET
                    username=%s,
                    status=%s
                WHERE
                    lab_id=%s
                    AND role=%s
            """, (
                username,
                status,
                session["lab_id"],
                role
            ))

        db.commit()

        flash(f"{role} account updated successfully.", "success")

    except Exception as e:

        db.rollback()
        flash(str(e), "danger")

    finally:

        cursor.close()
        db.close()

    return redirect(url_for("settings"))
@app.route("/delete-patient/<patient_id>", methods=["POST"])
@login_required
@role_required("Developer", "Admin")
def delete_patient(patient_id):

    db = get_db()
    cursor = db.cursor()

    lab_id = session["lab_id"]
    print("Delete route called")
    print(patient_id)
    print(lab_id)

    try:
        db.start_transaction()

        # Patient Exists?
        cursor.execute("""
            SELECT patient_id
            FROM patients
            WHERE patient_id=%s
            AND lab_id=%s
        """, (patient_id, lab_id))

        if cursor.fetchone() is None:
            flash("Patient not found.", "danger")
            return redirect(url_for("patient_search"))

        # -------------------------
        # Delete Child Records
        # -------------------------

       

        cursor.execute("""
            DELETE FROM test_results
            WHERE patient_id=%s
            AND lab_id=%s
        """, (patient_id, lab_id))
        print("Deleted test_results")

        cursor.execute("""
            DELETE FROM reports
            WHERE patient_id=%s
            AND lab_id=%s
        """, (patient_id, lab_id))
        print("Deleted report")

        cursor.execute("""
            DELETE FROM patient_tests
            WHERE patient_id=%s
            AND lab_id=%s
        """, (patient_id, lab_id))
        print("Deleted Patient_test")

        cursor.execute("""
            DELETE FROM payment_transactions
            WHERE patient_id=%s
            AND lab_id=%s
        """, (patient_id, lab_id))
        print("Deleted payment_transation")

        cursor.execute("""
            DELETE FROM pending_payments
            WHERE patient_id=%s
            AND lab_id=%s
        """, (patient_id, lab_id))
        print("Deleted pending_payment")

        cursor.execute("""
            DELETE FROM payments
            WHERE patient_id=%s
            AND lab_id=%s
        """, (patient_id, lab_id))
        print("Deleted payments")


        # -------------------------
        # Delete Patient
        # -------------------------

        cursor.execute("""
            DELETE FROM patients
            WHERE patient_id=%s
            AND lab_id=%s
        """, (patient_id, lab_id))
        print("Deleted patients")

        db.commit()

        flash("Patient deleted successfully.", "success")

    except Exception as e:
     db.rollback()

     print("="*60)
     print("DELETE ERROR")
     print(e)

     import traceback
     traceback.print_exc()
     print("="*60)

     flash(str(e), "danger")

    finally:

        cursor.close()
        db.close()

    return redirect(url_for("patient_search"))

@app.route("/user-management")
@login_required
@role_required("Developer", "Admin")
def user_management():

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:

        cursor.execute("""
            SELECT
                id,
                username,
                role,
                status
            FROM users
            WHERE lab_id=%s
            ORDER BY
                FIELD(role,'Admin','Technician','Receptionist','Developer'),
                username
        """, (session["lab_id"],))

        users = cursor.fetchall()

        return render_template(
            "user_management.html",
            users=users
        )

    finally:
        cursor.close()
        db.close()
@app.route("/add-user", methods=["POST"])
@login_required
@role_required("Admin", "Developer")
def add_user():

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:

        # ----------------------------
        # Get Form Data
        # ----------------------------

        username = request.form["username"].strip().lower()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        role = request.form["role"]
        status = request.form["status"]

        lab_id = session["lab_id"]

        # ----------------------------
        # Validation
        # ----------------------------

        if not username:
            flash("Username is required.", "danger")
            return redirect(url_for("user_management"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("user_management"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("user_management"))

        # ----------------------------
        # Check Duplicate Username
        # Same username allowed in
        # another laboratory
        # ----------------------------

        cursor.execute("""
            SELECT id
            FROM users
            WHERE lab_id=%s
            AND username=%s
        """, (lab_id, username))

        existing = cursor.fetchone()

        if existing:
            flash("Username already exists.", "warning")
            return redirect(url_for("user_management"))

        # ----------------------------
        # Hash Password
        # ----------------------------

        hashed_password = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

        # ----------------------------
        # Insert User
        # ----------------------------

        cursor.execute("""
            INSERT INTO users
            (
                lab_id,
                username,
                password,
                role,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, (
            lab_id,
            username,
            hashed_password,
            role,
            status
        ))

        db.commit()

        flash("User created successfully.", "success")

        return redirect(url_for("user_management"))

    except Exception as e:

        db.rollback()

        print(e)

        flash("Something went wrong.", "danger")

        return redirect(url_for("user_management"))

    finally:

        cursor.close()
        db.close()
@app.route("/edit-user/<int:user_id>", methods=["POST"])
@login_required
@role_required("Admin", "Developer")
def edit_user(user_id):

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:

        # --------------------------------
        # Get Form Data
        # --------------------------------

        username = request.form["username"].strip().lower()
        role = request.form["role"]
        status = request.form["status"]

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        lab_id = session["lab_id"]

        # --------------------------------
        # Check User Exists
        # --------------------------------

        cursor.execute("""
            SELECT *
            FROM users
            WHERE id=%s
            AND lab_id=%s
        """, (user_id, lab_id))

        user = cursor.fetchone()

        if not user:
            flash("User not found.", "danger")
            return redirect(url_for("user_management"))

        # --------------------------------
        # Check Duplicate Username
        # --------------------------------

        cursor.execute("""
            SELECT id
            FROM users
            WHERE lab_id=%s
            AND username=%s
            AND id<>%s
        """, (
            lab_id,
            username,
            user_id
        ))

        duplicate = cursor.fetchone()

        if duplicate:
            flash("Username already exists.", "warning")
            return redirect(url_for("user_management"))

        # --------------------------------
        # Password Validation
        # --------------------------------

        if password:

            if password != confirm_password:

                flash("Passwords do not match.", "danger")
                return redirect(url_for("user_management"))

            if len(password) < 6:

                flash("Password must be at least 6 characters.", "danger")
                return redirect(url_for("user_management"))

            hashed_password = bcrypt.generate_password_hash(
                password
            ).decode("utf-8")

            cursor.execute("""
                UPDATE users
                SET
                    username=%s,
                    password=%s,
                    role=%s,
                    status=%s
                WHERE id=%s
            """, (
                username,
                hashed_password,
                role,
                status,
                user_id
            ))

        else:

            cursor.execute("""
                UPDATE users
                SET
                    username=%s,
                    role=%s,
                    status=%s
                WHERE id=%s
            """, (
                username,
                role,
                status,
                user_id
            ))

        db.commit()

        flash("User updated successfully.", "success")

        return redirect(url_for("user_management"))

    except Exception as e:

        db.rollback()

        print(e)

        flash("Something went wrong.", "danger")

        return redirect(url_for("user_management"))

    finally:

        cursor.close()
        db.close()
@app.route("/delete-user/<int:user_id>", methods=["POST"])
@login_required
@role_required("Admin", "Developer")
def delete_user(user_id):

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:

        lab_id = session["lab_id"]

        # ------------------------------------
        # Check User Exists
        # ------------------------------------

        cursor.execute("""
            SELECT *
            FROM users
            WHERE id=%s
            AND lab_id=%s
        """, (user_id, lab_id))

        user = cursor.fetchone()

        if not user:
            flash("User not found.", "danger")
            return redirect(url_for("user_management"))

        # ------------------------------------
        # Don't allow deleting yourself
        # ------------------------------------

        if user["id"] == session["user_id"]:
            flash("You cannot delete your own account.", "danger")
            return redirect(url_for("user_management"))

        # ------------------------------------
        # Don't allow deleting the last Admin
        # ------------------------------------

        if user["role"] == "Admin":

            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM users
                WHERE lab_id=%s
                AND role='Admin'
            """, (lab_id,))

            admin_count = cursor.fetchone()["total"]

            if admin_count <= 1:
                flash("Cannot delete the last Admin account.", "danger")
                return redirect(url_for("user_management"))

        # ------------------------------------
        # Delete User
        # ------------------------------------

        cursor.execute("""
            DELETE FROM users
            WHERE id=%s
            AND lab_id=%s
        """, (user_id, lab_id))

        db.commit()

        flash("User deleted successfully.", "success")

    except Exception as e:

        db.rollback()

        print("DELETE USER ERROR:", e)

        flash("Something went wrong.", "danger")

    finally:

        cursor.close()
        db.close()

    return redirect(url_for("user_management"))
@app.route("/delete-signatory/<int:id>")
@login_required
@role_required("Developer", "Admin")
def delete_signatory(id):

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    # Get image filename
    cursor.execute("""
        SELECT signature
        FROM report_signatories
        WHERE id=%s
        AND lab_id=%s
    """, (id, session["lab_id"]))

    sign = cursor.fetchone()

    if sign:

        image_path = os.path.join(
            app.config["UPLOAD_SIGNATORY"],
            sign["signature"]
        )

        if os.path.exists(image_path):
            os.remove(image_path)

        cursor.execute("""
            DELETE
            FROM report_signatories
            WHERE id=%s
            AND lab_id=%s
        """, (id, session["lab_id"]))

        db.commit()

    cursor.close()
    db.close()

    flash("Signatory deleted successfully.", "success")

    return redirect(url_for("settings"))
@app.route("/edit-signatory/<int:id>", methods=["POST"])
@login_required
@role_required("Developer", "Admin")
def edit_signatory(id):

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT *
        FROM report_signatories
        WHERE id=%s
        AND lab_id=%s
    """, (id, session["lab_id"]))

    sign = cursor.fetchone()

    if not sign:

        flash("Signatory not found.", "danger")
        return redirect(url_for("settings"))

    filename = sign["signature"]

    file = request.files.get("signature")

    if file and file.filename:

        if sign["signature"]:

            old = os.path.join(
                app.config["UPLOAD_SIGNATORY"],
                sign["signature"]
            )

            if os.path.exists(old):
                os.remove(old)

        import uuid

        filename = (
            f"{uuid.uuid4().hex}_"
            f"{secure_filename(file.filename)}"
        )

        file.save(
            os.path.join(
                app.config["UPLOAD_SIGNATORY"],
                filename
            )
        )

    cursor.execute("""
        UPDATE report_signatories
        SET

        name=%s,
        designation=%s,
        signature=%s

        WHERE id=%s
        AND lab_id=%s
    """,
    (
        request.form["name"],
        request.form["designation"],
        filename,
        id,
        session["lab_id"]
    ))

    db.commit()

    cursor.close()
    db.close()

    flash("Signatory updated successfully.", "success")

    return redirect(url_for("settings"))
@app.route('/edit-parameter/<int:parameter_id>', methods=['GET', 'POST'])
@login_required
@role_required('Developer', 'Admin')
def edit_parameter(parameter_id):

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT *
        FROM test_parameters
        WHERE id=%s
        AND lab_id=%s
    """, (parameter_id, session["lab_id"]))

    parameter = cursor.fetchone()

    if not parameter:
        flash("Parameter not found.", "danger")
        return redirect(request.referrer)

    if request.method == "POST":

        cursor.execute("""
            UPDATE test_parameters
            SET
                parameter_name=%s,
                unit=%s,
                reference_type=%s,
                display_order=%s
            WHERE id=%s
            AND lab_id=%s
        """, (
            request.form["parameter_name"],
            request.form["unit"],
            request.form["reference_type"],
            request.form["display_order"],
            parameter_id,
            session["lab_id"]
        ))

        db.commit()

        flash("Parameter updated successfully.", "success")

        return redirect(url_for(
            "parameter_builder",
            component_id=parameter["component_id"]
        ))

    return render_template(
        "edit_parameter.html",
        parameter=parameter
    )
@app.route('/delete-parameter/<int:parameter_id>', methods=['POST'])
@login_required
@role_required('Developer', 'Admin')
def delete_parameter(parameter_id):

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT component_id
        FROM parameter_definition
        WHERE id=%s
    """, (parameter_id,))

    parameter = cursor.fetchone()

    if not parameter:
        flash("Parameter not found.", "danger")
        return redirect(request.referrer)

    cursor.execute("""
        DELETE FROM parameter_definition
        WHERE id=%s
    """, (parameter_id,))

    db.commit()

    flash("Parameter deleted successfully.", "success")

    return redirect(url_for(
        "test_builder.parameter_list",
        component_id=parameter["component_id"]
    ))
# ============================================================
# SUPER ADMIN DASHBOARD
# ============================================================

@app.route("/super-admin")
@login_required
@role_required("Developer")
def super_admin_dashboard():

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:
        # ----------------------------------------------------
        # 1. Total Laboratories
        # ----------------------------------------------------
        cursor.execute("""
            SELECT COUNT(*) AS total_labs
            FROM laboratories
        """)
        total_labs = cursor.fetchone()["total_labs"]

        # ----------------------------------------------------
        # 2. Active Laboratories
        # ----------------------------------------------------
        cursor.execute("""
            SELECT COUNT(*) AS active_labs
            FROM laboratories
            WHERE status = 'Active'
        """)
        active_labs = cursor.fetchone()["active_labs"]

        # ----------------------------------------------------
        # 3. Active Subscriptions
        # ----------------------------------------------------
        # ----------------------------------------------------
# 3. Active Subscriptions
# ----------------------------------------------------

        cursor.execute("""
    SELECT COUNT(*) AS active_subscriptions
    FROM lab_subscriptions
    WHERE status = 'Active'
      AND start_date <= CURDATE()
      AND end_date >= CURDATE()
""")

        active_subscriptions = cursor.fetchone()["active_subscriptions"]

        # ----------------------------------------------------
        # 4. Expired Subscriptions
        # ----------------------------------------------------
        cursor.execute("""
    SELECT COUNT(*) AS expired_subscriptions
    FROM lab_subscriptions
    WHERE end_date < CURDATE()
      AND status IN ('Active', 'Expired')
""")

        expired_subscriptions = cursor.fetchone()["expired_subscriptions"] 

        # ----------------------------------------------------
        # 5. Subscriptions Expiring Within 7 Days
        # ----------------------------------------------------
        cursor.execute("""
    SELECT COUNT(*) AS expiring_soon
    FROM lab_subscriptions
    WHERE status = 'Active'
      AND start_date <= CURDATE()
      AND end_date >= CURDATE()
      AND end_date <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
""")

        expiring_soon = cursor.fetchone()["expiring_soon"] 

        # ----------------------------------------------------
        # 6. Recent Laboratories
        # ----------------------------------------------------
        cursor.execute("""
            SELECT
                l.lab_id,
                l.lab_name,
                l.owner_name,
                l.status,
                l.created_at
            FROM laboratories l
            ORDER BY l.id DESC
            LIMIT 10
        """)
        recent_labs = cursor.fetchall()

        # ----------------------------------------------------
        # 7. Recent Subscription Assignments
        # ----------------------------------------------------
        cursor.execute("""
            SELECT
                ls.id,
                ls.lab_id,
                l.lab_name,
                sp.plan_name,
                ls.start_date,
                ls.end_date,
                ls.status
            FROM lab_subscriptions ls
            JOIN laboratories l
                ON l.lab_id = ls.lab_id
            JOIN subscription_plans sp
                ON sp.id = ls.plan_id
            ORDER BY ls.id DESC
            LIMIT 10
        """)
        recent_subscriptions = cursor.fetchall()

        current_time = datetime.now().strftime(
            "%d %B %Y | %I:%M %p"
        )

        return render_template(
            "super_admin_dashboard.html",
            total_labs=total_labs,
            active_labs=active_labs,
            active_subscriptions=active_subscriptions,
            expired_subscriptions=expired_subscriptions,
            expiring_soon=expiring_soon,
            recent_labs=recent_labs,
            recent_subscriptions=recent_subscriptions,
            current_time=current_time,
            lab_settings=None
        )

    finally:
        cursor.close()
        db.close()
@app.route("/super-admin/laboratories")
@login_required
@role_required("Developer")
def super_admin_labs():

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:
        search = request.args.get("search", "").strip()
        status_filter = request.args.get("status", "").strip()

        query = """
            SELECT
                l.id,
                l.lab_id,
                l.lab_name,
                l.owner_name,
                l.status,
                l.created_at,

                sp.plan_name,
                ls.start_date AS subscription_start,
                ls.end_date AS subscription_end,
                ls.status AS subscription_status

            FROM laboratories l

            LEFT JOIN lab_subscriptions ls
                ON ls.id = (
                    SELECT ls2.id
                    FROM lab_subscriptions ls2
                    WHERE ls2.lab_id = l.lab_id
                    ORDER BY ls2.id DESC
                    LIMIT 1
                )

            LEFT JOIN subscription_plans sp
                ON sp.id = ls.plan_id

            WHERE 1 = 1
        """

        params = []

        # Search by Lab ID, Lab Name, or Owner Name
        if search:
            query += """
                AND (
                    l.lab_id LIKE %s
                    OR l.lab_name LIKE %s
                    OR l.owner_name LIKE %s
                )
            """

            search_value = f"%{search}%"

            params.extend([
                search_value,
                search_value,
                search_value
            ])

        # Filter by laboratory status
        if status_filter:
            query += " AND l.status = %s"
            params.append(status_filter)

        query += " ORDER BY l.id DESC"

        cursor.execute(query, tuple(params))
        laboratories = cursor.fetchall()

        # Get available laboratory statuses for the filter
        cursor.execute("""
            SELECT DISTINCT status
            FROM laboratories
            WHERE status IS NOT NULL
            ORDER BY status
        """)

        statuses = [
            row["status"]
            for row in cursor.fetchall()
        ]

        return render_template(
            "super_admin_labs.html",
            laboratories=laboratories,
            search=search,
            status_filter=status_filter,
            statuses=statuses
        )

    except Exception as e:
        app.logger.exception(
            "Error loading Super Admin laboratory management"
        )

        return (
            "Unable to load laboratory management. "
            "Check the application logs for details.",
            500
        )

    finally:
        cursor.close()
        db.close()
@app.route("/super-admin/subscriptions/assign", methods=["GET", "POST"])
@login_required
@role_required("Developer")
def super_admin_assign_subscription():

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:
        # Fetch all laboratories
        cursor.execute("""
            SELECT lab_id, lab_name, owner_name, status
            FROM laboratories
            ORDER BY id DESC
        """)
        laboratories = cursor.fetchall()

        # Fetch active subscription plans
        cursor.execute("""
    SELECT
        id,
        plan_name,
        monthly_price,
        annual_price,
        max_users,
        max_patients_per_month,
        analyzer_integration
    FROM subscription_plans
    WHERE status = 'Active'
    ORDER BY monthly_price ASC
""")

        plans = cursor.fetchall()

        if request.method == "POST":

            lab_id = request.form.get("lab_id", "").strip()
            plan_id = request.form.get("plan_id", "").strip()
            start_date = request.form.get("start_date", "").strip()
            end_date = request.form.get("end_date", "").strip()

            # Validate required fields
            if not all([lab_id, plan_id, start_date, end_date]):
                flash("Please fill in all required fields.", "error")

                return render_template(
                    "super_admin_assign_subscription.html",
                    laboratories=laboratories,
                    plans=plans
                )

            # Validate dates
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid date format.", "error")

                return render_template(
                    "super_admin_assign_subscription.html",
                    laboratories=laboratories,
                    plans=plans
                )

            if end < start:
                flash(
                    "End date must be on or after the start date.",
                    "error"
                )

                return render_template(
                    "super_admin_assign_subscription.html",
                    laboratories=laboratories,
                    plans=plans
                )

            # Verify laboratory exists
            cursor.execute("""
                SELECT lab_id
                FROM laboratories
                WHERE lab_id = %s
            """, (lab_id,))

            if not cursor.fetchone():
                flash("Selected laboratory was not found.", "error")

                return render_template(
                    "super_admin_assign_subscription.html",
                    laboratories=laboratories,
                    plans=plans
                )

            # Verify selected plan is active
            cursor.execute("""
                SELECT id
                FROM subscription_plans
                WHERE id = %s
                  AND status = 'Active'
            """, (plan_id,))

            if not cursor.fetchone():
                flash("Selected subscription plan is unavailable.", "error")

                return render_template(
                    "super_admin_assign_subscription.html",
                    laboratories=laboratories,
                    plans=plans
                )

            # Insert new subscription record
            cursor.execute("""
                INSERT INTO lab_subscriptions
                    (lab_id, plan_id, start_date, end_date, status)
                VALUES
                    (%s, %s, %s, %s, %s)
            """, (
                lab_id,
                int(plan_id),
                start_date,
                end_date,
                "Active"
            ))

            db.commit()

            flash(
                "Subscription assigned successfully.",
                "success"
            )

            return redirect(url_for("super_admin_assign_subscription"))

        return render_template(
            "super_admin_assign_subscription.html",
            laboratories=laboratories,
            plans=plans
        )

    except Exception:
        db.rollback()

        app.logger.exception(
            "Error assigning laboratory subscription"
        )

        return (
            "Subscription operation failed. "
            "Check the Flask terminal for the actual error.",
            500
        )

    finally:
        cursor.close()
        db.close()
@app.route("/super-admin/plans")
@login_required
@role_required("Developer")
def super_admin_plans():

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:
        search = request.args.get("search", "").strip()
        status_filter = request.args.get("status", "").strip()

        query = """
            SELECT
                sp.id,
                sp.plan_name,
                sp.description,
                sp.monthly_price,
                sp.annual_price,
                sp.max_users,
                sp.max_patients_per_month,
                sp.analyzer_integration,
                sp.status,
                sp.created_at,
                COUNT(DISTINCT ls.lab_id) AS assigned_labs
            FROM subscription_plans sp

            LEFT JOIN lab_subscriptions ls
                ON ls.plan_id = sp.id

            WHERE 1 = 1
        """

        params = []

        # Search by plan name or description
        if search:
            query += """
                AND (
                    sp.plan_name LIKE %s
                    OR sp.description LIKE %s
                )
            """

            search_value = f"%{search}%"

            params.extend([
                search_value,
                search_value
            ])

        # Filter by plan status
        if status_filter:
            query += " AND sp.status = %s"
            params.append(status_filter)

        query += """
            GROUP BY
                sp.id,
                sp.plan_name,
                sp.description,
                sp.monthly_price,
                sp.annual_price,
                sp.max_users,
                sp.max_patients_per_month,
                sp.analyzer_integration,
                sp.status,
                sp.created_at
            ORDER BY sp.id DESC
        """

        cursor.execute(query, tuple(params))
        plans = cursor.fetchall()

        # Summary statistics
        cursor.execute("""
            SELECT
                COUNT(*) AS total_plans,
                COALESCE(
                    SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END),
                    0
                ) AS active_plans,
                COALESCE(
                    SUM(CASE WHEN status = 'Inactive' THEN 1 ELSE 0 END),
                    0
                ) AS inactive_plans
            FROM subscription_plans
        """)

        statistics = cursor.fetchone()

        return render_template(
            "super_admin_plans.html",
            plans=plans,
            statistics=statistics,
            search=search,
            status_filter=status_filter
        )

    except Exception:
        app.logger.exception(
            "Error loading subscription plan management"
        )

        return (
            "Unable to load subscription plans. "
            "Check the Flask terminal for the actual error.",
            500
        )

    finally:
        cursor.close()
        db.close()
@app.route("/super-admin/plans/create", methods=["GET", "POST"])
@login_required
@role_required("Developer")
def super_admin_create_plan():

    if request.method == "POST":

        plan_name = request.form.get("plan_name", "").strip()
        description = request.form.get("description", "").strip()
        monthly_price = request.form.get("monthly_price", "").strip()
        annual_price = request.form.get("annual_price", "").strip()
        max_users = request.form.get("max_users", "").strip()
        max_patients_per_month = request.form.get(
            "max_patients_per_month", ""
        ).strip()
        analyzer_integration = (
            1 if request.form.get("analyzer_integration") == "on" else 0
        )
        status = request.form.get("status", "Active").strip()

        # Validate required fields
        if not plan_name:
            flash("Plan name is required.", "danger")
            return render_template("super_admin_create_plan.html")

        # Validate status
        if status not in ("Active", "Inactive"):
            flash("Invalid plan status.", "danger")
            return render_template("super_admin_create_plan.html")

        # Validate prices
        try:
            monthly_price = float(monthly_price)
            annual_price = float(annual_price)

            if (
                not math.isfinite(monthly_price)
                or not math.isfinite(annual_price)
                or monthly_price < 0
                or annual_price < 0
            ):
                raise ValueError

        except (ValueError, TypeError):
            flash("Enter valid non-negative monthly and annual prices.", "danger")
            return render_template("super_admin_create_plan.html")

        # Validate optional limits
        try:
            max_users = int(max_users) if max_users else None
            max_patients_per_month = (
                int(max_patients_per_month)
                if max_patients_per_month
                else None
            )

            if (
                (max_users is not None and max_users < 1)
                or (
                    max_patients_per_month is not None
                    and max_patients_per_month < 1
                )
            ):
                raise ValueError

        except (ValueError, TypeError):
            flash(
                "Limits must be positive whole numbers or left blank for unlimited.",
                "danger"
            )
            return render_template("super_admin_create_plan.html")

        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)

        try:
            # Prevent duplicate plan names
            cursor.execute(
                """
                SELECT id
                FROM subscription_plans
                WHERE LOWER(plan_name) = LOWER(%s)
                LIMIT 1
                """,
                (plan_name,)
            )

            if cursor.fetchone():
                flash("A plan with this name already exists.", "danger")
                return render_template("super_admin_create_plan.html")

            cursor.execute(
                """
                INSERT INTO subscription_plans (
                    plan_name,
                    description,
                    monthly_price,
                    annual_price,
                    max_users,
                    max_patients_per_month,
                    analyzer_integration,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    plan_name,
                    description,
                    monthly_price,
                    annual_price,
                    max_users,
                    max_patients_per_month,
                    analyzer_integration,
                    status
                )
            )

            db.commit()

            flash("Subscription plan created successfully.", "success")
            return redirect(url_for("super_admin_plans"))

        except Exception:
            db.rollback()
            app.logger.exception("Error creating subscription plan")
            flash("Unable to create the plan. Check the application logs.", "danger")

        finally:
            cursor.close()
            db.close()

    return render_template("super_admin_create_plan.html")
@app.route("/super-admin/plans/edit/<int:plan_id>", methods=["GET", "POST"])
@login_required
@role_required("Developer")
def super_admin_edit_plan(plan_id):

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:
        # Fetch existing plan
        cursor.execute("""
            SELECT
                id,
                plan_name,
                description,
                monthly_price,
                annual_price,
                max_users,
                max_patients_per_month,
                analyzer_integration,
                status
            FROM subscription_plans
            WHERE id = %s
        """, (plan_id,))

        plan = cursor.fetchone()

        if not plan:
            flash("Subscription plan not found.", "danger")
            return redirect(url_for("super_admin_plans"))

        if request.method == "POST":

            plan_name = request.form.get("plan_name", "").strip()
            description = request.form.get("description", "").strip()
            monthly_price_raw = request.form.get("monthly_price", "").strip()
            annual_price_raw = request.form.get("annual_price", "").strip()
            max_users_raw = request.form.get("max_users", "").strip()
            max_patients_raw = request.form.get(
                "max_patients_per_month", ""
            ).strip()

            analyzer_integration = (
                1 if request.form.get("analyzer_integration") == "on" else 0
            )

            status = request.form.get("status", "").strip()

            # Validate required fields
            if not plan_name:
                flash("Plan name is required.", "danger")
                return render_template(
                    "super_admin_edit_plan.html", plan=plan
                )

            if status not in ("Active", "Inactive"):
                flash("Invalid plan status.", "danger")
                return render_template(
                    "super_admin_edit_plan.html", plan=plan
                )

            # Validate prices
            try:
                monthly_price = float(monthly_price_raw)
                annual_price = float(annual_price_raw)

                if (
                    not math.isfinite(monthly_price)
                    or not math.isfinite(annual_price)
                    or monthly_price < 0
                    or annual_price < 0
                ):
                    raise ValueError

            except (ValueError, TypeError):
                flash(
                    "Enter valid non-negative monthly and annual prices.",
                    "danger"
                )
                return render_template(
                    "super_admin_edit_plan.html", plan=plan
                )

            # Validate optional limits
            try:
                max_users = int(max_users_raw) if max_users_raw else None
                max_patients = (
                    int(max_patients_raw) if max_patients_raw else None
                )

                if (
                    (max_users is not None and max_users < 1)
                    or (max_patients is not None and max_patients < 1)
                ):
                    raise ValueError

            except (ValueError, TypeError):
                flash(
                    "Limits must be positive whole numbers or left blank.",
                    "danger"
                )
                return render_template(
                    "super_admin_edit_plan.html", plan=plan
                )

            # Prevent duplicate names, excluding this plan
            cursor.execute("""
                SELECT id
                FROM subscription_plans
                WHERE LOWER(plan_name) = LOWER(%s)
                  AND id != %s
                LIMIT 1
            """, (plan_name, plan_id))

            if cursor.fetchone():
                flash("Another plan already uses this name.", "danger")
                return render_template(
                    "super_admin_edit_plan.html", plan=plan
                )

            # Update plan
            cursor.execute("""
                UPDATE subscription_plans
                SET
                    plan_name = %s,
                    description = %s,
                    monthly_price = %s,
                    annual_price = %s,
                    max_users = %s,
                    max_patients_per_month = %s,
                    analyzer_integration = %s,
                    status = %s
                WHERE id = %s
            """, (
                plan_name,
                description,
                monthly_price,
                annual_price,
                max_users,
                max_patients,
                analyzer_integration,
                status,
                plan_id
            ))

            db.commit()

            flash("Subscription plan updated successfully.", "success")
            return redirect(url_for("super_admin_plans"))

        return render_template(
            "super_admin_edit_plan.html",
            plan=plan
        )

    except Exception:
        db.rollback()
        app.logger.exception("Error editing subscription plan")
        return (
            "Unable to edit the subscription plan. Check the Flask logs.",
            500
        )

    finally:
        cursor.close()
        db.close()
@app.route("/super-admin/subscription-history")
@login_required
@role_required("Developer")
def super_admin_subscription_history():

    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:
        search = request.args.get("search", "").strip()
        status_filter = request.args.get("status", "").strip()

        query = """
            SELECT
                ls.id AS subscription_id,
                ls.lab_id,
                l.lab_name,
                l.owner_name,
                sp.plan_name,
                sp.monthly_price,
                sp.annual_price,
                ls.start_date,
                ls.end_date,
                ls.status AS subscription_status
            FROM lab_subscriptions ls
            LEFT JOIN laboratories l
                ON l.lab_id = ls.lab_id
            LEFT JOIN subscription_plans sp
                ON sp.id = ls.plan_id
            WHERE 1 = 1
        """

        params = []

        if search:
            query += """
                AND (
                    ls.lab_id LIKE %s
                    OR l.lab_name LIKE %s
                    OR l.owner_name LIKE %s
                    OR sp.plan_name LIKE %s
                )
            """

            search_value = f"%{search}%"
            params.extend([
                search_value,
                search_value,
                search_value,
                search_value
            ])

        if status_filter:
            query += " AND ls.status = %s"
            params.append(status_filter)

        query += " ORDER BY ls.id DESC"

        cursor.execute(query, tuple(params))
        subscriptions = cursor.fetchall()

        # Available subscription statuses for the filter
        cursor.execute("""
            SELECT DISTINCT status
            FROM lab_subscriptions
            WHERE status IS NOT NULL
            ORDER BY status
        """)

        statuses = [
            row["status"]
            for row in cursor.fetchall()
        ]

        # Summary statistics
        cursor.execute("""
            SELECT
                COUNT(*) AS total_subscriptions,
                COALESCE(
                    SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END),
                    0
                ) AS active_subscriptions,
                COALESCE(
                    SUM(CASE WHEN status = 'Expired' THEN 1 ELSE 0 END),
                    0
                ) AS expired_subscriptions,
                COALESCE(
                    SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END),
                    0
                ) AS cancelled_subscriptions
            FROM lab_subscriptions
        """)

        statistics = cursor.fetchone()

        return render_template(
            "super_admin_subscription_history.html",
            subscriptions=subscriptions,
            statuses=statuses,
            status_filter=status_filter,
            search=search,
            statistics=statistics
        )

    except Exception:
        app.logger.exception(
            "Error loading Super Admin subscription history"
        )

        return (
            "Unable to load subscription history. "
            "Check the Flask terminal for details.",
            500
        )

    finally:
        cursor.close()
        db.close()
@app.route("/super-admin/broadcasts", methods=["GET", "POST"])
@login_required
@role_required("Developer")
def super_admin_broadcasts():
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    try:
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            message = request.form.get("message", "").strip()
            target_type = request.form.get("target_type", "All").strip()

            if not title or not message:
                flash("Title and message are required.", "danger")

            elif target_type not in ("All", "Active"):
                flash("Invalid announcement target.", "danger")

            else:
                # Start transaction
                db.start_transaction()

                # 1. Save announcement
                cursor.execute("""
                    INSERT INTO announcements (
                        title,
                        message,
                        target_type,
                        created_by,
                        status
                    )
                    VALUES (%s, %s, %s, %s, 'Published')
                """, (
                    title,
                    message,
                    target_type,
                    session["user_id"]
                ))

                announcement_id = cursor.lastrowid

                # 2. Select recipient laboratories
                if target_type == "Active":
                    cursor.execute("""
                        SELECT lab_id
                        FROM laboratories
                        WHERE status = 'Active'
                    """)
                else:
                    cursor.execute("""
                        SELECT lab_id
                        FROM laboratories
                    """)

                laboratories = cursor.fetchall()

                # 3. Create one recipient record per laboratory
                if laboratories:
                    recipient_values = [
                        (announcement_id, lab["lab_id"])
                        for lab in laboratories
                    ]

                    cursor.executemany("""
                        INSERT INTO announcement_recipients (
                            announcement_id,
                            lab_id,
                            is_read
                        )
                        VALUES (%s, %s, 0)
                    """, recipient_values)

                # 4. Commit announcement and recipients together
                db.commit()

                flash(
                    f"Announcement published successfully to "
                    f"{len(laboratories)} laboratory/laboratories.",
                    "success"
                )

                return redirect(url_for("super_admin_broadcasts"))

        # Announcement history
        cursor.execute("""
            SELECT
                id,
                title,
                message,
                target_type,
                created_at,
                status
            FROM announcements
            ORDER BY id DESC
        """)

        announcements = cursor.fetchall()

        return render_template(
            "super_admin_broadcasts.html",
            announcements=announcements
        )

    except Exception:
        db.rollback()
        app.logger.exception("Error managing announcements")

        return (
            "Unable to manage announcements. Check the Flask logs.",
            500
        )

    finally:
        cursor.close()
        db.close()



if __name__ == "__main__":
    # Debug mode must never be enabled by default. Use a local-only
    # development override when needed; production should run via Gunicorn.
    debug_enabled = os.getenv("FLASK_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=debug_enabled
    )
    