from analyzer_receiver import get_db, record_packet_failure


def test_failure_log_persistence():
    message_id = "TEST-FAILURE-LOG-20261020"

    # Unique identifiers for this isolated failure-log test.
    analyzer_id = "ANALYZER_TEST_LOG"
    sample_id = "SMP-TEST-LOG-NOT-EXIST"
    test_code = "CBC"
    packet_hash = "test-hash-failure-log-20261020"

    connection = None
    cursor = None

    try:
        # Remove a previous record only if it belongs to this exact
        # dedicated test message ID. Never touch other packets.
        connection = get_db()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT message_id, analyzer_id, sample_id, packet_hash, status
            FROM analyzer_packets
            WHERE message_id = %s
            """,
            (message_id,)
        )
        existing = cursor.fetchone()

        if existing:
            if (
                existing[1] != analyzer_id
                or existing[2] != sample_id
                or existing[3] != packet_hash
            ):
                raise RuntimeError(
                    "Test message ID already belongs to different packet data. "
                    "Choose a new unique message ID."
                )

            if existing[4] == "completed":
                raise RuntimeError(
                    "Test packet is already completed. Choose a new unique ID."
                )

            cursor.execute(
                "DELETE FROM analyzer_packets WHERE message_id = %s",
                (message_id,)
            )
            connection.commit()

        cursor.close()
        cursor = None
        connection.close()
        connection = None

        # Call the real failure logger, which uses its own DB connection.
        record_packet_failure(
            message_id=message_id,
            analyzer_id=analyzer_id,
            sample_id=sample_id,
            patient_test_id=None,
            lab_id=None,
            test_code=test_code,
            packet_hash=packet_hash,
            error_message="Controlled failure-log persistence test"
        )

        # Verify that the failure was committed to the real database.
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                message_id,
                status,
                retry_count,
                error_message,
                last_retry_at
            FROM analyzer_packets
            WHERE message_id = %s
            """,
            (message_id,)
        )

        row = cursor.fetchone()

        if not row:
            raise AssertionError(
                "Failure log was not found in analyzer_packets."
            )

        print("Message ID:", row["message_id"])
        print("Status:", row["status"])
        print("Retry count:", row["retry_count"])
        print("Error message:", row["error_message"])
        print("Last retry at:", row["last_retry_at"])

        assert row["status"] == "failed"
        assert row["retry_count"] >= 1
        assert row["error_message"] == (
            "Controlled failure-log persistence test"
        )

        print("PASS: Failure log persisted in MySQL.")

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    test_failure_log_persistence()