def merge_results(report_structure, saved_results, component_results):

    # Normalize component result keys to strings.
    normalized_component_results = {
        str(key): value
        for key, value in (component_results or {}).items()
    }

    for test in report_structure:

        for section in test.get("sections", []):

            for component in section.get("components", []):

                component_type = component.get("component_type")

                # ====================================================
                # DICTIONARY / DROPDOWN RESULT COMPONENT
                # ====================================================

                if component_type in ("dictionary_result", "dictionary"):

                    component_id = component.get(
                        "component_id",
                        component.get("id")
                    )

                    selected_value = normalized_component_results.get(
                        str(component_id), ""
                    )

                    component["selected_value"] = selected_value or ""

                    print(
                        "[REPORT DICTIONARY MERGE]",
                        "Component ID:", component_id,
                        "Component:", component.get("component_name"),
                        "Type:", component_type,
                        "Value:", repr(selected_value)
                    )

                    continue

                # ====================================================
                # PARAMETER COMPONENT
                # ====================================================

                if component_type not in (
                    "parameter",
                    "parameter_table",
                    "formula"
                ):
                    continue

                # ====================================================
                # MERGE SAVED PARAMETERS
                # ====================================================

                for parameter in component.get("parameters", []):

                    parameter_id = parameter.get("parameter_id")

                    if parameter_id is None:
                        continue

                    result = (saved_results or {}).get(parameter_id)

                    if result is None:
                        result = (saved_results or {}).get(str(parameter_id))

                    if result is None:
                        continue

                    parameter["result"] = result.get("result", "")

                    if result.get("unit"):
                        parameter["unit"] = result["unit"]

                    if result.get("reference_range"):
                        parameter["reference_range"] = result["reference_range"]

                    if result.get("reference_text"):
                        parameter["reference_text"] = result["reference_text"]

                    parameter["entry_mode"] = result.get("entry_mode", "")

                    parameter["status"] = "normal"

                    parameter["display_result"] = parameter["result"]

    return report_structure