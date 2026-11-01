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

    report_structure = []

    if tests is None and patient_id is not None:
        tests = load_patient_tests(cursor, patient_id)

    if not tests:
        return report_structure

    for test in tests:

        test_id = test["test_id"]
        test_name = test["test_name"]

        test_data = {
            "test_id": test_id,
            "test_name": test_name,
            "sections": []
        }

        sections = load_sections(cursor, test_id)

        for section in sections:

            section_id = section["id"]

            section_data = {
                "section_id": section_id,
                "section_name": section["section_name"],
                "description": section["description"],
                "components": []
            }

            components = load_components(cursor, section_id)

            for comp in components:

                component_data = load_component(
                    cursor,
                    comp,
                    patient_age=patient_age,
                    patient_gender=patient_gender
                )

                section_data["components"].append(component_data)

            if section_data["components"]:
                test_data["sections"].append(section_data)

        if test_data["sections"]:
            report_structure.append(test_data)

    return report_structure