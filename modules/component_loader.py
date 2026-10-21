import json

from modules.dictionary_loader import load_dictionary_values


def _parse_component_content(content):
    """Parse component_content JSON into a dictionary."""
    if isinstance(content, dict):
        return content

    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    return {}


def _format_number(value):
    """Format numbers without unnecessary trailing zeroes."""
    if value is None:
        return ""

    try:
        return f"{float(value):g}"
    except (ValueError, TypeError):
        return str(value)


def _build_reference_range(
    reference_text,
    lower_value,
    upper_value,
    age_from=None,
    age_to=None,
    age_unit=None,
    gender=None,
):
    """
    Build a simple reference-range string.
    Age and gender are deliberately not displayed.
    """
    if lower_value is not None and upper_value is not None:
        return f"{_format_number(lower_value)} - {_format_number(upper_value)}"

    if reference_text and str(reference_text).strip():
        return str(reference_text).strip()

    if lower_value is not None:
        return f">= {_format_number(lower_value)}"

    if upper_value is not None:
        return f"<= {_format_number(upper_value)}"

    return ""


def _load_reference_ranges(cursor, parameter_ids):
    """
    Load active reference ranges for parameter IDs.

    Returns:
        {parameter_id: [range_text, ...]}
    """
    reference_ranges = {parameter_id: [] for parameter_id in parameter_ids}

    if not parameter_ids:
        return reference_ranges

    placeholders = ", ".join(["%s"] * len(parameter_ids))
    query = f"""
        SELECT
            parameter_id,
            gender,
            age_from,
            age_to,
            age_unit,
            lower_value,
            upper_value,
            reference_text,
            interpretation
        FROM parameter_reference_ranges
        WHERE status = 'active'
          AND parameter_id IN ({placeholders})
        ORDER BY parameter_id, age_from, age_to
    """

    cursor.execute(query, tuple(parameter_ids))
    rows = cursor.fetchall()

    for row in rows:
        (
            parameter_id,
            gender,
            age_from,
            age_to,
            age_unit,
            lower_value,
            upper_value,
            reference_text,
            interpretation,
        ) = row

        range_text = _build_reference_range(
            reference_text=reference_text,
            lower_value=lower_value,
            upper_value=upper_value,
            age_from=age_from,
            age_to=age_to,
            age_unit=age_unit,
            gender=gender,
        )

        if range_text:
            reference_ranges.setdefault(parameter_id, []).append(range_text)

    # Remove duplicate strings, preserving order.
    for parameter_id, ranges in reference_ranges.items():
        reference_ranges[parameter_id] = list(dict.fromkeys(ranges))

    return reference_ranges


def _load_parameter_dictionary_id(cursor, parameter_id, component_settings):
    """
    Resolve a parameter's dictionary ID from explicit component settings.

    Supported settings:
      - dictionary_id_<parameter_id>
      - parameter_dictionaries: {"<parameter_id>": dictionary_id}

    Deliberately does not scan arbitrary database tables because that can
    select an unrelated mapping. If your application stores mappings in a
    dedicated table, add that table's exact schema/query here.
    """
    dictionary_id = component_settings.get(f"dictionary_id_{parameter_id}")
    if dictionary_id:
        return dictionary_id

    parameter_dictionaries = component_settings.get("parameter_dictionaries", {})
    if isinstance(parameter_dictionaries, dict):
        dictionary_id = parameter_dictionaries.get(str(parameter_id))
        if dictionary_id is None:
            dictionary_id = parameter_dictionaries.get(parameter_id)

    return dictionary_id


def _safe_load_dictionary_values(cursor, dictionary_id):
    """Load dictionary values without hiding database errors in debug mode."""
    if dictionary_id in (None, ""):
        return []

    try:
        return load_dictionary_values(cursor, dictionary_id) or []
    except Exception as exc:
        print(
            f"[component_loader] Failed loading dictionary "
            f"{dictionary_id!r}: {exc}"
        )
        return []


