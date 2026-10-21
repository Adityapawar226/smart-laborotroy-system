import mysql.connector
from analyzer_receiver import get_db


def test_transaction_rollback():
    connection = None
    cursor = None

    try:
        connection = get_db()
        connection.start_transaction()
        cursor = connection.cursor()

        # Create a temporary test table.
        # This table is separate from patient results.
        cursor.execute("""
            CREATE TEMPORARY TABLE IF NOT EXISTS
            transaction_test_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                parameter_name VARCHAR(100) NOT NULL,
                result_value VARCHAR(100) NOT NULL
            )
        """)

        # First insert should succeed.
        cursor.execute("""
            INSERT INTO transaction_test_results
            (parameter_name, result_value)
            VALUES (%s, %s)
        """, ("HB", "13.8"))

        print("First insert: SUCCESS")

        try:
            # Intentionally invalid SQL to simulate a DB failure.
            cursor.execute("""
                INSERT INTO table_that_does_not_exist
                (parameter_name, result_value)
                VALUES (%s, %s)
            """, ("WBC_COUNT", "7200"))

        except mysql.connector.Error as error:
            print("Simulated database error:", error.errno)

            # Roll back the whole transaction.
            connection.rollback()
            print("Transaction rollback: SUCCESS")

        # Start a fresh transaction to verify the outcome.
        connection.start_transaction()

        cursor.execute("""
            SELECT COUNT(*)
            FROM transaction_test_results
        """)

        count = cursor.fetchone()[0]

        print("Rows after rollback:", count)

        if count == 0:
            print("PASS: No partial results remain.")
        else:
            print("FAIL: Partial results remain.")

        connection.rollback()

    except Exception as error:
        if connection and connection.is_connected():
            connection.rollback()

        print("Test failed:", error)

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    test_transaction_rollback()