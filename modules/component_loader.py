
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
    """Build a reference-range string."""
    if lower_value is not None and upper_value is not None:
        return (
            f"{_format_number(lower_value)} - "
            f"{_format_number(upper_value)}"
        )

    if reference_text and str(reference_text).strip():
        return str(reference_text).strip()

    if lower_value is not None:
        return f">= {_format_number(lower_value)}"

    if upper_value is not None:
        return f"<= {_format_number(upper_value)}"

    return ""


def _age_in_range_unit(age_years, age_unit):
    """
    Convert the patient's stored age to the unit used by the range.

    Patient registration currently stores age as an integer in years.
    """
    if age_years is None:
        return None

    try:
        age = float(age_years)
    except (TypeError, ValueError):
        return None

    unit = str(age_unit or "years").strip().lower()

    if unit in {"month", "months", "mon", "m"}:
        return age * 12

    if unit in {"day", "days", "d"}:
        return age * 365.25

    if unit in {"week", "weeks", "wk", "w"}:
        return age * 52.1775

    # Default: years
    return age


def _gender_matches(range_gender, patient_gender):
    """
    Return (matches, specificity).

    Gender-specific matches receive higher priority than general ranges.
    """
    range_value = str(range_gender or "all").strip().lower()
    patient_value = str(patient_gender or "").strip().lower()

    general_values = {
        "",
        "all",
        "any",
        "both",
        "unisex",
        "male/female",
        "all genders",
    }

    if range_value in general_values:
        return True, 0

    if not patient_value:
        return False, 0

    if range_value == patient_value:
        return True, 1

    return False, 0


def _load_reference_ranges(
    cursor,
    parameter_ids,
    patient_age=None,
    patient_gender=None,
):
    """
    Select one applicable active reference range per parameter.

    Priority:
      1. Match the patient's gender and age.
      2. Prefer gender-specific ranges over general ranges.
      3. Prefer the narrowest applicable age interval.
    """
    selected = {
        parameter_id: None
        for parameter_id in parameter_ids
    }

    if not parameter_ids:
        return selected

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
        WHERE LOWER(status) = 'active'
          AND parameter_id IN ({placeholders})
        ORDER BY parameter_id, age_from, age_to
    """

    cursor.execute(query, tuple(parameter_ids))
    rows = cursor.fetchall() or []

    candidates = {
        parameter_id: []
        for parameter_id in parameter_ids
    }

    for row in rows:
        (
            parameter_id,
            range_gender,
            age_from,
            age_to,
            age_unit,
            lower_value,
            upper_value,
            reference_text,
            interpretation,
        ) = row

        gender_match, gender_specificity = _gender_matches(
            range_gender,
            patient_gender,
        )

        if not gender_match:
            continue

        age_value = _age_in_range_unit(
            patient_age,
            age_unit,
        )

        # If the patient has an age, enforce the configured boundaries.
        if age_value is not None:
            if age_from is not None and age_value < float(age_from):
                continue

            if age_to is not None and age_value > float(age_to):
                continue

        # If age is unknown, do not choose an age-restricted range.
        elif age_from is not None or age_to is not None:
            continue

        range_text = _build_reference_range(
            reference_text=reference_text,
            lower_value=lower_value,
            upper_value=upper_value,
        )

        if not range_text:
            continue

        # Prefer narrower intervals when both age boundaries exist.
        if age_from is not None and age_to is not None:
            age_span = float(age_to) - float(age_from)
        else:
            age_span = float("inf")

        candidates.setdefault(parameter_id, []).append(
            (
                gender_specificity,
                age_span,
                range_text,
                lower_value,
                upper_value,
                interpretation,
            )
        )

    # Choose the single best applicable range.
    for parameter_id, options in candidates.items():
        if not options:
            continue

        options.sort(
            key=lambda item: (
                -item[0],
                item[1],
            )
        )

        best = options[0]

        selected[parameter_id] = {
            "text": best[2],
            "lower_value": best[3],
            "upper_value": best[4],
            "interpretation": best[5],
        }

    return selected


def _load_parameter_dictionary_id(
    cursor,
    parameter_id,
    component_settings,
):
    """Resolve a parameter's dictionary ID from explicit settings."""
    dictionary_id = component_settings.get(
        f"dictionary_id_{parameter_id}"
    )

    if dictionary_id:
        return dictionary_id

    parameter_dictionaries = component_settings.get(
        "parameter_dictionaries",
        {},
    )

    if isinstance(parameter_dictionaries, dict):
        dictionary_id = parameter_dictionaries.get(
            str(parameter_id)
        )

        if dictionary_id is None:
            dictionary_id = parameter_dictionaries.get(
                parameter_id
            )

    return dictionary_id


