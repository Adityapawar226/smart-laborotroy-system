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
    "patient_id": row["patient_id"],
    "name": row["name"],
    "age": row["age"],
    "gender": row["gender"],
    "doctor_name": row["doctor_name"],
    "collection_date": row["collected_on"],
    "report_date": row["report_generated_on"],
    "sample_id": row["sample_id"]
}