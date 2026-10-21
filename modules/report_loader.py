from modules.enter_results_loader import (
    load_patient_tests,
    load_sections,
    load_components
)
from modules.component_loader import load_component


def build_report_structure(cursor, patient_id=None, tests=None):
    """
    Build complete report structure including tests, sections,
    components, and parameter definitions.
    """

    report_structure = []

    # ============================================================
    # LOAD TESTS
    # ============================================================

    if callable(tests):
        print(
            "WARNING: A function was passed as tests:",
            tests.__name__
        )
        tests = None

    if tests is None and patient_id is not None:
        tests = load_patient_tests(cursor, patient_id)

    print("DEBUG patient_id:", repr(patient_id))
    print("DEBUG tests:", repr(tests))
    print("DEBUG tests type:", type(tests))

    if not tests:
        return report_structure

    # ============================================================
    # BUILD REPORT
    # ============================================================

    for test in tests:

        test_id = test[0]
        test_name = test[1]

        test_data = {
            "test_id": test_id,
            "test_name": test_name,
            "sections": []
        }

        # ========================================================
        # LOAD SECTIONS
        # ========================================================

        sections = load_sections(cursor, test_id)

        for section in sections:

            section_id = section[0]

            section_data = {
                "section_id": section_id,
                "section_name": section[1],
                "description": section[2],
                "components": []
            }

            # ====================================================
            # LOAD COMPONENTS
            # ====================================================

            components = load_components(cursor, section_id)

            for comp in components:

                component_data = load_component(cursor, comp)

                section_data["components"].append(component_data)

            if section_data["components"]:
                test_data["sections"].append(section_data)

        if test_data["sections"]:
            report_structure.append(test_data)

    return report_structure