def load_patient(cursor, patient_id, lab_id):
    """
    Load patient information along with the sample ID.
    """

    cursor.execute("""
        SELECT
            p.patient_id,
            p.name,
            p.age,
            p.gender,
            p.doctor_name,
            p.collected_on,
            p.report_generated_on,
            s.sample_id
        FROM patients p
        LEFT JOIN samples s
            ON s.patient_id = p.patient_id
            AND s.lab_id = p.lab_id
        WHERE
            p.patient_id = %s
            AND p.lab_id = %s
        ORDER BY s.id DESC
        LIMIT 1
    """, (patient_id, lab_id))

    row = cursor.fetchone()

    if not row:
        return None

    return {
        "patient_id": row[0],
        "name": row[1],
        "age": row[2],
        "gender": row[3],
        "doctor_name": row[4],
        "collection_date": row[5],
        "report_date": row[6],
        "sample_id": row[7]
    }