def load_component(cursor, comp):
    """
    Load one report component, its active parameters, dictionary options,
    and reference ranges.

    Expected component tuple:
        (id, component_name, component_type, component_content)
    """
    if not comp or len(comp) < 4:
        raise ValueError(
            "load_component expected a component row with at least "
            "(id, component_name, component_type, component_content)"
        )

    component_id = comp[0]
    component_name = comp[1]
    component_type = comp[2]
    component_content = comp[3]
    component_settings = _parse_component_content(component_content)

    # Read the dedicated settings table. In this application, settings such as
    # dictionary_id may be stored here rather than only in component_content.
    try:
        cursor.execute(
            """
            SELECT setting_key, setting_value
            FROM report_component_settings
            WHERE component_id = %s
            """,
            (component_id,),
        )
        for setting_key, setting_value in (cursor.fetchall() or []):
            if setting_key:
                component_settings.setdefault(str(setting_key), setting_value)
    except Exception as exc:
        # Keep component_content usable if this installation does not have
        # report_component_settings or the query fails.
        print(
            f"[component_loader] Could not load settings for "
            f"component {component_id}: {exc}"
        )

    component_data = {
        "component_id": component_id,
        "component_name": component_name,
        "component_type": component_type,
        "component_content": component_content,
        "component_settings": component_settings,
        "parameters": [],
        "dropdown_options": [],
        "dictionary_values": [],
        "selected_value": "",
    }

    # 1. Component-level dictionary, e.g. a dictionary_result component.
    component_dictionary_id = component_settings.get("dictionary_id")
    if component_dictionary_id:
        dictionary_values = _safe_load_dictionary_values(
            cursor, component_dictionary_id
        )
        component_data["dropdown_options"] = dictionary_values
        component_data["dictionary_values"] = dictionary_values

    print(
        "[component_loader] Component:",
        component_id,
        "| type:",
        component_type,
        "| settings:",
        component_settings,
        "| dictionary_id:",
        component_settings.get("dictionary_id"),
        "| dictionary_values:",
        component_data["dictionary_values"],
    )

    # 2. Load parameter definitions.
    cursor.execute(
        """
        SELECT
            pd.id,
            pd.parameter_code,
            pd.display_name,
            pd.short_name,
            pd.unit,
            pd.formula_id,
            rf.formula_expression,
            pd.decimal_places,
            pd.data_type,
            pd.reference_type,
            pd.min_range,
            pd.max_range,
            pd.default_value,
            pd.editable,
            pd.optional_field,
            pd.display_order
        FROM parameter_definition pd
        LEFT JOIN report_formulas rf
            ON pd.formula_id = rf.id
        WHERE pd.component_id = %s
          AND pd.status = 'active'
        ORDER BY pd.display_order, pd.id
        """,
        (component_id,),
    )
    rows = cursor.fetchall()

    if not rows:
        return component_data

    parameter_ids = [row[0] for row in rows]
    reference_ranges = _load_reference_ranges(cursor, parameter_ids)
    print(
        "[component_loader] Reference ranges for component",
        component_id,
        ":",
        reference_ranges,
    )

    for row in rows:
        (
            parameter_id,
            parameter_code,
            display_name,
            short_name,
            unit,
            formula_id,
            formula_expression,
            decimal_places,
            data_type,
            reference_type,
            min_range,
            max_range,
            default_value,
            editable,
            optional_field,
            display_order,
        ) = row

        data_type = str(data_type or "numeric").strip().lower()
        reference_type = str(reference_type or "normal").strip().lower()

        if formula_id or data_type == "formula":
            input_type = "formula"
        elif data_type == "list":
            input_type = "dropdown"
        elif data_type == "text":
            input_type = "text"
        else:
            input_type = "numeric"

        # Use the explicit reference ranges first, then min/max fallback.
        parameter_reference_ranges = reference_ranges.get(parameter_id, [])
        if parameter_reference_ranges:
            reference_range = "; ".join(parameter_reference_ranges)
        elif min_range is not None and max_range is not None:
            reference_range = (
                f"{_format_number(min_range)} - {_format_number(max_range)}"
            )
        elif min_range is not None:
            reference_range = f">= {_format_number(min_range)}"
        elif max_range is not None:
            reference_range = f"<= {_format_number(max_range)}"
        else:
            reference_range = ""

        # 3. Parameter-level dictionary. No arbitrary table scanning.
        dropdown_options = []
        dictionary_id = None
        if input_type == "dropdown":
            dictionary_id = _load_parameter_dictionary_id(
                cursor, parameter_id, component_settings
            )
            if dictionary_id:
                dropdown_options = _safe_load_dictionary_values(
                    cursor, dictionary_id
                )

        parameter_data = {
            "id": parameter_id,
            "parameter_id": parameter_id,
            "code": parameter_code or "",
            "parameter_code": parameter_code or "",
            "name": display_name or "",
            "display_name": display_name or "",
            "short_name": short_name or "",
            "unit": unit or "",
            "input_type": input_type,
            "data_type": data_type,
            "reference_type": reference_type,
            "reference_range": reference_range,
            "formula_id": formula_id,
            "formula_expression": formula_expression or "",
            "decimal_places": decimal_places if decimal_places is not None else 2,
            "formula_decimal_places": (
                decimal_places if decimal_places is not None else 2
            ),
            "default_value": default_value if default_value is not None else "",
            "editable": editable,
            "optional_field": optional_field,
            "display_order": display_order,
            "dropdown_options": dropdown_options,
            "result": None,
        }
        component_data["parameters"].append(parameter_data)

    return component_data