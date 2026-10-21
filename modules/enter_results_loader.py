from flask import session


from modules.patient_loader import load_patient


def load_patient_tests(cursor, patient_id):
    """
    Load all tests selected for the patient.
    """

    lab_id = session["lab_id"]

    cursor.execute("""
        SELECT
            pt.test_id,
            t.test_name
        FROM patient_tests pt
        JOIN tests t
            ON pt.test_id=t.id
        WHERE pt.patient_id=%s
        AND pt.lab_id=%s
        ORDER BY t.test_name
    """, (patient_id, lab_id))

    return cursor.fetchall()


def load_sections(cursor, test_id):

    cursor.execute("""
        SELECT
            id,
            section_name,
            description
        FROM test_sections
        WHERE test_id=%s
        ORDER BY display_order,id
    """, (test_id,))

    return cursor.fetchall()


def load_components(cursor, section_id):

    cursor.execute("""
        SELECT
            id,
            component_name,
            component_type,
            component_content
        FROM report_components
        WHERE section_id=%s
        AND is_active=1
        ORDER BY display_order,id
    """, (section_id,))

    return cursor.fetchall()