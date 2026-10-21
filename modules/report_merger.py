def merge_results(report_structure, saved_results, component_results):
    for test in report_structure:
        for section in test.get("sections", []):
            for component in section.get("components", []):

                # ====================================================
                # DICTIONARY RESULT COMPONENT
                # ====================================================
                if component.get("component_type") == "dictionary_result":
                    component_id = component.get("component_id")

                    component["selected_value"] = component_results.get(
                        component_id, ""
                    )
                    continue

                # ====================================================
                # PARAMETER COMPONENT
                # ====================================================
                if component.get("component_type") not in (
                    "parameter",
                    "parameter_table",
                ):
                    continue

                # ====================================================
                # MERGE SAVED PARAMETERS
                # ====================================================
                for parameter in component.get("parameters", []):
                    parameter_id = parameter.get("parameter_id")

                    if parameter_id is None:
                        continue

                    # Use the saved result when available.
                    result = saved_results.get(parameter_id)

                    if result is None:
                        continue

                    # Restore result value, including valid values such as 0.
                    parameter["result"] = result.get("result", "")

                    # Restore unit.
                    if result.get("unit"):
                        parameter["unit"] = result["unit"]

                    # Restore reference range.
                    if result.get("reference_range"):
                        parameter["reference_range"] = result["reference_range"]

                    # Restore reference text if available.
                    if result.get("reference_text"):
                        parameter["reference_text"] = result["reference_text"]

                    # Restore entry mode.
                    parameter["entry_mode"] = result.get("entry_mode", "")

                    # Default status.
                    parameter["status"] = "normal"

                    # Value displayed in the report.
                    parameter["display_result"] = parameter["result"]

    return report_structure