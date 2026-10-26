
from modules.enter_results_loader import (
    load_patient_tests,
    load_sections,
    load_components,
)

from modules.component_loader import load_component


def build_report_structure(
    cursor,
    patient_id=None,
    tests=None,
    patient_age=None,
    patient_gender=None,
):
    """
    Build the report structure with patient-specific reference ranges.

    Normal report:
        build_report_structure(
            cursor,
            patient_id=patient_id,
            patient_age=patient_age,
            patient_gender=patient_gender,
        )

    Public QR report:
        build_report_structure(cursor, tests=tests)
    """

    report_structure = []

    # Load patient tests when they are not provided.
    if tests is None and patient_id is not None:
        tests = load_patient_tests(
            cursor,
            patient_id,
        )

    if not tests:
        return report_structure

    # Build the report.
    for test in tests:
        test_id = test[0]
        test_name = test[1]

        test_data = {
            "test_id": test_id,
            "test_name": test_name,
            "sections": [],
        }

        # Load sections belonging to this test.
        sections = load_sections(
            cursor,
            test_id,
        )

        for section in sections:
            section_id = section[0]

            section_data = {
                "section_id": section_id,
                "section_name": section[1],
                "description": section[2],
                "components": [],
            }

            # Load components belonging to this section.
            components = load_components(
                cursor,
                section_id,
            )

            for comp in components:
                component_data = load_component(
                    cursor,
                    comp,
                    patient_age=patient_age,
                    patient_gender=patient_gender,
                )

                section_data["components"].append(
                    component_data
                )

            if section_data["components"]:
                test_data["sections"].append(
                    section_data
                )

        if test_data["sections"]:
            report_structure.append(
                test_data
            )

    return report_structure

