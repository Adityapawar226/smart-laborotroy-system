from unittest.mock import MagicMock, patch

import mysql.connector
import analyzer_receiver as receiver


def test_receiver_rolls_back_on_insert_failure():
    connection = MagicMock()
    cursor = MagicMock()

    connection.is_connected.return_value = True
    connection.cursor.return_value = cursor

    # Mock the sample lookup.
    sample = {
        "sample_id": "SMP-TEST-ROLLBACK",
        "patient_id": "PAT-TEST",
        "lab_id": "LAB-TEST",
    }

    # Mock the matching patient test.
    patient_test = {
        "patient_test_id": 9001,
        "patient_id": "PAT-TEST",
        "sample_id": "SMP-TEST-ROLLBACK",
        "test_id": 26,
        "lab_id": "LAB-TEST",
        "analyzer_status": "Pending",
        "test_name": "CBC",
    }

    parameters = [
        {
            "parameter_id": 101,
            "parameter_code": "HB",
            "display_name": "Hemoglobin",
            "short_name": "Hb",
            "unit": "g/dL",
            "component_id": 1,
            "section_id": 1,
            "parameter_lab_id": "LAB-TEST",
        },
        {
            "parameter_id": 102,
            "parameter_code": "WBC_COUNT",
            "display_name": "WBC Count",
            "short_name": "WBC",
            "unit": "cells/uL",
            "component_id": 1,
            "section_id": 1,
            "parameter_lab_id": "LAB-TEST",
        },
    ]

    cursor.fetchone.side_effect = [sample, patient_test]
    cursor.fetchall.side_effect = [parameters, []]

    insert_count = 0

    def execute_side_effect(sql, params=None):
        nonlocal insert_count

        normalized_sql = " ".join(sql.split()).upper()

        if normalized_sql.startswith("INSERT INTO TEST_RESULTS"):
            insert_count += 1

            if insert_count == 2:
                raise mysql.connector.Error(
                    msg="Simulated test database failure",
                    errno=1146,
                )

    cursor.execute.side_effect = execute_side_effect

    packet = {
        "message_id": "MOCK-ROLLBACK-TEST-001",
        "analyzer_id": "ANALYZER_TEST",
        "sample_id": "SMP-TEST-ROLLBACK",
        "test_code": "CBC",
        "results": {
            "HB": 13.8,
            "WBC_COUNT": 7200,
        },
    }

    with (
        patch.object(receiver, "get_db", return_value=connection),
        patch.object(receiver, "record_packet_failure") as failure_logger,
    ):
        client = receiver.app.test_client()

        response = client.post(
            "/api/analyzer/receive",
            json=packet,
            headers={"X-Analyzer-Key": receiver.API_KEY},
        )

    print("HTTP status:", response.status_code)
    print("Response:", response.get_json())
    print("Result insert attempts:", insert_count)
    print("Rollback called:", connection.rollback.called)
    print("Failure logger called:", failure_logger.called)

    assert response.status_code == 500
    assert insert_count == 2
    assert connection.rollback.called
    assert failure_logger.called

    print("PASS: Receiver handled the simulated insert failure.")


if __name__ == "__main__":
    test_receiver_rolls_back_on_insert_failure()