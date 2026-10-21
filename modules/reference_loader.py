import re


def apply_reference_status(report_structure):
    """
    Compare result against reference range.

    Supported reference formats:

        1. Numeric:
           9 - 19

        2. Quoted numeric:
           "10 - 20"

        3. Multiple classifications:
           Negative : 1-9
           Normal   : 10-20
           Positive : 21-30

    Adds:

        status:
            normal
            high
            low
            negative
            positive
            out_of_range

        display_result:
            ↑ result
            ↓ result
            classification text
    """

    for test in report_structure:

        for section in test.get("sections", []):

            for component in section.get("components", []):

                if component.get("component_type") not in [
                    "parameter",
                    "parameter_table"
                ]:
                    continue

                for parameter in component.get("parameters", []):

                    result = parameter.get("result")
                    reference = parameter.get("reference_range")

                    # -----------------------------------------
                    # DEFAULT
                    # -----------------------------------------

                    parameter["status"] = "normal"
                    parameter["display_result"] = result

                    if result in ("", None):
                        continue

                    if reference in ("", "-", None):
                        continue

                    try:

                        reference = str(reference).strip()

                        # Remove surrounding quotes
                        reference = (
                            reference
                            .strip('"')
                            .strip("'")
                            .strip()
                        )

                        value = float(result)

                        # =================================================
                        # CASE 1:
                        #
                        # Negative : 1-9
                        # Normal   : 10-20
                        # Positive : 21-30
                        # =================================================

                        classification_pattern = re.findall(
                            r'([A-Za-z][A-Za-z\s]*)\s*:\s*(-?\d+(?:\.\d+)?)\s*[-–—]\s*(-?\d+(?:\.\d+)?)',
                            reference
                        )

                        if classification_pattern:

                            matched = False

                            for label, low_text, high_text in classification_pattern:

                                label = label.strip().lower()

                                low = float(low_text)
                                high = float(high_text)

                                if low <= value <= high:

                                    matched = True

                                    # -----------------------------
                                    # Negative
                                    # -----------------------------

                                    if label == "negative":

                                        parameter["status"] = "negative"

                                        parameter["display_result"] = (
                                            f"Negative ({result})"
                                        )

                                    # -----------------------------
                                    # Positive
                                    # -----------------------------

                                    elif label == "positive":

                                        parameter["status"] = "positive"

                                        parameter["display_result"] = (
                                            f"Positive ({result})"
                                        )

                                    # -----------------------------
                                    # Normal
                                    # -----------------------------

                                    elif label == "normal":

                                        parameter["status"] = "normal"

                                        parameter["display_result"] = result

                                    # -----------------------------
                                    # Custom Classification
                                    # -----------------------------

                                    else:

                                        parameter["status"] = label

                                        parameter["display_result"] = (
                                            f"{label.title()} ({result})"
                                        )

                                    break

                            # -----------------------------------------
                            # Value outside all classifications
                            # -----------------------------------------

                            if not matched:

                                parameter["status"] = "out_of_range"

                                parameter["display_result"] = (
                                    f"↑ {result}"
                                )

                            continue

                        # =================================================
                        # CASE 2:
                        #
                        # Normal numeric range
                        #
                        # 9 - 19
                        # "10 - 20"
                        # =================================================

                        match = re.match(
                            r'^\s*(-?\d+(?:\.\d+)?)\s*[-–—]\s*(-?\d+(?:\.\d+)?)\s*$',
                            reference
                        )

                        if not match:
                            continue

                        low = float(match.group(1))
                        high = float(match.group(2))

                        # -----------------------------------------
                        # LOW
                        # -----------------------------------------

                        if value < low:

                            parameter["status"] = "low"

                            parameter["display_result"] = (
                                f"↓ {result}"
                            )

                        # -----------------------------------------
                        # HIGH
                        # -----------------------------------------

                        elif value > high:

                            parameter["status"] = "high"

                            parameter["display_result"] = (
                                f"↑ {result}"
                            )

                        # -----------------------------------------
                        # NORMAL
                        # -----------------------------------------

                        else:

                            parameter["status"] = "normal"

                            parameter["display_result"] = result

                    except (ValueError, TypeError):

                        continue

    return report_structure