def load_signatories(
    cursor,
    patient_id,
    lab_id
):
    """
    Load report signatories.
    """

    cursor.execute("""
        SELECT

            p.name,
            p.designation,
            p.signature,

            s.name,
            s.designation,
            s.signature

        FROM reports r

        LEFT JOIN report_signatories p
            ON r.primary_signatory_id = p.id

        LEFT JOIN report_signatories s
            ON r.secondary_signatory_id = s.id

        WHERE
            r.patient_id=%s
            AND r.lab_id=%s
    """, (
        patient_id,
        lab_id
    ))

    row = cursor.fetchone()

    if not row:

        return {

            "primary": None,
            "secondary": None

        }

    return {

        "primary": {

            "name": row[0],
            "designation": row[1],
            "signature": row[2]

        },

        "secondary": {

            "name": row[3],
            "designation": row[4],
            "signature": row[5]

        }

    }