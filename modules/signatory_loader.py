
def load_signatories(cursor, patient_id, lab_id):
    """
    Load report signatories.
    Returns primary and secondary signatory details.
    """

    cursor.execute("""
        SELECT
            p.name AS primary_name,
            p.designation AS primary_designation,
            p.signature AS primary_signature,

            s.name AS secondary_name,
            s.designation AS secondary_designation,
            s.signature AS secondary_signature

        FROM reports r

        LEFT JOIN report_signatories p
            ON r.primary_signatory_id = p.id

        LEFT JOIN report_signatories s
            ON r.secondary_signatory_id = s.id

        WHERE r.patient_id = %s
          AND r.lab_id = %s

        LIMIT 1
    """, (patient_id, lab_id))

    row = cursor.fetchone()

    if not row:
        return {
            "primary": None,
            "secondary": None
        }

    primary = None
    secondary = None

    if row["primary_name"]:
        primary = {
            "name": row["primary_name"],
            "designation": row["primary_designation"],
            "signature": row["primary_signature"]
        }

    if row["secondary_name"]:
        secondary = {
            "name": row["secondary_name"],
            "designation": row["secondary_designation"],
            "signature": row["secondary_signature"]
        }

    return {
        "primary": primary,
        "secondary": secondary
    }
