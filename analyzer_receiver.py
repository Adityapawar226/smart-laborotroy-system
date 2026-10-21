from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os

from flask import Flask, request, jsonify
from dotenv import load_dotenv
import mysql.connector


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")

app = Flask(__name__)

API_KEY = os.getenv("ANALYZER_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "ANALYZER_API_KEY is missing from the .env file"
    )

app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

# Analyzer test code -> Smart Lab test ID
ANALYZER_TEST_MAPPING = {
    "CBC": 26
}


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


def record_packet_failure(
    message_id, analyzer_id, sample_id, patient_test_id,
    lab_id, test_code, packet_hash, error_message
):
    """Persist failure metadata outside the rolled-back result transaction.

    patient_test_id and lab_id may be NULL for early validation failures
    (for example, an unknown sample ID). The table must permit NULL in those
    two columns; message_id remains globally unique.
    """
    if not all([message_id, analyzer_id, sample_id, test_code, packet_hash]):
        return

    failure_connection = None
    failure_cursor = None
    try:
        # Keep error details useful but bounded; never include credentials.
        safe_error = (str(error_message) or "Processing failed")[:4000]
        failure_connection = get_db()
        failure_cursor = failure_connection.cursor()
        failure_cursor.execute(
            """
            INSERT INTO analyzer_packets (
                message_id, analyzer_id, sample_id, patient_test_id,
                lab_id, test_code, packet_hash, status, error_message,
                retry_count, last_retry_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'failed', %s, 1, CURRENT_TIMESTAMP)
            ON DUPLICATE KEY UPDATE
                status = IF(
                    status = 'completed'
                    OR packet_hash <> VALUES(packet_hash)
                    OR analyzer_id <> VALUES(analyzer_id)
                    OR sample_id <> VALUES(sample_id)
                    OR (lab_id IS NOT NULL AND VALUES(lab_id) IS NOT NULL AND lab_id <> VALUES(lab_id)),
                    status,
                    'failed'
                ),
                error_message = IF(
                    status = 'completed'
                    OR packet_hash <> VALUES(packet_hash)
                    OR analyzer_id <> VALUES(analyzer_id)
                    OR sample_id <> VALUES(sample_id)
                    OR (lab_id IS NOT NULL AND VALUES(lab_id) IS NOT NULL AND lab_id <> VALUES(lab_id)),
                    error_message,
                    VALUES(error_message)
                ),
                retry_count = IF(
                    status = 'completed'
                    OR packet_hash <> VALUES(packet_hash)
                    OR analyzer_id <> VALUES(analyzer_id)
                    OR sample_id <> VALUES(sample_id)
                    OR (lab_id IS NOT NULL AND VALUES(lab_id) IS NOT NULL AND lab_id <> VALUES(lab_id)),
                    retry_count,
                    retry_count + 1
                ),
                last_retry_at = IF(
                    status = 'completed'
                    OR packet_hash <> VALUES(packet_hash)
                    OR analyzer_id <> VALUES(analyzer_id)
                    OR sample_id <> VALUES(sample_id)
                    OR (lab_id IS NOT NULL AND VALUES(lab_id) IS NOT NULL AND lab_id <> VALUES(lab_id)),
                    last_retry_at,
                    CURRENT_TIMESTAMP
                )
            """,
            (message_id, analyzer_id, sample_id, patient_test_id,
             lab_id, test_code, packet_hash, safe_error)
        )
        failure_connection.commit()
    except Exception:
        app.logger.exception("Could not persist analyzer packet failure")
        if failure_connection and failure_connection.is_connected():
            failure_connection.rollback()
    finally:
        if failure_cursor:
            failure_cursor.close()
        if failure_connection and failure_connection.is_connected():
            failure_connection.close()


def test_db_connection():
    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor()

        cursor.execute("SELECT DATABASE()")
        database_name = cursor.fetchone()[0]

        print("MySQL connection successful!")
        print("Connected database:", database_name)

    except mysql.connector.Error as exc:
        print("MySQL connection failed:", exc)

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "analyzer-receiver",
        "time_utc": datetime.now(timezone.utc).isoformat()
    }), 200