def _safe_load_dictionary_values(cursor, dictionary_id):
    """Load dictionary values safely."""
    if dictionary_id in (None, ""):
        return []

    try:
        return load_dictionary_values(
            cursor,
            dictionary_id,
        ) or []

    except Exception as exc:
        print(
            "[component_loader] Failed loading dictionary "
            f"{dictionary_id!r}: {exc}"
        )
        return []


def load_component(
    cursor,
    comp,
    patient_age=None,
    patient_gender=None,
):
    """
    Load a report component and select reference ranges for this patient.

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

    component_settings = _parse_component_content(
        component_content
    )

    # Load additional component settings.
    try:
        cursor.execute(
            """
            SELECT setting_key, setting_value
            FROM report_component_settings
            WHERE component_id = %s
            """,
            (component_id,),
        )

        for setting_key, setting_value in cursor.fetchall() or []:
            if setting_key:
                component_settings.setdefault(
                    str(setting_key),
                    setting_value,
                )

    except Exception as exc:
        print(
            "[component_loader] Could not load settings for "
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

    # Component-level dictionary.
    component_dictionary_id = component_settings.get(
        "dictionary_id"
    )

    if component_dictionary_id:
        dictionary_values = _safe_load_dictionary_values(
            cursor,
            component_dictionary_id,
        )

        component_data["dropdown_options"] = dictionary_values
        component_data["dictionary_values"] = dictionary_values

    # Load parameter definitions.
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

    parameter_ids = [
        row[0]
        for row in rows
    ]

    reference_ranges = _load_reference_ranges(
        cursor,
        parameter_ids,
        patient_age,
        patient_gender,
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

        data_type = str(
            data_type or "numeric"
        ).strip().lower()

        reference_type = str(
            reference_type or "normal"
        ).strip().lower()

        if formula_id or data_type == "formula":
            input_type = "formula"

        elif data_type == "list":
            input_type = "dropdown"

        elif data_type == "text":
            input_type = "text"

        else:
            input_type = "numeric"

        # Use the selected patient-specific range first.
        selected_reference = reference_ranges.get(
            parameter_id
        )

        if selected_reference:
            reference_range = selected_reference["text"]

        elif min_range is not None and max_range is not None:
            reference_range = (
                f"{_format_number(min_range)} - "
                f"{_format_number(max_range)}"
            )

        elif min_range is not None:
            reference_range = f">= {_format_number(min_range)}"

        elif max_range is not None:
            reference_range = f"<= {_format_number(max_range)}"

        else:
            reference_range = ""

        # Parameter-level dictionary options.
        dropdown_options = []

        if input_type == "dropdown":
            dictionary_id = _load_parameter_dictionary_id(
                cursor,
                parameter_id,
                component_settings,
            )

            if dictionary_id:
                dropdown_options = _safe_load_dictionary_values(
                    cursor,
                    dictionary_id,
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

            # Keep numeric bounds available for result interpretation.
            "reference_lower": (
                selected_reference["lower_value"]
                if selected_reference
                else min_range
            ),
            "reference_upper": (
                selected_reference["upper_value"]
                if selected_reference
                else max_range
            ),
            "reference_interpretation": (
                selected_reference["interpretation"]
                if selected_reference
                else ""
            ),

            "formula_id": formula_id,
            "formula_expression": formula_expression or "",
            "decimal_places": (
                decimal_places
                if decimal_places is not None
                else 2
            ),
            "formula_decimal_places": (
                decimal_places
                if decimal_places is not None
                else 2
            ),
            "default_value": (
                default_value
                if default_value is not None
                else ""
            ),
            "editable": editable,
            "optional_field": optional_field,
            "display_order": display_order,
            "dropdown_options": dropdown_options,
            "result": None,
        }

        component_data["parameters"].append(
            parameter_data
        )

    return component_data

