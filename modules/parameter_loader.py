
def load_parameters(cursor, component_id, component_dictionary=None):
    """
    Load all active parameters belonging to a component.

    Input types:
        - formula: Automatically calculated parameter
        - dropdown: Parameter with dictionary options
        - numeric: Manually entered numeric parameter
        - text: Manually entered text parameter
    """

    if component_dictionary is None:
        component_dictionary = []

    cursor.execute("""
        SELECT
            pd.id,
            pd.parameter_code,
            pd.display_name,
            pd.short_name,
            pd.unit,
            pd.reference_type,
            pd.data_type,
            pd.default_value,
            pd.display_order,
            pd.formula_id,
            pd.decimal_places,
            pd.editable,
            pd.machine_readable,
            rf.formula_name,
            rf.formula_expression,
            rf.decimal_places

        FROM parameter_definition pd

        LEFT JOIN report_formulas rf
            ON pd.formula_id = rf.id

        WHERE
            pd.component_id = %s
            AND pd.status = 'active'

        ORDER BY
            pd.display_order
    """, (component_id,))

    rows = cursor.fetchall()

    parameters = []

    for row in rows:

        # -----------------------------------
        # Extract parameter properties
        # -----------------------------------

        parameter_id = row[0]
        parameter_code = row[1]
        display_name = row[2]
        short_name = row[3]
        unit = row[4]

        reference_type = row[5]
        data_type = row[6]
        default_value = row[7]
        display_order = row[8]

        formula_id = row[9]

        decimal_places = row[10]
        editable = bool(row[11])
        machine_readable = bool(row[12])

        formula_name = row[13]
        formula_expression = row[14]
        formula_decimal_places = row[15]

        # -----------------------------------
        # Decide Input Type
        # -----------------------------------

        if formula_id is not None:
            input_type = "formula"

        elif component_dictionary:
            input_type = "dropdown"

        elif str(data_type or "").strip().lower() in (
            "numeric",
            "number",
            "integer",
            "float"
        ):
            input_type = "numeric"

        else:
            input_type = "text"

        # -----------------------------------
        # Formula parameters are not editable
        # -----------------------------------

        if input_type == "formula":
            editable = False

        # -----------------------------------
        # Build parameter dictionary
        # -----------------------------------

        parameter = {
            "parameter_id": parameter_id,
            "parameter_code": parameter_code,
            "display_name": display_name,
            "short_name": short_name,
            "unit": unit,

            "reference_type": reference_type,
            "data_type": data_type,
            "default_value": default_value,
            "display_order": display_order,

            "formula_id": formula_id,

            "decimal_places": decimal_places,
            "editable": editable,
            "machine_readable": machine_readable,

            "formula_name": formula_name,
            "formula_expression": formula_expression,
            "formula_decimal_places": formula_decimal_places,

            "input_type": input_type,

            "dropdown_options": component_dictionary,

            "reference_range": "",

            "result": ""
        }

        parameters.append(parameter)

    print(
        f"[PARAMETER LOADER] Component ID: {component_id} "
        f"| Parameters Loaded: {len(parameters)}"
    )

    for parameter in parameters:
        print(
            f"[PARAMETER LOADER] "
            f"{parameter['display_name']} "
            f"| Input Type: {parameter['input_type']} "
            f"| Formula ID: {parameter['formula_id']} "
            f"| Editable: {parameter['editable']}"
        )

    return parameters