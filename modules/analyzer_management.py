"""Analyzer Management blueprint for Smart Lab.

This module manages analyzer configuration only. It does not claim that a
physical analyzer is connected; live connectivity requires a protocol adapter.
"""
import os
from datetime import datetime
from functools import wraps

import mysql.connector
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, current_app
)

analyzer_management_bp = Blueprint(
    "analyzer_management", __name__, url_prefix="/analyzer-management"
)

ALLOWED_ROLES = ("Developer", "Admin", "Technician")
CONNECTION_TYPES = ("USB", "Serial/COM", "TCP/IP", "File Import", "Other")
PROTOCOLS = ("Unknown", "ASTM", "HL7", "HTTP/JSON", "CSV", "Vendor-specific", "Other")


def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


def analyzer_access_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "lab_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") not in ALLOWED_ROLES:
            return "403 Forbidden", 403
        return view(*args, **kwargs)
    return wrapped


def ensure_tables():
    """Create only this module's tables; safe to call on module page visits."""
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS analyzer_devices (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                lab_id VARCHAR(64) NOT NULL,
                analyzer_name VARCHAR(120) NOT NULL,
                manufacturer VARCHAR(120) NOT NULL,
                model_number VARCHAR(120) NOT NULL,
                test_category VARCHAR(80) NOT NULL DEFAULT 'Other',
                connection_type VARCHAR(40) NOT NULL DEFAULT 'USB',
                protocol VARCHAR(40) NOT NULL DEFAULT 'Unknown',
                host_address VARCHAR(255) NULL,
                host_port INT NULL,
                enabled TINYINT(1) NOT NULL DEFAULT 1,
                last_seen_at DATETIME NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_analyzer_devices_lab (lab_id),
                INDEX idx_analyzer_devices_lab_enabled (lab_id, enabled)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS analyzer_test_mappings (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                lab_id VARCHAR(64) NOT NULL,
                analyzer_id BIGINT UNSIGNED NOT NULL,
                analyzer_test_code VARCHAR(120) NOT NULL,
                smart_lab_test_id BIGINT UNSIGNED NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_analyzer_test_code (lab_id, analyzer_id, analyzer_test_code),
                INDEX idx_analyzer_mapping_lab (lab_id),
                CONSTRAINT fk_analyzer_mapping_device
                    FOREIGN KEY (analyzer_id) REFERENCES analyzer_devices(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        db.commit()
    except Exception:
        db.rollback()
        current_app.logger.exception("Analyzer Management table initialization failed")
        raise
    finally:
        cur.close()
        db.close()


def status_for(device):
    # Configuration is not proof of a live hardware connection.
    if not device["enabled"]:
        return "Disabled"
    if device.get("last_seen_at"):
        return "Seen previously"
    return "Not verified"


@analyzer_management_bp.route("/")
@analyzer_access_required
def dashboard():
    ensure_tables()
    lab_id = session["lab_id"]
    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT COUNT(*) AS total, SUM(enabled=1) AS enabled_count FROM analyzer_devices WHERE lab_id=%s", (lab_id,))
        stats = cur.fetchone() or {}
        cur.execute("SELECT COUNT(*) AS total FROM analyzer_test_mappings WHERE lab_id=%s", (lab_id,))
        stats["mapping_count"] = (cur.fetchone() or {}).get("total", 0)
        # Aliases used by templates/analyzer_management.html
        stats["total_devices"] = stats.get("total", 0) or 0
        stats["enabled_devices"] = stats.get("enabled_count", 0) or 0
        stats["total_mappings"] = stats.get("mapping_count", 0) or 0
        try:
            cur.execute("SELECT COUNT(*) AS total, SUM(status='failed') AS failed_count, SUM(status='completed') AS completed_count FROM analyzer_packets WHERE lab_id=%s", (lab_id,))
            packet_stats = cur.fetchone() or {}
        except mysql.connector.Error:
            # Keep the configuration dashboard usable if receiver table migration differs.
            db.rollback()
            packet_stats = {"total": 0, "failed_count": 0, "completed_count": 0}
        stats["failed_packets"] = packet_stats.get("failed_count", 0) or 0
        cur.execute("SELECT * FROM analyzer_devices WHERE lab_id=%s ORDER BY created_at DESC", (lab_id,))
        devices = cur.fetchall()
        for device in devices:
            device["display_status"] = status_for(device)
        return render_template(
            "analyzer_management.html", devices=devices,
            stats=stats, packet_stats=packet_stats,
            current_time=datetime.now().strftime("%d %b %Y | %I:%M %p")
        )
    finally:
        cur.close()
        db.close()


@analyzer_management_bp.route("/add", methods=["GET", "POST"])
@analyzer_access_required
def add_analyzer():
    ensure_tables()
    if request.method == "POST":
        values = {
            "analyzer_name": request.form.get("analyzer_name", "").strip(),
            "manufacturer": request.form.get("manufacturer", "").strip(),
            "model_number": request.form.get("model_number", "").strip(),
            "test_category": request.form.get("test_category", "Other").strip(),
            "connection_type": request.form.get("connection_type", "USB").strip(),
            "protocol": request.form.get("protocol", "Unknown").strip(),
            "host_address": request.form.get("host_address", "").strip() or None,
            "host_port": request.form.get("host_port", "").strip() or None,
        }
        if not all(values[k] for k in ("analyzer_name", "manufacturer", "model_number")):
            flash("Analyzer name, manufacturer and model are required.", "danger")
            return render_template("analyzer_management_form.html", device=values, connection_types=CONNECTION_TYPES, protocols=PROTOCOLS, page_title="Add Analyzer")
        if values["connection_type"] not in CONNECTION_TYPES or values["protocol"] not in PROTOCOLS:
            flash("Invalid connection type or protocol selection.", "danger")
            return render_template("analyzer_management_form.html", device=values, connection_types=CONNECTION_TYPES, protocols=PROTOCOLS, page_title="Add Analyzer")
        try:
            port = int(values["host_port"]) if values["host_port"] else None
            if port is not None and not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            flash("Port must be a number between 1 and 65535.", "danger")
            return render_template("analyzer_management_form.html", device=values, connection_types=CONNECTION_TYPES, protocols=PROTOCOLS, page_title="Add Analyzer")
        db = get_db()
        cur = db.cursor()
        try:
            cur.execute("""INSERT INTO analyzer_devices
                (lab_id, analyzer_name, manufacturer, model_number, test_category,
                 connection_type, protocol, host_address, host_port, enabled)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,1)""",
                (session["lab_id"], values["analyzer_name"], values["manufacturer"], values["model_number"],
                 values["test_category"], values["connection_type"], values["protocol"], values["host_address"], port))
            db.commit()
            flash("Analyzer configuration saved. Physical connection is not yet verified.", "success")
            return redirect(url_for("analyzer_management.dashboard"))
        except Exception:
            db.rollback()
            current_app.logger.exception("Could not save analyzer configuration")
            flash("Could not save analyzer. Check application logs and database permissions.", "danger")
        finally:
            cur.close()
            db.close()
        values["host_port"] = values["host_port"] or ""
        return render_template("analyzer_management_form.html", device=values, connection_types=CONNECTION_TYPES, protocols=PROTOCOLS, page_title="Add Analyzer")
    return render_template("analyzer_management_form.html", device={}, connection_types=CONNECTION_TYPES, protocols=PROTOCOLS, page_title="Add Analyzer")


@analyzer_management_bp.route("/<int:analyzer_id>/edit", methods=["GET", "POST"])
@analyzer_access_required
def edit_analyzer(analyzer_id):
    ensure_tables()
    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM analyzer_devices WHERE id=%s AND lab_id=%s", (analyzer_id, session["lab_id"]))
        device = cur.fetchone()
        if not device:
            flash("Analyzer not found for this laboratory.", "warning")
            return redirect(url_for("analyzer_management.dashboard"))
        if request.method == "POST":
            fields = {k: request.form.get(k, "").strip() for k in ("analyzer_name", "manufacturer", "model_number", "test_category", "connection_type", "protocol", "host_address", "host_port")}
            if not all(fields[k] for k in ("analyzer_name", "manufacturer", "model_number")):
                flash("Analyzer name, manufacturer and model are required.", "danger")
            elif fields["connection_type"] not in CONNECTION_TYPES or fields["protocol"] not in PROTOCOLS:
                flash("Invalid connection type or protocol selection.", "danger")
            else:
                try:
                    port = int(fields["host_port"]) if fields["host_port"] else None
                    if port is not None and not 1 <= port <= 65535:
                        raise ValueError
                    cur.execute("""UPDATE analyzer_devices SET analyzer_name=%s, manufacturer=%s, model_number=%s,
                        test_category=%s, connection_type=%s, protocol=%s, host_address=%s, host_port=%s
                        WHERE id=%s AND lab_id=%s""",
                        (fields["analyzer_name"], fields["manufacturer"], fields["model_number"], fields["test_category"],
                         fields["connection_type"], fields["protocol"], fields["host_address"] or None, port, analyzer_id, session["lab_id"]))
                    db.commit()
                    flash("Analyzer configuration updated. Connection status still requires real communication.", "success")
                    return redirect(url_for("analyzer_management.dashboard"))
                except ValueError:
                    flash("Port must be a number between 1 and 65535.", "danger")
                except Exception:
                    db.rollback()
                    current_app.logger.exception("Could not update analyzer configuration")
                    flash("Could not update analyzer configuration.", "danger")
            device.update(fields)
        return render_template("analyzer_management_form.html", device=device, connection_types=CONNECTION_TYPES, protocols=PROTOCOLS, page_title="Edit Analyzer")
    finally:
        cur.close()
        db.close()


@analyzer_management_bp.route("/<int:analyzer_id>/toggle", methods=["POST"])
@analyzer_access_required
def toggle_analyzer(analyzer_id):
    ensure_tables()
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("UPDATE analyzer_devices SET enabled = 1 - enabled WHERE id=%s AND lab_id=%s", (analyzer_id, session["lab_id"]))
        if cur.rowcount:
            db.commit()
            flash("Analyzer enabled state updated.", "success")
        else:
            db.rollback()
            flash("Analyzer not found for this laboratory.", "warning")
    except Exception:
        db.rollback()
        current_app.logger.exception("Could not toggle analyzer")
        flash("Could not update analyzer state.", "danger")
    finally:
        cur.close()
        db.close()
    return redirect(url_for("analyzer_management.dashboard"))


@analyzer_management_bp.route("/logs")
@analyzer_access_required
def communication_logs():
    ensure_tables()
    db = get_db()
    cur = db.cursor(dictionary=True)
    packets = []
    unavailable = False
    try:
        try:
            cur.execute("""SELECT message_id, analyzer_id, sample_id, test_code, status,
                error_message, retry_count, last_retry_at, processed_at
                FROM analyzer_packets WHERE lab_id=%s ORDER BY COALESCE(last_retry_at, processed_at) DESC LIMIT 200""", (session["lab_id"],))
            packets = cur.fetchall()
        except mysql.connector.Error:
            db.rollback()
            unavailable = True
        return render_template("analyzer_management_logs.html", packets=packets, unavailable=unavailable)
    finally:
        cur.close()
        db.close()
# =========================================================
# ANALYZER TEST MAPPING
# =========================================================

@analyzer_management_bp.route("/mappings", methods=["GET", "POST"])
@analyzer_access_required
def test_mappings():
    ensure_tables()

    lab_id = session["lab_id"]
    db = get_db()
    cur = db.cursor(dictionary=True)

    try:
        if request.method == "POST":
            analyzer_id = request.form.get("analyzer_id", type=int)
            analyzer_test_code = (
                request.form.get("analyzer_test_code") or ""
            ).strip()
            smart_lab_test_id = request.form.get(
                "smart_lab_test_id", type=int
            )

            if not analyzer_id or not analyzer_test_code or not smart_lab_test_id:
                flash("Please fill all mapping fields.", "danger")
                return redirect(url_for("analyzer_management.test_mappings"))

            # Verify analyzer belongs to the current laboratory
            cur.execute("""
                SELECT id
                FROM analyzer_devices
                WHERE id = %s AND lab_id = %s AND enabled = 1
            """, (analyzer_id, lab_id))

            analyzer = cur.fetchone()

            if not analyzer:
                flash("Invalid or disabled analyzer.", "danger")
                return redirect(url_for("analyzer_management.test_mappings"))

            # Verify test belongs to this laboratory or is a global test
            cur.execute("""
                SELECT id
                FROM tests
                WHERE id = %s
                  AND (lab_id = %s OR lab_id IS NULL)
            """, (smart_lab_test_id, lab_id))

            test = cur.fetchone()

            if not test:
                flash("Selected test is not available for this laboratory.", "danger")
                return redirect(url_for("analyzer_management.test_mappings"))

            try:
                cur.execute("""
                    INSERT INTO analyzer_test_mappings
                    (
                        lab_id,
                        analyzer_id,
                        analyzer_test_code,
                        smart_lab_test_id
                    )
                    VALUES (%s, %s, %s, %s)
                """, (
                    lab_id,
                    analyzer_id,
                    analyzer_test_code,
                    smart_lab_test_id
                ))

                db.commit()
                flash("Analyzer test mapping saved successfully.", "success")

            except mysql.connector.IntegrityError:
                db.rollback()
                flash(
                    "This analyzer test code is already mapped. "
                    "Use a different code.",
                    "warning"
                )

            return redirect(url_for("analyzer_management.test_mappings"))

        # Load enabled analyzers for this laboratory
        cur.execute("""
            SELECT id, analyzer_name, model_number
            FROM analyzer_devices
            WHERE lab_id = %s AND enabled = 1
            ORDER BY analyzer_name
        """, (lab_id,))
        devices = cur.fetchall()

        # Load tests available to this laboratory
        cur.execute("""
            SELECT id, test_name
            FROM tests
            WHERE lab_id = %s OR lab_id IS NULL
            ORDER BY test_name
        """, (lab_id,))
        tests = cur.fetchall()

        # Load existing mappings
        cur.execute("""
            SELECT
                m.id,
                m.analyzer_test_code,
                d.analyzer_name,
                t.test_name,
                m.created_at
            FROM analyzer_test_mappings m
            JOIN analyzer_devices d ON d.id = m.analyzer_id
            JOIN tests t ON t.id = m.smart_lab_test_id
            WHERE m.lab_id = %s
            ORDER BY m.created_at DESC
        """, (lab_id,))
        mappings = cur.fetchall()

        return render_template(
            "analyzer_test_mappings.html",
            devices=devices,
            tests=tests,
            mappings=mappings
        )

    except Exception:
        db.rollback()
        current_app.logger.exception("Failed to load analyzer test mappings")
        raise

    finally:
        cur.close()
        db.close()