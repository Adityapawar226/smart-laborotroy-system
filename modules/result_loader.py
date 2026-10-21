"""
Result Loader Module
--------------------
Loads saved parameter results and component results
for a patient's laboratory report.
"""


def load_saved_results(cursor, patient_id, lab_id):
    """
    Load saved parameter results for a patient.

    Args:
        cursor: Active MySQL database cursor.
        patient_id: Patient ID.
        lab_id: Laboratory ID.

    Returns:
        Dictionary containing saved parameter results,
        indexed by parameter_id.
    """

    cursor.execute("""
        SELECT
            parameter_id,
            component_id,
            section_id,
            parameter_name,
            result_value,
            unit,
            reference_range,
            entry_mode
        FROM test_results
        WHERE patient_id = %s
          AND lab_id = %s
    """, (patient_id, lab_id))

    rows = cursor.fetchall()

    print("\n" + "=" * 60)
    print("[DEBUG] LOAD SAVED RESULTS")
    print("Patient ID:", patient_id)
    print("Lab ID:", lab_id)
    print("Rows found:", len(rows))
    print("Database rows:", rows)
    print("=" * 60 + "\n")

    results = {}

    for row in rows:
        parameter_id = row[0]

        results[parameter_id] = {
            "parameter_name": row[3],
            "result": row[4],
            "unit": row[5],
            "reference_range": row[6],
            "entry_mode": row[7],
            "component_id": row[1],
            "section_id": row[2]
        }

    print("[DEBUG] SAVED RESULTS DICTIONARY:")
    print(results)

    return results


def load_component_results(cursor, patient_id, lab_id):
    """
    Load saved component results for a patient.

    Args:
        cursor: Active MySQL database cursor.
        patient_id: Patient ID.
        lab_id: Laboratory ID.

    Returns:
        Dictionary mapping component_id to result_value.
    """

    cursor.execute("""
        SELECT
            component_id,
            result_value
        FROM report_component_results
        WHERE patient_id = %s
          AND lab_id = %s
    """, (patient_id, lab_id))

    rows = cursor.fetchall()

    print("\n" + "=" * 60)
    print("[DEBUG] LOAD COMPONENT RESULTS")
    print("Patient ID:", patient_id)
    print("Lab ID:", lab_id)
    print("Rows found:", len(rows))
    print("Database rows:", rows)
    print("=" * 60 + "\n")

    results = {}

    for row in rows:
        component_id = row[0]
        results[component_id] = row[1]

    print("[DEBUG] COMPONENT RESULTS DICTIONARY:")
    print(results)

    return results