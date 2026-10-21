def load_parameters(cursor, component_id, component_dictionary=None):
    """
    Load all parameters belonging to a component.
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

        # -----------------------------
        # Decide Input Type
        # -----------------------------

        if row[9]:
            input_type = "formula"

        elif component_dictionary:
            input_type = "dropdown"

        else:
            input_type = "text"

        parameter = {

            "parameter_id": row[0],
            "parameter_code": row[1],
            "display_name": row[2],
            "short_name": row[3],
            "unit": row[4],

            "reference_type": row[5],
            "data_type": row[6],
            "default_value": row[7],
            "display_order": row[8],

            "formula_id": row[9],

            "decimal_places": row[10],
            "editable": bool(row[11]),
            "machine_readable": bool(row[12]),

            "formula_name": row[13],
            "formula_expression": row[14],
            "formula_decimal_places": row[15],

            "input_type": input_type,

            "dropdown_options": component_dictionary,

            "reference_range": "",

            "result": ""

        }

        parameters.append(parameter)

    return parameters