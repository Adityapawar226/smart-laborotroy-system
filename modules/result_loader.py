
"""
Result Loader Module
--------------------
Loads saved parameter results and component results
for a patient's laboratory report.
"""


def load_saved_results(cursor, patient_id, lab_id):
    """
    Load saved parameter results for a patient.

    Returns:
        Dictionary indexed by parameter_id.
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
    print("=" * 60)

    results = {}

    for row in rows:

        parameter_id = row["parameter_id"]

        results[parameter_id] = {
            "parameter_id": parameter_id,
            "component_id": row["component_id"],
            "section_id": row["section_id"],
            "parameter_name": row["parameter_name"],
            "result_value": row["result_value"],
            "unit": row["unit"],
            "reference_range": row["reference_range"],
            "entry_mode": row["entry_mode"]
        }

    print("[DEBUG] SAVED RESULTS DICTIONARY:")
    print(results)
    print("=" * 60 + "\n")

    return results


def load_component_results(cursor, patient_id, lab_id):
    """
    Load saved component results for a patient.

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
    print("=" * 60)

    results = {}

    for row in rows:
        component_id = row["component_id"]
        results[component_id] = row["result_value"]

    print("[DEBUG] COMPONENT RESULTS DICTIONARY:")
    print(results)
    print("=" * 60 + "\n")

    return results

