from modules.formula_service import calculate_all_formulas


def delete_old_results(cursor, patient_id, lab_id):
    """
    Delete previously saved laboratory results for this patient and lab.

    Call this only when regenerating the report.
    """

    cursor.execute(
        """
        DELETE FROM test_results
        WHERE patient_id = %s
          AND lab_id = %s
        """,
        (patient_id, lab_id)
    )


def save_signatories(
    cursor,
    patient_id,
    lab_id,
    primary_id,
    secondary_id
):
    """
    Save or update report signatories.
    """

    cursor.execute(
        """
        SELECT id
        FROM reports
        WHERE patient_id = %s
          AND lab_id = %s
        """,
        (patient_id, lab_id)
    )

    report = cursor.fetchone()

    if report:

        cursor.execute(
            """
            UPDATE reports
            SET primary_signatory_id = %s,
                secondary_signatory_id = %s
            WHERE patient_id = %s
              AND lab_id = %s
            """,
            (
                primary_id or None,
                secondary_id or None,
                patient_id,
                lab_id
            )
        )

    else:

        cursor.execute(
            """
            INSERT INTO reports (
                lab_id,
                patient_id,
                primary_signatory_id,
                secondary_signatory_id
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                lab_id,
                patient_id,
                primary_id or None,
                secondary_id or None
            )
        )


def save_manual_results(
    cursor,
    patient_id,
    lab_id,
    form
):
    """
    Save manually entered parameter values.

    Formula parameters are not saved manually.

    Returns a dictionary containing the manually entered values,
    indexed by display name, short name, parameter code, and ID.

    The dictionary is passed to the formula service.
    """

    parameter_values = {}

    cursor.execute(
        """
        SELECT
            pd.id,
            pd.parameter_code,
            pd.display_name,
            pd.short_name,
            pd.unit,
            pd.formula_id,
            pd.component_id,
            rc.component_name,
            ts.id,
            ts.section_name,
            t.id,
            t.test_name

        FROM parameter_definition pd

        JOIN report_components rc
            ON pd.component_id = rc.id

        JOIN test_sections ts
            ON rc.section_id = ts.id

        JOIN tests t
            ON ts.test_id = t.id

        JOIN patient_tests pt
            ON pt.test_id = t.id
           AND pt.patient_id = %s
           AND pt.lab_id = %s

        WHERE
            pd.status = 'active'

            AND (
                t.lab_id = %s
                OR t.lab_id IS NULL
            )

            AND (
                pd.lab_id = %s
                OR pd.lab_id IS NULL
            )

        ORDER BY
            t.id,
            ts.display_order,
            rc.display_order,
            pd.display_order
        """,
        (patient_id, lab_id, lab_id, lab_id)
    )

    parameters = cursor.fetchall()

    print("=" * 60)
    print("[MANUAL RESULT PROCESSING]")
    print("Patient ID:", patient_id)
    print("Lab ID:", lab_id)
    print("Parameters loaded:", len(parameters))
    print("=" * 60)

    for p in parameters:

        parameter_id = p[0]
        parameter_code = p[1]
        display_name = p[2]
        short_name = p[3]
        unit = p[4]
        formula_id = p[5]
        component_id = p[6]
        section_id = p[8]
        test_name = p[11]

        # Formula parameters must be calculated separately.
        if formula_id is not None:
            continue

        # Read the submitted value.
        raw_value = form.get(
            f"param_{parameter_id}",
            ""
        )

        if raw_value is None:
            continue

        result = str(raw_value).strip()

        if not result:
            continue

        # Store the value using the parameter's available identifiers.
        if display_name:
            parameter_values[display_name] = result

        if short_name:
            parameter_values[short_name] = result

        if parameter_code:
            parameter_values[parameter_code] = result

        parameter_values[f"param_{parameter_id}"] = result

        print(
            "[MANUAL RESULT]",
            "parameter_id =", parameter_id,
            "code =", parameter_code,
            "name =", display_name,
            "short_name =", short_name,
            "value =", result
        )

        # Save the manually entered result.
        cursor.execute(
            """
            INSERT INTO test_results (
                lab_id,
                patient_id,
                test_name,
                parameter_id,
                component_id,
                section_id,
                parameter_name,
                result_value,
                unit,
                reference_range,
                entry_mode
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                'Manual'
            )
            """,
            (
                lab_id,
                patient_id,
                test_name,
                parameter_id,
                component_id,
                section_id,
                display_name,
                result,
                unit,
                ""
            )
        )

    print("=" * 60)
    print("[PARAMETER VALUES FOR FORMULA]")
    print(parameter_values)
    print("=" * 60)

    return parameter_values


def save_formula_results(
    cursor,
    patient_id,
    lab_id,
    parameter_values
):
    """
    Calculate formula-based parameters and save them into test_results.

    Manual results must be collected before calling this function.

    The function uses calculate_all_formulas() from formula_service.py.
    """

    # Load active formula-based parameter definitions.
    cursor.execute(
        """
        SELECT
            id,
            formula_id

        FROM parameter_definition

        WHERE
            formula_id IS NOT NULL
            AND status = 'active'

            AND (
                lab_id = %s
                OR lab_id IS NULL
            )

        ORDER BY
            display_order,
            id
        """,
        (lab_id,)
    )

    rows = cursor.fetchall()

    formula_parameters = {
        row[0]: row[1]
        for row in rows
    }

    print("=" * 60)
    print("[FORMULA PROCESSING]")
    print("Patient ID:", patient_id)
    print("Lab ID:", lab_id)
    print("Formula parameters found:", len(formula_parameters))
    print("Available input parameters:", parameter_values)
    print("=" * 60)

    # Calculate the formulas.
    calculated_results = calculate_all_formulas(
        cursor,
        patient_id,
        lab_id,
        parameter_values,
        formula_parameters
    )

    saved_count = 0

    # Save each calculated result.
    for result in calculated_results:

        calculated_value = result.get("result")

        if calculated_value is None:
            print(
                "[FORMULA NOT SAVED]",
                result.get("display_name"),
                "has no calculated value."
            )
            continue

        cursor.execute(
            """
            INSERT INTO test_results (
                lab_id,
                patient_id,
                test_name,
                parameter_id,
                component_id,
                section_id,
                parameter_name,
                result_value,
                unit,
                reference_range,
                entry_mode
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                'Formula'
            )
            """,
            (
                lab_id,
                patient_id,
                result["test_name"],
                result["parameter_id"],
                result["component_id"],
                result["section_id"],
                result["display_name"],
                calculated_value,
                result["unit"],
                ""
            )
        )

        saved_count += 1

        print(
            "[FORMULA SAVED]",
            result["display_name"],
            "=",
            calculated_value
        )

    print("=" * 60)
    print("[FORMULA PROCESSING COMPLETE]")
    print("Calculated results returned:", len(calculated_results))
    print("Results inserted:", saved_count)
    print("=" * 60)

    return calculated_results


def save_dictionary_results(
    cursor,
    patient_id,
    lab_id,
    form
):
    """
    Save dictionary-based component results.
    """

    # Remove previous dictionary results for this patient and lab.
    cursor.execute(
        """
        DELETE FROM report_component_results
        WHERE patient_id = %s
          AND lab_id = %s
        """,
        (patient_id, lab_id)
    )

    saved_count = 0

    for key in form:

        if not key.startswith("dictionary_component_"):
            continue

        component_id_text = key.replace(
            "dictionary_component_",
            "",
            1
        )

        try:
            component_id = int(component_id_text)

        except (ValueError, TypeError):
            print(
                "[DICTIONARY ERROR] Invalid component ID:",
                key
            )
            continue

        raw_value = form.get(key, "")

        if raw_value is None:
            continue

        value = str(raw_value).strip()

        if not value:
            continue

        cursor.execute(
            """
            INSERT INTO report_component_results (
                lab_id,
                patient_id,
                component_id,
                result_value
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                lab_id,
                patient_id,
                component_id,
                value
            )
        )

        saved_count += 1

    print(
        "[DICTIONARY RESULTS SAVED]",
        saved_count
    )

    return saved_count