# =========================================================
# RECEIVE AND SAVE ANALYZER RESULTS
# =========================================================

@app.route("/api/analyzer/receive", methods=["POST"])
def receive_analyzer_packet():

    # -----------------------------------------------------
    # STEP 1: Authenticate analyzer
    # -----------------------------------------------------

    received_key = request.headers.get("X-Analyzer-Key", "")

    if received_key != API_KEY:
        return jsonify({
            "ok": False,
            "error": "Unauthorized analyzer"
        }), 401

    # -----------------------------------------------------
    # STEP 2: Validate JSON request
    # -----------------------------------------------------

    if not request.is_json:
        return jsonify({
            "ok": False,
            "error": "Content-Type must be application/json"
        }), 415

    packet = request.get_json(silent=True)

    if not isinstance(packet, dict):
        return jsonify({
            "ok": False,
            "error": "Invalid JSON packet"
        }), 400

    # -----------------------------------------------------
    # STEP 3: Validate required fields
    # -----------------------------------------------------

    required_fields = [
        "message_id",
        "analyzer_id",
        "sample_id",
        "test_code",
        "results"
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in packet
    ]

    if missing_fields:
        return jsonify({
            "ok": False,
            "error": "Required fields are missing",
            "missing_fields": missing_fields
        }), 400

    # -----------------------------------------------------
    # STEP 4: Validate message ID and calculate packet hash
    # -----------------------------------------------------

    message_id = packet.get("message_id")
    if not isinstance(message_id, str) or not message_id.strip():
        return jsonify({
            "ok": False,
            "error": "message_id must be a non-empty string"
        }), 400
    message_id = message_id.strip()

    # Stable hash: identical JSON packets produce the same hash.
    canonical_packet = json.dumps(
        packet,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False
    )
    packet_hash = hashlib.sha256(
        canonical_packet.encode("utf-8")
    ).hexdigest()

    # -----------------------------------------------------
    # STEP 5: Validate identifiers
    # -----------------------------------------------------

    for field in ["analyzer_id", "sample_id", "test_code"]:

        value = packet.get(field)

        if not isinstance(value, str) or not value.strip():
            return jsonify({
                "ok": False,
                "error": f"{field} must be a non-empty string"
            }), 400

    analyzer_id = packet["analyzer_id"].strip()
    sample_id = packet["sample_id"].strip()
    test_code = packet["test_code"].strip().upper()

    results = packet["results"]

    # -----------------------------------------------------
    # STEP 5: Validate result keys and values
    # -----------------------------------------------------

    if not isinstance(results, dict) or not results:
        return jsonify({
            "ok": False,
            "error": "Results must be a non-empty JSON object"
        }), 400

    if not all(
        isinstance(key, str) and key.strip()
        for key in results
    ):
        return jsonify({
            "ok": False,
            "error": "Every result must have a valid parameter key"
        }), 400

    if not all(
        isinstance(value, (str, int, float))
        and not isinstance(value, bool)
        for value in results.values()
    ):
        return jsonify({
            "ok": False,
            "error": "Result values must be strings or numbers"
        }), 400

    # Reject non-finite numeric values such as NaN and Infinity.
    for value in results.values():

        if isinstance(value, float):
            if not __import__("math").isfinite(value):
                return jsonify({
                    "ok": False,
                    "error": "Result values must be finite numbers"
                }), 400

    # -----------------------------------------------------
    # STEP 6: Map analyzer test code to Smart Lab test ID
    # -----------------------------------------------------

    test_id = ANALYZER_TEST_MAPPING.get(test_code)

    if test_id is None:
        return jsonify({
            "ok": False,
            "error": "Unsupported analyzer test code",
            "test_code": test_code
        }), 400

    connection = None
    cursor = None

    try:

        connection = get_db()
        connection.start_transaction()

        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # STEP 7: Find the exact sample
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                s.sample_id,
                s.patient_id,
                s.lab_id
            FROM samples s
            WHERE s.sample_id = %s
            FOR UPDATE
            """,
            (sample_id,)
        )

        sample = cursor.fetchone()

        if not sample:
            connection.rollback()
            record_packet_failure(
                message_id, analyzer_id, sample_id, None,
                None, test_code, packet_hash,
                f"Sample ID not found: {sample_id}"
            )

            return jsonify({
                "ok": False,
                "error": "Sample ID not found",
                "sample_id": sample_id,
                "message_id": message_id,
                "failure_logged": True
            }), 404

        patient_id = sample["patient_id"]
        lab_id = sample["lab_id"]

        # -------------------------------------------------
        # STEP 8: Find the exact patient test
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                pt.id AS patient_test_id,
                pt.patient_id,
                pt.sample_id,
                pt.test_id,
                pt.lab_id,
                pt.analyzer_status,
                t.test_name
            FROM patient_tests pt
            JOIN tests t
                ON t.id = pt.test_id
            WHERE pt.sample_id = %s
              AND pt.patient_id = %s
              AND pt.lab_id = %s
              AND pt.test_id = %s
            FOR UPDATE
            """,
            (
                sample_id,
                patient_id,
                lab_id,
                test_id
            )
        )

        patient_test = cursor.fetchone()

        if not patient_test:
            connection.rollback()
            record_packet_failure(
                message_id, analyzer_id, sample_id, None,
                lab_id, test_code, packet_hash,
                f"Matching patient test not found for sample {sample_id}, test {test_id}, lab {lab_id}"
            )

            return jsonify({
                "ok": False,
                "error": "Matching patient test not found",
                "sample_id": sample_id,
                "test_id": test_id,
                "lab_id": lab_id,
                "message_id": message_id,
                "failure_logged": True
            }), 404

        patient_test_id = patient_test["patient_test_id"]

        # -------------------------------------------------
        # STEP 8A: Reserve this packet ID (idempotency guard)
        # -------------------------------------------------
        # The analyzer_packets.message_id UNIQUE key is the final
        # protection against concurrent/repeated delivery. This insert
        # is in the same transaction as result inserts, so a failed save
        # rolls the reservation back and allows a safe retry.
        try:
            cursor.execute(
                """
                INSERT INTO analyzer_packets (
                    message_id,
                    analyzer_id,
                    sample_id,
                    patient_test_id,
                    lab_id,
                    test_code,
                    packet_hash,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'processing')
                """,
                (
                    message_id,
                    analyzer_id,
                    sample_id,
                    patient_test_id,
                    lab_id,
                    test_code,
                    packet_hash
                )
            )
        except mysql.connector.IntegrityError as exc:
            if exc.errno != 1062:
                raise

            # Undo this transaction, then inspect the existing packet.
            connection.rollback()
            cursor.execute(
                """
                SELECT packet_hash, status, analyzer_id, sample_id,
                       patient_test_id, lab_id
                FROM analyzer_packets
                WHERE message_id = %s
                LIMIT 1
                """,
                (message_id,)
            )
            existing_packet = cursor.fetchone()

            if not existing_packet:
                # The conflicting unique key may have been a different
                # unique index; do not silently treat it as a duplicate.
                return jsonify({
                    "ok": False,
                    "error": "Packet conflicts with an existing analyzer record"
                }), 409

            if existing_packet["packet_hash"] != packet_hash:
                return jsonify({
                    "ok": False,
                    "error": "message_id was already used with different packet data",
                    "message_id": message_id,
                    "duplicate": False
                }), 409

            if existing_packet["status"] == "completed":
                return jsonify({
                    "ok": True,
                    "duplicate": True,
                    "database_saved": True,
                    "message": "Packet was already processed; no results were inserted again",
                    "message_id": message_id,
                    "analyzer_id": existing_packet["analyzer_id"],
                    "sample_id": existing_packet["sample_id"],
                    "lab_id": existing_packet["lab_id"],
                    "patient_test_id": existing_packet["patient_test_id"]
                }), 200

            if existing_packet["status"] == "failed":
                # A failed packet with the same hash is safe to retry. Start a
                # fresh transaction because the duplicate insert rolled back.
                connection.start_transaction()
                cursor.execute(
                    """
                    UPDATE analyzer_packets
                    SET status = 'processing',
                        error_message = NULL,
                        retry_count = retry_count + 1,
                        last_retry_at = CURRENT_TIMESTAMP,
                        processed_at = NULL,
                        lab_id = %s,
                        patient_test_id = %s
                    WHERE message_id = %s
                      AND (lab_id = %s OR lab_id IS NULL)
                      AND analyzer_id = %s
                      AND sample_id = %s
                      AND packet_hash = %s
                      AND status = 'failed'
                    """,
                    (
                        lab_id,
                        patient_test_id,
                        message_id,
                        lab_id,
                        analyzer_id,
                        sample_id,
                        packet_hash
                    )
                )
                if cursor.rowcount == 1:
                    # Continue below with parameter mapping and result saving.
                    pass
                else:
                    connection.rollback()
                    return jsonify({
                        "ok": False,
                        "duplicate": True,
                        "error": "Failed packet could not be reserved for retry; send it again shortly",
                        "message_id": message_id
                    }), 409
            else:
                return jsonify({
                    "ok": False,
                    "duplicate": True,
                    "error": "This packet ID is currently being processed",
                    "message_id": message_id,
                    "status": existing_packet["status"]
                }), 409

        # -------------------------------------------------
        # STEP 9: Load parameter definitions
        #
        # parameter_definition does not contain test_id.
        # Test association is resolved through:
        #
        # parameter_definition
        #     -> report_components
        #     -> test_sections
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                pd.id AS parameter_id,
                pd.parameter_code,
                pd.display_name,
                pd.short_name,
                pd.unit,
                pd.component_id,
                rc.section_id,
                pd.lab_id AS parameter_lab_id
            FROM parameter_definition pd
            JOIN report_components rc
                ON rc.id = pd.component_id
            JOIN test_sections ts
                ON ts.id = rc.section_id
            WHERE ts.test_id = %s
              AND pd.status = 'active'
              AND (pd.lab_id = %s OR pd.lab_id IS NULL)
              AND (rc.is_active = 1 OR rc.is_active IS NULL)
            ORDER BY
                CASE
                    WHEN pd.lab_id = %s THEN 0
                    ELSE 1
                END,
                pd.id
            """,
            (
                test_id,
                lab_id,
                lab_id
            )
        )

        parameter_rows = cursor.fetchall()

        if not parameter_rows:
            connection.rollback()

            return jsonify({
                "ok": False,
                "error": "No active parameter definitions found",
                "test_id": test_id,
                "lab_id": lab_id
            }), 400

        # -------------------------------------------------
        # STEP 10: Build parameter lookup
        #
        # FIX:
        # HB and Hb normalize to the same key: "hb".
        # If both belong to parameter ID 49, this is not
        # ambiguous.
        #
        # If the same normalized key belongs to different
        # parameter IDs, mark it ambiguous.
        #
        # Lab-specific definitions take precedence over
        # global definitions when the same key is present.
        # -------------------------------------------------

        parameter_lookup = {}

        for row in parameter_rows:

            possible_keys = [
                row["parameter_code"],
                row["display_name"],
                row["short_name"]
            ]

            for key in possible_keys:

                if not key:
                    continue

                normalized_key = key.strip().casefold()

                if normalized_key not in parameter_lookup:

                    parameter_lookup[normalized_key] = row
                    continue

                existing_parameter = parameter_lookup[
                    normalized_key
                ]

                # Already ambiguous: do not choose randomly.
                if existing_parameter is None:
                    continue

                # Same parameter ID means duplicate aliases
                # for the same parameter, not an ambiguity.
                if (
                    existing_parameter["parameter_id"]
                    == row["parameter_id"]
                ):
                    continue

                # Prefer the lab-specific definition over a
                # global definition if both have the same key.
                existing_is_lab_specific = (
                    existing_parameter["parameter_lab_id"] == lab_id
                )

                new_is_lab_specific = (
                    row["parameter_lab_id"] == lab_id
                )

                if (
                    new_is_lab_specific
                    and not existing_is_lab_specific
                ):
                    parameter_lookup[normalized_key] = row

                elif (
                    existing_is_lab_specific
                    and not new_is_lab_specific
                ):
                    continue

                else:
                    # Different parameters share the same key
                    # at the same priority level.
                    parameter_lookup[normalized_key] = None

        # -------------------------------------------------
        # STEP 11: Map all incoming results
        # -------------------------------------------------

        mapped_results = []
        unknown_parameters = []
        seen_parameter_ids = set()
        duplicate_packet_keys = []

        for incoming_key, result_value in results.items():

            normalized_key = incoming_key.strip().casefold()

            parameter = parameter_lookup.get(normalized_key)

            if parameter is None:
                unknown_parameters.append(incoming_key)
                continue

            parameter_id = parameter["parameter_id"]

            # Prevent two incoming aliases from inserting
            # duplicate results for the same parameter.
            if parameter_id in seen_parameter_ids:
                duplicate_packet_keys.append(incoming_key)
                continue

            seen_parameter_ids.add(parameter_id)

            mapped_results.append(
                (
                    parameter,
                    str(result_value).strip()
                )
            )

        if unknown_parameters:
            connection.rollback()

            return jsonify({
                "ok": False,
                "error": "Some result keys are unknown or ambiguous",
                "unknown_parameters": unknown_parameters,
                "message": "No results were saved"
            }), 400

        if duplicate_packet_keys:
            connection.rollback()

            return jsonify({
                "ok": False,
                "error": (
                    "Multiple incoming keys map to the same parameter"
                ),
                "duplicate_keys": duplicate_packet_keys,
                "message": "No results were saved"
            }), 400

        if not mapped_results:
            connection.rollback()

            return jsonify({
                "ok": False,
                "error": "No valid result parameters were supplied"
            }), 400

        # -------------------------------------------------
        # STEP 12: Check existing results
        #
        # Do not silently overwrite existing results.
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT parameter_id, result_value
            FROM test_results
            WHERE lab_id = %s
              AND patient_id = %s
              AND patient_test_id = %s
              AND sample_id = %s
            FOR UPDATE
            """,
            (
                lab_id,
                patient_id,
                patient_test_id,
                sample_id
            )
        )

        existing_rows = cursor.fetchall()
        existing_values = {
            row["parameter_id"]: str(row["result_value"]).strip()
            for row in existing_rows
        }

        duplicate_parameters = [
            parameter["parameter_id"]
            for parameter, _ in mapped_results
            if parameter["parameter_id"] in existing_values
        ]

        if duplicate_parameters:
            # Compatibility with results saved before analyzer_packets
            # tracking was added: if ALL incoming parameters already exist
            # and their values match, record this packet as completed instead
            # of returning 409 or inserting the results a second time.
            all_already_present = all(
                parameter["parameter_id"] in existing_values
                for parameter, _ in mapped_results
            )

            def values_match(existing, incoming):
                existing = str(existing).strip()
                incoming = str(incoming).strip()
                try:
                    from decimal import Decimal, InvalidOperation
                    return Decimal(existing) == Decimal(incoming)
                except (InvalidOperation, ValueError):
                    return existing.casefold() == incoming.casefold()

            all_values_match = all(
                values_match(
                    existing_values.get(parameter["parameter_id"], ""),
                    incoming_value
                )
                for parameter, incoming_value in mapped_results
                if parameter["parameter_id"] in existing_values
            )

            if all_already_present and all_values_match:
                cursor.execute(
                    """
                    UPDATE analyzer_packets
                    SET status = 'completed',
                        processed_at = CURRENT_TIMESTAMP
                    WHERE message_id = %s
                      AND lab_id = %s
                      AND analyzer_id = %s
                    """,
                    (message_id, lab_id, analyzer_id)
                )
                connection.commit()
                return jsonify({
                    "ok": True,
                    "duplicate": True,
                    "database_saved": True,
                    "message": (
                        "Matching results already existed; packet was "
                        "recorded without inserting duplicate results"
                    ),
                    "message_id": message_id,
                    "analyzer_id": analyzer_id,
                    "patient_id": patient_id,
                    "sample_id": sample_id,
                    "lab_id": lab_id,
                    "patient_test_id": patient_test_id,
                    "result_count": len(mapped_results)
                }), 200

            connection.rollback()
            return jsonify({
                "ok": False,
                "duplicate": False,
                "error": (
                    "Results already exist and do not fully match this packet"
                ),
                "duplicate_parameter_ids": duplicate_parameters,
                "message": (
                    "No results were saved. Existing results were preserved."
                )
            }), 409

        # -------------------------------------------------
        # STEP 13: Insert results into test_results
        # -------------------------------------------------

        insert_sql = """
            INSERT INTO test_results (
                patient_id,
                test_name,
                parameter_id,
                component_id,
                section_id,
                parameter_name,
                result_value,
                unit,
                reference_range,
                entry_mode,
                lab_id,
                patient_test_id,
                sample_id
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                'Automatic', %s, %s, %s
            )
        """

        for parameter, result_value in mapped_results:

            cursor.execute(
                insert_sql,
                (
                    patient_id,
                    patient_test["test_name"],
                    parameter["parameter_id"],
                    parameter["component_id"],
                    parameter["section_id"],
                    parameter["display_name"],
                    result_value,
                    parameter["unit"],
                    "",
                    lab_id,
                    patient_test_id,
                    sample_id
                )
            )

        # -------------------------------------------------
        # STEP 14: Update analyzer status
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE patient_tests
            SET analyzer_status = 'Completed'
            WHERE id = %s
              AND lab_id = %s
            """,
            (
                patient_test_id,
                lab_id
            )
        )

        # Mark the packet completed in the same transaction as its results.
        cursor.execute(
            """
            UPDATE analyzer_packets
            SET status = 'completed',
                processed_at = CURRENT_TIMESTAMP
            WHERE message_id = %s
              AND lab_id = %s
              AND analyzer_id = %s
            """,
            (message_id, lab_id, analyzer_id)
        )

        # Commit packet log, results and analyzer status together.
        connection.commit()

        # -------------------------------------------------
        # STEP 15: Log successful integration
        # -------------------------------------------------

        print("\n========== ANALYZER RESULTS SAVED ==========")
        print("Analyzer:", analyzer_id)
        print("Patient:", patient_id)
        print("Sample:", sample_id)
        print("Lab:", lab_id)
        print("Patient Test ID:", patient_test_id)
        print("Test:", patient_test["test_name"])
        print("Results saved:", len(mapped_results))
        print("============================================\n")

        return jsonify({
            "ok": True,
            "message": "Analyzer results saved successfully",
            "database_saved": True,
            "duplicate": False,
            "message_id": message_id,
            "analyzer_id": analyzer_id,
            "patient_id": patient_id,
            "sample_id": sample_id,
            "lab_id": lab_id,
            "patient_test_id": patient_test_id,
            "test_id": test_id,
            "result_count": len(mapped_results)
        }), 201

    # -----------------------------------------------------
    # DATABASE ERROR HANDLING
    # -----------------------------------------------------

    except mysql.connector.Error as exc:

        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception(
            "MySQL error while saving analyzer results"
        )
        # Save failure metadata in a separate transaction after rollback.
        record_packet_failure(
            locals().get("message_id"), locals().get("analyzer_id"),
            locals().get("sample_id"), locals().get("patient_test_id"),
            locals().get("lab_id"), locals().get("test_code"),
            locals().get("packet_hash"), f"MySQL error {getattr(exc, 'errno', '')}: {exc}"
        )

        return jsonify({
            "ok": False,
            "error": "Database operation failed",
            "retryable": True,
            "message_id": locals().get("message_id"),
            "message": (
                "No successful save was confirmed. The packet may be retried "
                "with the same message_id and identical data."
            )
        }), 500

    except Exception as exc:

        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception(
            "Unexpected analyzer integration error"
        )
        record_packet_failure(
            locals().get("message_id"), locals().get("analyzer_id"),
            locals().get("sample_id"), locals().get("patient_test_id"),
            locals().get("lab_id"), locals().get("test_code"),
            locals().get("packet_hash"), f"Unexpected error: {exc}"
        )

        return jsonify({
            "ok": False,
            "error": "Unexpected receiver error",
            "retryable": True,
            "message_id": locals().get("message_id")
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    print("Starting Smart Lab Analyzer Receiver...")
    print("Health check: http://127.0.0.1:5055/health")

    test_db_connection()

    app.run(
        host="127.0.0.1",
        port=5055,
        debug=False
    )