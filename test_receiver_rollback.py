import mysql.connector
from analyzer_receiver import get_db


def test_receiver_transaction_rollback():
    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor()

        # Prepare an isolated temporary table.
        cursor.execute("""
            CREATE TEMPORARY TABLE rollback_test_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                parameter_name VARCHAR(100) NOT NULL,
                result_value VARCHAR(100) NOT NULL
            ) ENGINE=InnoDB
        """)

        # CREATE TEMPORARY TABLE does not remove the table on rollback.
        # Ensure no transaction is active before starting the test.
        connection.rollback()
        connection.start_transaction()

        # Simulate first analyzer result insertion.
        cursor.execute("""
            INSERT INTO rollback_test_results
                (parameter_name, result_value)
            VALUES (%s, %s)
        """, ("HB", "13.8"))

        print("First result inserted inside transaction.")

        try:
            # Deliberately trigger a MySQL error.
            cursor.execute("""
                INSERT INTO rollback_test_table_does_not_exist
                    (parameter_name, result_value)
                VALUES (%s, %s)
            """, ("WBC_COUNT", "7200"))

        except mysql.connector.Error as exc:
            print("Simulated MySQL error:", exc.errno)

            connection.rollback()
            print("Transaction rolled back.")

        # Verify that the first insert was undone.
        connection.start_transaction()

        cursor.execute("""
            SELECT COUNT(*)
            FROM rollback_test_results
        """)

        count = cursor.fetchone()[0]

        print("Rows remaining after rollback:", count)

        if count == 0:
            print("PASS: No partial results remain.")
        else:
            print("FAIL: Partial results remain.")

        connection.rollback()

    except Exception as exc:
        if connection and connection.is_connected():
            connection.rollback()

        print("Test failed:", exc)

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    test_receiver_transaction_rollback()