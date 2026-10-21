from modules.formula_engine import calculate_formula


def calculate_formula_results(
    cursor,
    patient_id,
    lab_id,
    parameter_values
):
    """
    Calculate all formula parameters for the patient's selected tests
    and save them into test_results.
    """

    cursor.execute("""
        SELECT

            pd.id,
            pd.display_name,
            pd.short_name,
            pd.unit,

            rf.formula_expression,

            t.test_name

        FROM parameter_definition pd

        JOIN report_formulas rf
            ON pd.formula_id = rf.id

        JOIN report_components rc
            ON pd.component_id = rc.id

        JOIN test_sections ts
            ON rc.section_id = ts.id

        JOIN tests t
            ON ts.test_id = t.id

        JOIN patient_tests pt
            ON pt.test_id = t.id

        WHERE

            pt.patient_id = %s
            AND pt.lab_id = %s

            AND pd.formula_id IS NOT NULL

            AND pd.status = 'active'

        ORDER BY
            pd.display_order

    """, (patient_id, lab_id))

    formula_parameters = cursor.fetchall()

    for formula in formula_parameters:

        parameter_id = formula[0]
        display_name = formula[1]
        short_name = formula[2]
        unit = formula[3]
        formula_expression = formula[4]
        test_name = formula[5]

        # -----------------------------
        # Calculate Formula
        # -----------------------------

        result = calculate_formula(
            formula_expression,
            parameter_values
        )

        if result is None:
            continue

        # -----------------------------
        # Update parameter dictionary
        # -----------------------------

        parameter_values[display_name] = result

        if short_name:
            parameter_values[short_name] = result

        # -----------------------------
        # Save Formula Result
        # -----------------------------

        cursor.execute("""
            INSERT INTO test_results
            (

                lab_id,

                patient_id,

                test_name,

                parameter_name,

                result_value,

                unit,

                reference_range,

                entry_mode

            )

            VALUES
            (

                %s,

                %s,

                %s,

                %s,

                %s,

                %s,

                %s,

                'Formula'

            )

        """, (

            lab_id,

            patient_id,

            test_name,

            display_name,

            result,

            unit,

            "",

        ))

    return parameter_values