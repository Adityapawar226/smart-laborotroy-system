import mysql.connector
from analyzer_receiver import get_db


def test_mysql_atomicity():
    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor()

        # Create an isolated InnoDB temporary table.
        cursor.execute("""
            CREATE TEMPORARY TABLE rollback_atomicity_test (
                id INT AUTO_INCREMENT PRIMARY KEY,
                parameter_name VARCHAR(100) NOT NULL,
                result_value VARCHAR(100) NOT NULL
            ) ENGINE=InnoDB
        """)

        connection.commit()

        # Begin the transaction being tested.
        connection.start_transaction()

        # Simulate the first successful analyzer result.
        cursor.execute("""
            INSERT INTO rollback_atomicity_test
                (parameter_name, result_value)
            VALUES (%s, %s)
        """, ("HB", "13.8"))

        print("First insert: SUCCESS")

        # Force a genuine MySQL error.
        try:
            cursor.execute("""
                INSERT INTO rollback_atomicity_table_missing
                    (parameter_name, result_value)
                VALUES (%s, %s)
            """, ("WBC_COUNT", "7200"))

        except mysql.connector.Error as exc:
            print("Simulated MySQL error:", exc.errno)

            connection.rollback()
            print("Rollback executed.")

        # Verify using a fresh transaction.
        connection.start_transaction()

        cursor.execute("""
            SELECT COUNT(*)
            FROM rollback_atomicity_test
        """)

        remaining_rows = cursor.fetchone()[0]

        print("Rows remaining after rollback:", remaining_rows)

        if remaining_rows == 0:
            print("PASS: MySQL removed the uncommitted insert.")
        else:
            print("FAIL: Unexpected rows remain.")

        connection.rollback()

        if remaining_rows != 0:
            raise AssertionError("Transaction rollback test failed.")

    except Exception as exc:
        if connection and connection.is_connected():
            connection.rollback()

        print("TEST FAILED:", exc)
        raise

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    test_mysql_atomicity()