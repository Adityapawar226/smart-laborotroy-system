from modules.formula_engine import calculate_formula


def calculate_all_formulas(
    cursor,
    patient_id,
    lab_id,
    parameter_values,
    formula_parameters
):
    """
    Calculate formula-based laboratory parameters.

    Supports:
        - Manual parameter values
        - Parameter codes
        - Short names
        - Display names
        - Previously calculated formula results
        - Retrying formulas when dependencies become available

    Returns:
        A list of dictionaries containing calculated results.

    Formula results are calculated here.
    Saving is handled by result_saver.py.
    """

    calculated_results = []

    calculated_parameter_ids = set()

    available_values = dict(parameter_values or {})

    # =========================================================
    # STEP 1: LOAD FORMULA DEFINITIONS
    # =========================================================

    formula_definitions = {}

    for parameter_id, formula_id in formula_parameters.items():

        cursor.execute(
            """
            SELECT
                pd.id AS parameter_id,
                pd.display_name AS display_name,
                pd.short_name AS short_name,
                pd.parameter_code AS parameter_code,
                pd.unit AS unit,
                pd.component_id AS component_id,

                rc.component_name AS component_name,

                ts.id AS section_id,
                ts.section_name AS section_name,

                t.id AS test_id,
                t.test_name AS test_name,

                rf.formula_expression AS formula_expression

            FROM parameter_definition pd

            JOIN report_components rc
                ON pd.component_id = rc.id

            JOIN test_sections ts
                ON rc.section_id = ts.id

            JOIN tests t
                ON ts.test_id = t.id

            JOIN report_formulas rf
                ON pd.formula_id = rf.id

            WHERE
                pd.id = %s
                AND pd.formula_id = %s
                AND pd.status = 'active'
                AND rf.status = 'active'

                AND (
                    t.lab_id = %s
                    OR t.lab_id IS NULL
                )

                AND (
                    pd.lab_id = %s
                    OR pd.lab_id IS NULL
                )

            LIMIT 1
            """,
            (
                parameter_id,
                formula_id,
                lab_id,
                lab_id
            )
        )

        row = cursor.fetchone()

        if not row:

            print(
                "[FORMULA SKIPPED - DEFINITION NOT FOUND]",
                "parameter_id =", parameter_id,
                "formula_id =", formula_id,
                "lab_id =", lab_id
            )

            continue

        print("[FORMULA DEFINITION ROW]", row)

        # DictCursor mapping
        formula_definitions[parameter_id] = {

            "parameter_id": row["parameter_id"],

            "display_name": row["display_name"],

            "short_name": row["short_name"],

            "parameter_code": row["parameter_code"],

            "unit": row["unit"],

            "component_id": row["component_id"],

            "component_name": row["component_name"],

            "section_id": row["section_id"],

            "section_name": row["section_name"],

            "test_id": row["test_id"],

            "test_name": row["test_name"],

            "formula_expression": row["formula_expression"],

            "formula_id": formula_id
        }

    # =========================================================
    # STEP 2: FORMULA SERVICE INITIALIZATION
    # =========================================================

    print("=" * 70)

    print("[FORMULA SERVICE STARTED]")

    print("Patient ID:", patient_id)

    print("Lab ID:", lab_id)

    print(
        "Formula definitions loaded:",
        len(formula_definitions)
    )

    print("Initial parameter values:", available_values)

    print("=" * 70)

    # =========================================================
    # STEP 3: HANDLE FORMULAS IN MULTIPLE PASSES
    # =========================================================

    pending_parameter_ids = list(formula_definitions.keys())

    while pending_parameter_ids:

        progress_made = False

        remaining_parameter_ids = []

        for parameter_id in pending_parameter_ids:

            if parameter_id in calculated_parameter_ids:
                continue

            definition = formula_definitions[parameter_id]

            display_name = definition["display_name"]

            short_name = definition["short_name"]

            parameter_code = definition["parameter_code"]

            formula_expression = definition["formula_expression"]

            print("-" * 70)

            print("[FORMULA DEBUG]")

            print("Patient ID:", patient_id)

            print("Lab ID:", lab_id)

            print("Parameter ID:", parameter_id)

            print("Parameter:", display_name)

            print("Parameter Code:", parameter_code)

            print("Formula ID:", definition["formula_id"])

            print("Formula:", formula_expression)

            # =================================================
            # STEP 4: CALCULATE FORMULA
            # =================================================

            try:

                result = calculate_formula(
                    formula_expression,
                    available_values
                )

            except Exception as error:

                print(
                    "[FORMULA ERROR]",
                    "Parameter:", display_name,
                    "Error:", error
                )

                remaining_parameter_ids.append(parameter_id)

                continue

            # =================================================
            # STEP 5: HANDLE UNSUCCESSFUL CALCULATIONS
            # =================================================

            if result is None:

                print(
                    "[FORMULA PENDING]",
                    "Parameter:", display_name,
                    "Formula:", formula_expression
                )

                remaining_parameter_ids.append(parameter_id)

                continue

            try:

                result = round(float(result), 2)

            except (TypeError, ValueError):

                print(
                    "[INVALID FORMULA RESULT]",
                    "Parameter:", display_name,
                    "Result:", result
                )

                remaining_parameter_ids.append(parameter_id)

                continue

            # =================================================
            # STEP 6: STORE CALCULATED RESULT
            # =================================================

            calculated_results.append(
                {
                    "parameter_id": parameter_id,

                    "component_id": definition["component_id"],

                    "section_id": definition["section_id"],

                    "test_id": definition["test_id"],

                    "test_name": definition["test_name"],

                    "display_name": display_name,

                    "short_name": short_name,

                    "parameter_code": parameter_code,

                    "unit": definition["unit"],

                    "result": result
                }
            )

            calculated_parameter_ids.add(parameter_id)

            progress_made = True

            # =================================================
            # STEP 7: MAKE RESULT AVAILABLE TO OTHER FORMULAS
            # =================================================

            if display_name:
                available_values[display_name] = result

            if short_name:
                available_values[short_name] = result

            if parameter_code:
                available_values[parameter_code] = result

            available_values[f"param_{parameter_id}"] = result

            print(
                "[FORMULA SUCCESS]",
                display_name,
                "=",
                result,
                definition["unit"] or ""
            )

        # =====================================================
        # STEP 8: PREPARE NEXT CALCULATION PASS
        # =====================================================

        if not remaining_parameter_ids:
            break

        if not progress_made:

            print("=" * 70)

            print("[FORMULA PROCESSING STOPPED]")

            print(
                "Some formulas could not be calculated "
                "because their variables are missing or "
                "their expressions are invalid."
            )

            for parameter_id in remaining_parameter_ids:

                definition = formula_definitions[parameter_id]

                print(
                    "[UNRESOLVED FORMULA]",
                    "Parameter ID:", parameter_id,
                    "Parameter:", definition["display_name"],
                    "Formula:", definition["formula_expression"]
                )

            print("=" * 70)

            break

        pending_parameter_ids = remaining_parameter_ids

    # =========================================================
    # STEP 9: RETURN RESULTS
    # =========================================================

    print("=" * 70)

    print("[FORMULA SERVICE COMPLETE]")

    print(
        "Total formulas loaded:",
        len(formula_definitions)
    )

    print(
        "Successfully calculated:",
        len(calculated_results)
    )

    print(
        "Not calculated:",
        len(formula_definitions) - len(calculated_parameter_ids)
    )

    print("=" * 70)

    return calculated_results