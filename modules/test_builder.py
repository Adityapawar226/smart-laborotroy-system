from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)
import json
from pathlib import Path

from flask import (
    request,
    redirect,
    url_for,
    render_template,
    flash,
    session,
    current_app
)
from modules.formula_engine import calculate_formula
from decimal import Decimal
import mysql.connector
import os
from dotenv import load_dotenv
from flask import redirect, url_for

load_dotenv()

test_builder_bp = Blueprint(
    "test_builder",
    __name__,
    template_folder="../templates/test_builder"
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_SSL_CA = PROJECT_ROOT / "aiven-ca.pem"
def get_db():
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "15054")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        ssl_ca=str(DB_SSL_CA),
        ssl_verify_cert=True,
        ssl_verify_identity=True,
        connection_timeout=15
    )
    
def can_access_lab(target_lab_id, allow_global=True):
    """
    Check whether the logged-in user can access data
    belonging to target_lab_id.

    Developer:
        Can access every lab.

    Lab user:
        Can access only their own lab.
        Global data (lab_id=None) can also be accessed
        when allow_global=True.
    """

    role = session.get("role")
    current_lab_id = session.get("lab_id")

    if role == "Developer":
        return True

    if target_lab_id == current_lab_id:
        return True

    if allow_global and target_lab_id is None:
        return True

    return False


@test_builder_bp.route("/configure-test/<int:test_id>")
def configure_test(test_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                id,
                test_name,
                lab_id
            FROM tests
            WHERE id=%s
              AND (
                  %s = 'Developer'
                  OR lab_id=%s
                  OR lab_id IS NULL
              )
        """, (
            test_id,
            session.get("role"),
            session["lab_id"]
        ))

        test = cursor.fetchone()

        if not test:

            flash(
                "Test not found or access denied.",
                "danger"
            )

            return redirect(
                url_for(
                    "test_builder.department_tests",
                    department_id=request.args.get(
                        "department_id",
                        1
                    )
                )
            )

        cursor.execute("""
            SELECT id
            FROM test_sections
            WHERE test_id=%s
            ORDER BY display_order,id
            LIMIT 1
        """, (test_id,))

        section = cursor.fetchone()

        if not section:

            flash(
                "No section found for this test.",
                "warning"
            )

            return redirect(
                url_for(
                    "test_builder.department_tests",
                    department_id=request.args.get(
                        "department_id",
                        1
                    )
                )
            )

        section_id = section["id"]

        return redirect(
            url_for(
                "test_builder.component_list",
                section_id=section_id
            )
        )

    finally:

        cursor.close()
        db.close()

    ############################################################
# ADD SECTION
############################################################

@test_builder_bp.route("/add-section/<int:test_id>", methods=["POST"])
def add_section(test_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                id,
                lab_id
            FROM tests
            WHERE id=%s
              AND (
                  %s = 'Developer'
                  OR lab_id=%s
              )
        """, (
            test_id,
            session.get("role"),
            session["lab_id"]
        ))

        test = cursor.fetchone()

        if not test:

            flash(
                "Test not found or access denied.",
                "danger"
            )

            return redirect(
                url_for("test_builder.configure_test_list")
            )

        cursor.execute("""
            INSERT INTO test_sections
            (
                test_id,
                lab_id,
                section_name,
                description,
                display_order
            )
            VALUES
            (
                %s,%s,%s,%s,%s
            )
        """, (
            test_id,
            test["lab_id"],
            request.form["section_name"],
            request.form.get("description"),
            request.form.get("display_order", 1)
        ))

        db.commit()

        flash(
            "Section added successfully.",
            "success"
        )

        return redirect(
            url_for(
                "test_builder.configure_single_test",
                test_id=test_id
            )
        )

    finally:

        cursor.close()
        db.close()
    ############################################################
# COMPONENT LIST
############################################################

@test_builder_bp.route("/components/<int:section_id>")
def component_list(section_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                ts.*,
                t.test_name,
                t.lab_id AS test_lab_id
            FROM test_sections ts
            JOIN tests t
                ON ts.test_id=t.id
            WHERE ts.id=%s
              AND (
                  %s = 'Developer'
                  OR t.lab_id=%s
                  OR t.lab_id IS NULL
              )
        """, (
            section_id,
            session.get("role"),
            session["lab_id"]
        ))

        section = cursor.fetchone()

        if not section:

            flash(
                "Section not found or access denied.",
                "danger"
            )

            return redirect(
                url_for(
                    "test_builder.configure_test_list"
                )
            )

        cursor.execute("""
            SELECT *
            FROM report_components
            WHERE section_id=%s
            ORDER BY display_order,id
        """, (section_id,))

        components = cursor.fetchall()

        return render_template(
            "test_builder/components.html",
            section=section,
            components=components
        )

    finally:

        cursor.close()
        db.close()
    ############################################################
# ADD COMPONENT
############################################################

############################################################
# ADD COMPONENT
############################################################
@test_builder_bp.route("/components/add/<int:section_id>", methods=["GET", "POST"])
def add_component(section_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # -------------------------------------------------
    # Get Section Details
    # -------------------------------------------------
    cursor.execute("""
    SELECT
        ts.*,
        t.test_name,
        t.lab_id AS test_lab_id
    FROM test_sections ts
    JOIN tests t
        ON ts.test_id = t.id
    WHERE ts.id = %s
      AND (
          %s = 'Developer'
          OR t.lab_id = %s
          OR t.lab_id IS NULL
      )
""", (
    section_id,
    session.get("role"),
    session["lab_id"]
))

    section = cursor.fetchone()

    if not section:
        flash("Section not found.", "danger")
        cursor.close()
        db.close()
        return redirect(url_for("test_builder.configure_test_list"))

    # -------------------------------------------------
    # SAVE COMPONENT
    # -------------------------------------------------
    if request.method == "POST":

        component_name = request.form["component_name"].strip()
        component_type = request.form["component_type"].strip()
        display_order = request.form.get("display_order", 1)

        component_content = ""

        # ---------------------------------------------
        # Component Content
        # ---------------------------------------------

        if component_type == "heading":

            component_content = request.form.get(
                "heading_text",
                ""
            )

        elif component_type in ["paragraph", "interpretation"]:

            mode = request.form.get("mode", "static")

            if mode == "static":
                component_content = request.form.get(
                    "paragraph_text",
                    ""
                )

        elif component_type == "formula":

            component_content = request.form.get(
                "formula_text",
                ""
            )

        # ---------------------------------------------
        # Save Component
        # ---------------------------------------------

        cursor.execute("""
            INSERT INTO report_components
            (
                test_id,
                section_id,
                component_name,
                component_type,
                component_content,
                display_order,
                is_required,
                is_active
            )
            VALUES
            (
                %s,%s,%s,%s,%s,%s,1,1
            )
        """, (

            section["test_id"],
            section_id,
            component_name,
            component_type,
            component_content,
            display_order

        ))

        db.commit()

        component_id = cursor.lastrowid
        # ======================================================
# DICTIONARY RESULT
# ======================================================

        if component_type == "dictionary_result":

    # Create Dictionary
         cursor.execute("""
        INSERT INTO report_dictionaries
        (
            dictionary_name,
            description
        )
        VALUES
        (%s,%s)
    """, (

        component_name,
        "Auto Generated"

    ))

        dictionary_id = cursor.lastrowid

    # Save Dictionary Values
        values = request.form.getlist("dictionary_values[]")

        order = 1

        for value in values:

         value = value.strip()

         if value:

            cursor.execute("""
                INSERT INTO report_dictionary_values
                (
                    dictionary_id,
                    value_text,
                    display_order
                )
                VALUES
                (%s,%s,%s)
            """, (

                dictionary_id,
                value,
                order

            ))

            order += 1

    # Link Component -> Dictionary
        cursor.execute("""
        INSERT INTO report_component_settings
        (
            component_id,
            setting_key,
            setting_value
        )
        VALUES
        (%s,%s,%s)
    """, (

        component_id,
        "dictionary_id",
        str(dictionary_id)

    ))

        db.commit()

        # ======================================================
        # SAVE COMPONENT SETTINGS
        # ======================================================

        if component_type == "heading":

            cursor.execute("""
                INSERT INTO report_component_settings
                (
                    component_id,
                    setting_key,
                    setting_value
                )
                VALUES
                (%s,%s,%s)
            """, (

                component_id,
                "alignment",
                request.form.get(
                    "alignment",
                    "left"
                )

            ))

        elif component_type in ["paragraph", "interpretation"]:

            mode = request.form.get(
                "mode",
                "static"
            )

            cursor.execute("""
                INSERT INTO report_component_settings
                (
                    component_id,
                    setting_key,
                    setting_value
                )
                VALUES
                (%s,%s,%s)
            """, (

                component_id,
                "mode",
                mode

            ))

            if mode == "dictionary":

                dictionary_id = request.form.get("dictionary_id")

                if dictionary_id:

                    cursor.execute("""
                        INSERT INTO report_component_settings
                        (
                            component_id,
                            setting_key,
                            setting_value
                        )
                        VALUES
                        (%s,%s,%s)
                    """, (

                        component_id,
                        "dictionary_id",
                        dictionary_id

                    ))

        db.commit()

        cursor.close()
        db.close()

        # ---------------------------------------------
        # Redirect
        # ---------------------------------------------

        if component_type == "parameter_table":

            return redirect(
                url_for(
                    "test_builder.parameter_list",
                    component_id=component_id
                )
            )

        return redirect(
            url_for(
                "test_builder.component_list",
                section_id=section_id
            )
        )

    # -------------------------------------------------
    # GET PAGE
    # -------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            dictionary_name
        FROM report_dictionaries
        ORDER BY dictionary_name
    """)

    dictionaries = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "test_builder/add_component.html",
        section=section,
        dictionaries=dictionaries
    )
@test_builder_bp.route("/parameters/add/<int:component_id>", methods=["GET", "POST"])
def add_parameter(component_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # -------------------------------------------------
    # Load Component Information
    # -------------------------------------------------

    cursor.execute("""
        SELECT
            rc.*,
            ts.section_name,
            t.test_name,
            t.lab_id AS test_lab_id
        FROM report_components rc
        JOIN test_sections ts
            ON rc.section_id = ts.id
        JOIN tests t
            ON rc.test_id = t.id
        WHERE rc.id = %s
          AND (
    %s = 'Developer'
    OR t.lab_id = %s
    OR t.lab_id IS NULL
)
    """, (
        component_id,
         session.get("role"),
         session["lab_id"]
    ))

    component = cursor.fetchone()

    if not component:
        flash("Component not found or access denied.", "danger")
        cursor.close()
        db.close()

        return redirect(
            url_for("test_builder.configure_test_list")
        )

    # -------------------------------------------------
    # SAVE PARAMETER
    # -------------------------------------------------

    if request.method == "POST":

        display_name = request.form["display_name"].strip()
        short_name = request.form.get("short_name")
        unit = request.form.get("unit")
        method = request.form.get("method")

        reference_type = request.form.get(
            "reference_type",
            "normal"
        )

        data_type = request.form.get(
            "data_type",
            "numeric"
        )

        display_order = request.form.get(
            "display_order",
            1
        )

        editable = 1 if request.form.get("editable") else 0
        optional_field = 1 if request.form.get("optional_field") else 0
        highlight_abnormal = (
            1 if request.form.get("highlight_abnormal") else 0
        )
        machine_readable = (
            1 if request.form.get("machine_readable") else 0
        )

        # ---------------------------------------------
        # Generate Parameter Code
        # ---------------------------------------------

        parameter_code = (
            display_name
            .upper()
            .replace(" ", "_")
            .replace("-", "_")
        )

        # ---------------------------------------------
        # Check Duplicate Parameter
        # ---------------------------------------------

        cursor.execute("""
            SELECT id
            FROM parameter_definition
            WHERE lab_id <=> %s
              AND parameter_code = %s
            LIMIT 1
        """, (
            component["test_lab_id"],
            parameter_code
        ))

        existing_parameter = cursor.fetchone()

        if existing_parameter:

            flash(
                f"Parameter '{display_name}' already exists in this lab.",
                "warning"
            )

            cursor.close()
            db.close()

            return redirect(
                url_for(
                    "test_builder.parameter_list",
                    component_id=component_id
                )
            )

        # ---------------------------------------------
        # Formula
        # ---------------------------------------------

        formula_id = request.form.get("formula_id")

        if formula_id == "":
            formula_id = None

        # ---------------------------------------------
        # Insert Parameter
        # ---------------------------------------------

        cursor.execute("""
            INSERT INTO parameter_definition
            (
                component_id,
                lab_id,
                parameter_code,
                display_name,
                short_name,
                unit,
                method,
                formula_id,
                reference_type,
                data_type,
                editable,
                optional_field,
                highlight_abnormal,
                machine_readable,
                display_order
            )
            VALUES
            (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
        """, (
            component_id,
            component["test_lab_id"],
            parameter_code,
            display_name,
            short_name,
            unit,
            method,
            formula_id,
            reference_type,
            data_type,
            editable,
            optional_field,
            highlight_abnormal,
            machine_readable,
            display_order
        ))

        db.commit()

        parameter_id = cursor.lastrowid

        # ---------------------------------------------
        # Save Dropdown Values
        # ---------------------------------------------

        if reference_type == "list" or data_type == "list":

            options = request.form.getlist(
                "option_values[]"
            )

            order = 1

            for option in options:

                option = option.strip()

                if option:

                    cursor.execute("""
                        INSERT INTO parameter_dropdown_options
                        (
                            parameter_id,
                            option_value,
                            display_order
                        )
                        VALUES
                        (
                            %s, %s, %s
                        )
                    """, (
                        parameter_id,
                        option,
                        order
                    ))

                    order += 1

        db.commit()

        flash(
            "Parameter added successfully.",
            "success"
        )

        cursor.close()
        db.close()

        return redirect(
            url_for(
                "test_builder.parameter_list",
                component_id=component_id
            )
        )

    # -------------------------------------------------
    # SHOW FORM
    # -------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            formula_name
        FROM report_formulas
        WHERE status = 'active'
        ORDER BY formula_name
    """)

    formulas = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "test_builder/add_parameter.html",
        component=component,
        formulas=formulas
    )


############################################################
# PARAMETER LIST
############################################################

@test_builder_bp.route("/parameters/<int:component_id>")
def parameter_list(component_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # -------------------------------------------------
    # Load Component Information
    # -------------------------------------------------

    cursor.execute("""
        SELECT
            rc.*,
            ts.section_name,
            t.test_name,
            t.lab_id AS test_lab_id
        FROM report_components rc
        JOIN test_sections ts
            ON rc.section_id = ts.id
        JOIN tests t
            ON rc.test_id = t.id
        WHERE rc.id = %s
          AND (
    %s = 'Developer'
    OR t.lab_id = %s
    OR t.lab_id IS NULL
)
    """, (
        component_id,
        session.get("role"),
        session["lab_id"]
    ))

    component = cursor.fetchone()

    if not component:

        flash(
            "Component not found or access denied.",
            "danger"
        )

        cursor.close()
        db.close()

        return redirect(
            url_for("test_builder.configure_test_list")
        )

    # -------------------------------------------------
    # Load Parameters
    # -------------------------------------------------

    cursor.execute("""
        SELECT *
        FROM parameter_definition
        WHERE component_id = %s
          AND lab_id <=> %s
        ORDER BY display_order, id
    """, (
        component_id,
        component["test_lab_id"]
    ))

    parameters = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "test_builder/parameter_builder.html",
        component=component,
        parameters=parameters
    )
  


    ########################################################
# Reference Range List
########################################################

@test_builder_bp.route("/reference-ranges/<int:parameter_id>")
def reference_range_list(parameter_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Parameter Details
    cursor.execute("""
    SELECT
        pd.*,
        rc.component_name,
        ts.section_name,
        t.test_name,
        t.lab_id AS test_lab_id
    FROM parameter_definition pd
    JOIN report_components rc
        ON pd.component_id = rc.id
    JOIN test_sections ts
        ON rc.section_id = ts.id
    JOIN tests t
        ON rc.test_id = t.id
    WHERE pd.id = %s
      AND (
          %s = 'Developer'
          OR t.lab_id = %s
          OR t.lab_id IS NULL
      )
""", (
    parameter_id,
    session.get("role"),
    session["lab_id"]
))

    parameter = cursor.fetchone()

    # Reference Ranges
    cursor.execute("""
        SELECT *
        FROM parameter_reference_ranges
        WHERE parameter_id=%s
        ORDER BY age_from
    """, (parameter_id,))

    ranges = cursor.fetchall()
    for r in ranges:
     print(r)
    for r in ranges:
     for field in [
        "lower_value",
        "upper_value",
        "critical_low",
        "critical_high"
    ]:
        if r[field] is not None:
            r[field] = format(r[field].normalize(), "f")
    cursor.close()
    db.close()

    return render_template(
        "test_builder/reference_ranges.html",
        parameter=parameter,
        ranges=ranges
    )
    
    ########################################################
# Add Reference Range
########################################################

@test_builder_bp.route(
    "/reference-ranges/add/<int:parameter_id>",
    methods=["GET", "POST"]
)
def add_reference_range(parameter_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Get Parameter Details
    cursor.execute("""
    SELECT
        pd.*,
        rc.component_name,
        ts.section_name,
        t.test_name,
        t.lab_id AS test_lab_id
    FROM parameter_definition pd
    JOIN report_components rc
        ON pd.component_id = rc.id
    JOIN test_sections ts
        ON rc.section_id = ts.id
    JOIN tests t
        ON rc.test_id = t.id
    WHERE pd.id = %s
      AND (
          %s = 'Developer'
          OR t.lab_id = %s
      )
""", (
    parameter_id,
    session.get("role"),
    session["lab_id"]
))

    parameter = cursor.fetchone()

    if not parameter:
        flash("Parameter not found.", "danger")
        cursor.close()
        db.close()
        return redirect(url_for("test_builder.configure_test_list"))

    if request.method == "POST":

        # Convert form value to Decimal
        def decimal_or_none(value):
            value = (value or "").strip()
            return Decimal(value) if value else None

        lower_value = decimal_or_none(request.form.get("lower_value"))
        upper_value = decimal_or_none(request.form.get("upper_value"))
        critical_low = decimal_or_none(request.form.get("critical_low"))
        critical_high = decimal_or_none(request.form.get("critical_high"))
        age_from = decimal_or_none(request.form.get("age_from"))
        age_to = decimal_or_none(request.form.get("age_to"))

        reference_text = request.form.get("reference_text", "").strip() or None
        interpretation = request.form.get("interpretation", "").strip() or None

        cursor.execute("""
            INSERT INTO parameter_reference_ranges
            (
                parameter_id,
                gender,
                age_from,
                age_to,
                age_unit,
                lower_value,
                upper_value,
                critical_low,
                critical_high,
                reference_text,
                interpretation
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            parameter_id,
            request.form["gender"],
            age_from,
            age_to,
            request.form["age_unit"],
            lower_value,
            upper_value,
            critical_low,
            critical_high,
            reference_text,
            interpretation
        ))

        db.commit()

        flash("Reference range added successfully.", "success")
         
        cursor.close()
        db.close()

        return redirect(
            url_for(
                "test_builder.reference_range_list",
                parameter_id=parameter_id
            )
        )

    cursor.close()
    db.close()

    return render_template(
        "test_builder/add_reference_range.html",
        parameter=parameter
    )
@test_builder_bp.route("/departments")
def department_list():

   db = get_db()
   cursor = db.cursor(dictionary=True)

   cursor.execute("""
    SELECT
        d.id,
        d.department_name,
        d.department_code,
        COUNT(t.id) AS total_tests
    FROM departments d
    LEFT JOIN tests t
        ON t.department_id = d.id
    GROUP BY d.id, d.department_name, d.department_code
    ORDER BY d.department_name
""")

   departments = cursor.fetchall()

   print(departments)
   cursor.close()
   db.close()
    

   return render_template(
        "test_builder/departments.html",
        departments=departments
    )
@test_builder_bp.route("/department-tests/<int:department_id>")
def department_tests(department_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        role = session.get("role")
        lab_code = session.get("lab_id")
        numeric_lab_id = None

        # --------------------------------------------------
        # GET LOGGED-IN LABORATORY'S NUMERIC ID
        # --------------------------------------------------

        if role != "Developer":

            cursor.execute("""
                SELECT id
                FROM laboratories
                WHERE lab_id = %s
            """, (lab_code,))

            lab_row = cursor.fetchone()

            if not lab_row:
                flash("Laboratory not found.", "danger")
                return redirect(url_for("login"))

            numeric_lab_id = lab_row["id"]

        # --------------------------------------------------
        # GET DEPARTMENT
        # --------------------------------------------------

        cursor.execute("""
            SELECT *
            FROM departments
            WHERE id = %s
        """, (department_id,))

        department = cursor.fetchone()

        if not department:
            flash("Department not found.", "danger")
            return redirect(
                url_for("test_builder.department_list")
            )

        # --------------------------------------------------
        # FILTER VALUES
        # --------------------------------------------------

        creator_filter = request.args.get("creator", "all")
        lab_filter = request.args.get("lab_id", "all")
        status_filter = request.args.get("status", "all")

        # --------------------------------------------------
        # BASE QUERY
        #
        # display_price:
        #   Lab-specific override if available
        #   Otherwise the original master price
        #
        # Developer sees master price.
        # --------------------------------------------------

        query = """
            SELECT
                t.*,

                l.lab_name AS laboratory_name,

                CASE
                    WHEN t.lab_id IS NULL
                        THEN 'Developer'
                    ELSE 'Laboratory'
                END AS creator_type,

                CASE
                    WHEN %s = 'Developer'
                        THEN t.price
                    ELSE COALESCE(lto.price, t.price)
                END AS display_price

            FROM tests t

            LEFT JOIN laboratories l
                ON l.lab_id = t.lab_id

            LEFT JOIN lab_test_overrides lto
                ON lto.test_id = t.id
               AND lto.lab_id = %s
               AND t.lab_id IS NULL

            WHERE t.department_id = %s
        """

        params = [
            role,
            numeric_lab_id if numeric_lab_id is not None else 0,
            department_id
        ]

        # --------------------------------------------------
        # ACCESS CONTROL AND FILTERS
        # --------------------------------------------------

        if role == "Developer":

            if creator_filter == "developer":
                query += """
                    AND t.lab_id IS NULL
                """

            elif creator_filter == "laboratory":
                query += """
                    AND t.lab_id IS NOT NULL
                """

            if lab_filter != "all":
                query += """
                    AND t.lab_id = %s
                """
                params.append(lab_filter)

            if status_filter in ("Active", "Inactive"):
                query += """
                    AND t.status = %s
                """
                params.append(status_filter)

            # Laboratory options for Developer
            cursor.execute("""
                SELECT lab_id, lab_name
                FROM laboratories
                ORDER BY lab_name
            """)

            laboratories = cursor.fetchall()

        else:

            # Laboratory users see only their own tests
            # and Developer-created global tests.
            query += """
                AND (
                    t.lab_id = %s
                    OR t.lab_id IS NULL
                )
            """

            params.append(lab_code)

            laboratories = []

        # --------------------------------------------------
        # ORDER AND FETCH
        # --------------------------------------------------

        query += """
            ORDER BY t.test_name
        """

        cursor.execute(query, tuple(params))
        tests = cursor.fetchall()

        # --------------------------------------------------
        # RENDER
        # --------------------------------------------------

        return render_template(
            "test_builder/tests.html",
            department=department,
            tests=tests,
            laboratories=laboratories,
            creator_filter=creator_filter,
            lab_filter=lab_filter,
            status_filter=status_filter,
            role=role
        )

    finally:
        cursor.close()
        db.close()
    
@test_builder_bp.route("/toggle-test-status/<int:test_id>")
def toggle_test_status(test_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, status, lab_id
            FROM tests
            WHERE id = %s
              AND (
                  %s = 'Developer'
                  OR lab_id = %s
              )
        """, (
            test_id,
            session.get("role"),
            session["lab_id"]
        ))

        test = cursor.fetchone()

        if not test:
            flash(
                "Global tests can only be managed by Developer, "
                "or test not found.",
                "danger"
            )
            return redirect(
                request.referrer
                or url_for("test_builder.configure_test_list")
            )

        new_status = (
            "Inactive"
            if test["status"] == "Active"
            else "Active"
        )

        cursor.execute("""
            UPDATE tests
            SET status = %s
            WHERE id = %s
              AND (
                  %s = 'Developer'
                  OR lab_id = %s
              )
        """, (
            new_status,
            test_id,
            session.get("role"),
            session["lab_id"]
        ))

        db.commit()

        flash("Test status updated.", "success")

        return redirect(
            request.referrer
            or url_for("test_builder.configure_test_list")
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()


@test_builder_bp.route(
    "/edit-test/<int:test_id>",
    methods=["GET", "POST"]
)
def edit_test(test_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(buffered=True, dictionary=True)

    try:
        # --------------------------------------------------
        # STEP 1: Identify the logged-in laboratory
        # --------------------------------------------------

        lab_code = session.get("lab_id")
        user_role = session.get("role")

        cursor.execute(
            """
            SELECT id, lab_id
            FROM laboratories
            WHERE lab_id = %s
            """,
            (lab_code,)
        )

        lab_row = cursor.fetchone()

        if not lab_row:
            flash(
                "Laboratory not found. Please log in again.",
                "danger"
            )
            return redirect(url_for("login"))

        numeric_lab_id = lab_row["id"]

        # --------------------------------------------------
        # STEP 2: Fetch the test
        # --------------------------------------------------

        cursor.execute(
            """
            SELECT *
            FROM tests
            WHERE id = %s
              AND (
                    %s = 'Developer'
                    OR lab_id = %s
                    OR lab_id IS NULL
              )
            """,
            (
                test_id,
                user_role,
                numeric_lab_id
            )
        )

        test = cursor.fetchone()

        if not test:
            flash(
                "Test not found or access denied.",
                "danger"
            )
            return redirect(
                url_for("test_builder.department_list")
            )

        # --------------------------------------------------
        # STEP 3: Determine edit permissions
        # --------------------------------------------------

        is_developer = user_role == "Developer"
        is_global = test.get("lab_id") is None

        # Non-Developer users can change only the price
        # of global tests.
        price_only_mode = (
            not is_developer
            and is_global
        )

        # --------------------------------------------------
        # STEP 4: Handle laboratory-specific price override
        # --------------------------------------------------

        if price_only_mode:

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS lab_test_overrides (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    lab_id BIGINT NOT NULL,
                    test_id BIGINT NOT NULL,
                    price DECIMAL(12,2) NOT NULL,
                    updated_at TIMESTAMP
                        DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_lab_test_override
                        (lab_id, test_id),
                    INDEX idx_lab_test_override_test
                        (test_id)
                )
                """
            )

            # Retrieve this laboratory's existing override.
            cursor.execute(
                """
                SELECT price
                FROM lab_test_overrides
                WHERE lab_id = %s
                  AND test_id = %s
                """,
                (
                    numeric_lab_id,
                    test_id
                )
            )

            override = cursor.fetchone()

            # Preserve the original master price.
            test["master_price"] = test["price"]

            # Display the laboratory-specific price if available.
            if override:
                test["price"] = override["price"]

        # --------------------------------------------------
        # STEP 5: Fetch department information
        # --------------------------------------------------

        cursor.execute(
            """
            SELECT *
            FROM departments
            WHERE id = %s
            """,
            (test["department_id"],)
        )

        department = cursor.fetchone()

        if not department:
            flash(
                "Department information not found.",
                "danger"
            )
            return redirect(
                url_for("test_builder.department_list")
            )

        # --------------------------------------------------
        # STEP 6: Handle POST request
        # --------------------------------------------------

        if request.method == "POST":

            # ==============================================
            # CASE A: Global test - update price override only
            # ==============================================

            if price_only_mode:

                raw_price = (
                    request.form.get("price") or ""
                ).strip()

                try:
                    price = Decimal(raw_price)

                    if (
                        not price.is_finite()
                        or price < 0
                    ):
                        raise ValueError(
                            "Invalid price"
                        )

                except Exception:

                    flash(
                        "Enter a valid non-negative price.",
                        "danger"
                    )

                    return render_template(
                        "test_builder/test_form.html",
                        test=test,
                        department=department,
                        test_code=test["test_code"],
                        edit_mode=True,
                        price_only_mode=True
                    )

                # Save only the current laboratory's override.
                # Do not modify the global tests table.
                cursor.execute(
                    """
                    INSERT INTO lab_test_overrides
                        (lab_id, test_id, price)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        price = VALUES(price)
                    """,
                    (
                        numeric_lab_id,
                        test_id,
                        price
                    )
                )

                db.commit()

                flash(
                    "Your laboratory's price was saved. "
                    "The global test was not changed.",
                    "success"
                )

            # ==============================================
            # CASE B: Developer or laboratory-owned test
            # ==============================================

            else:

                test_name = (
                    request.form.get("test_name") or ""
                ).strip()

                short_name = (
                    request.form.get("short_name") or ""
                ).strip()

                sample_type = (
                    request.form.get("sample_type") or ""
                ).strip()

                report_time = (
                    request.form.get("report_time") or ""
                ).strip()

                description = (
                    request.form.get("description") or ""
                ).strip()

                raw_price = (
                    request.form.get("price") or ""
                ).strip()

                if not test_name or not short_name:
                    flash(
                        "Test name and short name are required.",
                        "danger"
                    )

                    return render_template(
                        "test_builder/test_form.html",
                        test=test,
                        department=department,
                        test_code=test["test_code"],
                        edit_mode=True,
                        price_only_mode=False
                    )

                try:
                    price = Decimal(raw_price)

                    if (
                        not price.is_finite()
                        or price < 0
                    ):
                        raise ValueError(
                            "Invalid price"
                        )

                except Exception:

                    flash(
                        "Enter a valid non-negative price.",
                        "danger"
                    )

                    return render_template(
                        "test_builder/test_form.html",
                        test=test,
                        department=department,
                        test_code=test["test_code"],
                        edit_mode=True,
                        price_only_mode=False
                    )

                # Restrict updates to the Developer or
                # the laboratory that owns the test.
                cursor.execute(
                    """
                    UPDATE tests
                    SET
                        test_name = %s,
                        short_name = %s,
                        price = %s,
                        sample_type = %s,
                        report_time = %s,
                        description = %s
                    WHERE id = %s
                      AND (
                            %s = 'Developer'
                            OR lab_id = %s
                      )
                    """,
                    (
                        test_name,
                        short_name,
                        price,
                        sample_type,
                        report_time,
                        description,
                        test_id,
                        user_role,
                        numeric_lab_id
                    )
                )

                if cursor.rowcount == 0:
                    db.rollback()

                    flash(
                        "Test could not be updated. "
                        "Please verify your permissions.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "test_builder.department_tests",
                            department_id=test["department_id"]
                        )
                    )

                db.commit()

                flash(
                    "Test updated successfully.",
                    "success"
                )

            # --------------------------------------------------
            # STEP 7: Redirect after successful save
            # --------------------------------------------------

            return redirect(
                url_for(
                    "test_builder.department_tests",
                    department_id=test["department_id"]
                )
            )

        # --------------------------------------------------
        # STEP 8: Display the edit form
        # --------------------------------------------------

        return render_template(
            "test_builder/test_form.html",
            test=test,
            department=department,
            test_code=test["test_code"],
            edit_mode=True,
            price_only_mode=price_only_mode
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
        db.close()

        
@test_builder_bp.route("/components/edit/<int:component_id>", methods=["GET", "POST"])
def edit_component(component_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT
        rc.*,
        t.lab_id AS test_lab_id
    FROM report_components rc
    JOIN tests t
        ON rc.test_id=t.id
    WHERE rc.id=%s
      AND (
          %s = 'Developer'
          OR t.lab_id=%s
      )
""", (
    component_id,
    session.get("role"),
    session["lab_id"]
))

    component = cursor.fetchone()

    if not component:
        flash("Component not found.", "danger")
        cursor.close()
        db.close()
        return redirect(url_for("test_builder.configure_test_list"))

    if request.method == "POST":
        cursor.execute("""
    UPDATE report_components rc
    JOIN tests t
        ON rc.test_id=t.id
    SET
        rc.component_name=%s,
        rc.component_type=%s,
        rc.display_order=%s
    WHERE rc.id=%s
      AND (
          %s = 'Developer'
          OR t.lab_id=%s
      )
""", (
    request.form["component_name"],
    request.form["component_type"],
    request.form["display_order"],
    component_id,
    session.get("role"),
    session["lab_id"]
))

        db.commit()

        section_id = component["section_id"]

        cursor.close()
        db.close()

        flash("Component updated successfully.", "success")

        return redirect(url_for(
            "test_builder.component_list",
            section_id=section_id
        ))

    cursor.close()
    db.close()

    return render_template(
        "test_builder/edit_component.html",
        component=component
    )        
########################################################
# Edit Reference Range
########################################################

@test_builder_bp.route(
    "/reference-ranges/edit/<int:range_id>",
    methods=["GET", "POST"]
)
def edit_reference_range(range_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # --------------------------------------------------
    # Get Existing Reference Range
    # --------------------------------------------------

    cursor.execute("""
        SELECT *
        FROM parameter_reference_ranges
        WHERE id = %s
    """, (range_id,))

    reference = cursor.fetchone()

    if not reference:

        flash(
            "Reference range not found.",
            "danger"
        )

        cursor.close()
        db.close()

        return redirect(
            url_for(
                "test_builder.configure_test_list"
            )
        )

    parameter_id = reference["parameter_id"]

    # --------------------------------------------------
    # Get Parameter Details
    # --------------------------------------------------

    cursor.execute("""
        SELECT
            pd.*,
            rc.component_name,
            ts.section_name,
            t.test_name,
            t.lab_id AS test_lab_id

        FROM parameter_definition pd

        JOIN report_components rc
            ON pd.component_id = rc.id

        JOIN test_sections ts
            ON rc.section_id = ts.id

        JOIN tests t
            ON rc.test_id = t.id

        WHERE pd.id = %s
          AND (
                %s = 'Developer'
                OR t.lab_id = %s
                OR t.lab_id IS NULL
          )
    """, (
        parameter_id,
        session.get("role", ""),
        session.get("lab_id")
    ))

    # IMPORTANT:
    # Fetch ONLY ONCE
    parameter = cursor.fetchone()

    if not parameter:

        flash(
            "Parameter not found or access denied.",
            "danger"
        )

        cursor.close()
        db.close()

        return redirect(
            url_for(
                "test_builder.configure_test_list"
            )
        )

    # --------------------------------------------------
    # Save Changes
    # --------------------------------------------------

    if request.method == "POST":

        def decimal_or_none(value):

            value = (value or "").strip()

            return Decimal(value) if value else None

        lower_value = decimal_or_none(
            request.form.get("lower_value")
        )

        upper_value = decimal_or_none(
            request.form.get("upper_value")
        )

        critical_low = decimal_or_none(
            request.form.get("critical_low")
        )

        critical_high = decimal_or_none(
            request.form.get("critical_high")
        )

        age_from = decimal_or_none(
            request.form.get("age_from")
        )

        age_to = decimal_or_none(
            request.form.get("age_to")
        )

        reference_text = (
            request.form.get(
                "reference_text",
                ""
            ).strip()
            or None
        )

        interpretation = (
            request.form.get(
                "interpretation",
                ""
            ).strip()
            or None
        )

        cursor.execute("""
            UPDATE parameter_reference_ranges
            SET
                gender = %s,
                age_from = %s,
                age_to = %s,
                age_unit = %s,
                lower_value = %s,
                upper_value = %s,
                critical_low = %s,
                critical_high = %s,
                reference_text = %s,
                interpretation = %s

            WHERE id = %s
        """, (
            request.form["gender"],
            age_from,
            age_to,
            request.form["age_unit"],
            lower_value,
            upper_value,
            critical_low,
            critical_high,
            reference_text,
            interpretation,
            range_id
        ))

        db.commit()

        flash(
            "Reference Range updated successfully.",
            "success"
        )

        cursor.close()
        db.close()

        return redirect(
            url_for(
                "test_builder.reference_range_list",
                parameter_id=parameter_id
            )
        )

    # --------------------------------------------------
    # Show Edit Page
    # --------------------------------------------------

    cursor.close()
    db.close()

    return render_template(
        "test_builder/add_reference_range.html",
        parameter=parameter,
        reference=reference,
        edit_mode=True
    )
########################################################
# Delete Reference Range
########################################################

@test_builder_bp.route("/reference-ranges/delete/<int:range_id>")
def delete_reference_range(range_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Get parameter id before deleting
    cursor.execute("""
    SELECT
        prr.parameter_id,
        pd.lab_id,
        t.lab_id AS test_lab_id
    FROM parameter_reference_ranges prr
    JOIN parameter_definition pd
        ON prr.parameter_id=pd.id
    JOIN report_components rc
        ON pd.component_id=rc.id
    JOIN tests t
        ON rc.test_id=t.id
    WHERE prr.id=%s
      AND (
          %s = 'Developer'
          OR t.lab_id=%s
      )
""", (
    range_id,
    session.get("role"),
    session["lab_id"]
))

    reference = cursor.fetchone()

    if not reference:
     flash(
        "Reference range not found or access denied.",
        "danger"
    )
     cursor.close()
     db.close()
     return redirect(
        url_for(
            "test_builder.configure_test_list"
        )
    )

    parameter_id = reference["parameter_id"]
    cursor.execute("""
    SELECT pd.lab_id
    FROM parameter_definition pd
    WHERE pd.id = %s
""", (parameter_id,))

    parameter = cursor.fetchone()

    if not parameter:
     flash("Parameter not found.", "danger")
     cursor.close()
     db.close()
     return redirect(url_for("test_builder.configure_test_list"))

    if (
     session.get("role") != "Developer"
     and parameter["lab_id"] != session["lab_id"]
):
     flash("Access denied.", "danger")
     cursor.close()
     db.close()
     return redirect(url_for("test_builder.configure_test_list"))

    # Delete reference range
    cursor.execute("""
        DELETE FROM parameter_reference_ranges
        WHERE id=%s
    """, (range_id,))

    db.commit()

    cursor.close()
    db.close()

    flash("Reference Range deleted successfully.", "success")

    return redirect(
        url_for(
            "test_builder.reference_range_list",
            parameter_id=parameter_id
        )
    )  
@test_builder_bp.route(
    "/parameters/dropdown-options/<int:parameter_id>",
    methods=["POST"]
)
def save_dropdown_options(parameter_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                pd.id
            FROM parameter_definition pd
            JOIN report_components rc
                ON pd.component_id=rc.id
            JOIN tests t
                ON rc.test_id=t.id
            WHERE pd.id=%s
              AND (
                  %s = 'Developer'
                  OR t.lab_id=%s
              )
        """, (
            parameter_id,
            session.get("role"),
            session["lab_id"]
        ))

        parameter = cursor.fetchone()

        if not parameter:

            flash(
                "Parameter not found or access denied.",
                "danger"
            )

            return redirect(
                url_for(
                    "test_builder.configure_test_list"
                )
            )

        options = request.form.getlist(
            "option_values[]"
        )

        cursor.execute("""
            DELETE FROM parameter_dropdown_options
            WHERE parameter_id=%s
        """, (parameter_id,))

        for val in options:

            val = val.strip()

            if val:

                cursor.execute("""
                    INSERT INTO parameter_dropdown_options
                    (
                        parameter_id,
                        option_value
                    )
                    VALUES
                    (%s,%s)
                """, (
                    parameter_id,
                    val
                ))

        db.commit()

        flash(
            "Dictionary options updated successfully.",
            "success"
        )

        return redirect(request.referrer)

    finally:

        cursor.close()
        db.close() 
@test_builder_bp.route("/report-dictionaries")
def report_dictionaries():

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            rd.id,
            rd.dictionary_name,
            rd.description,
            COUNT(rdv.id) AS total_values
        FROM report_dictionaries rd
        LEFT JOIN report_dictionary_values rdv
            ON rd.id = rdv.dictionary_id
        GROUP BY
            rd.id,
            rd.dictionary_name,
            rd.description
        ORDER BY
            rd.dictionary_name
    """)

    dictionaries = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "test_builder/report_dictionaries.html",
        dictionaries=dictionaries
    )
@test_builder_bp.route("/report-dictionaries/add", methods=["GET","POST"])
def add_report_dictionary():

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor()

    if request.method == "POST":

        dictionary_name = request.form["dictionary_name"]
        description = request.form.get("description","")

        cursor.execute("""
            INSERT INTO report_dictionaries
            (
                dictionary_name,
                description
            )
            VALUES
            (%s,%s)
        """,(dictionary_name,description))

        db.commit()

        cursor.close()
        db.close()

        flash("Dictionary Added Successfully","success")

        return redirect(
            url_for("test_builder.report_dictionaries")
        )

    cursor.close()
    db.close()

    return render_template(
        "test_builder/add_report_dictionary.html"
    )
@test_builder_bp.route("/report-dictionaries/<int:dictionary_id>", methods=["GET","POST"])
def manage_dictionary(dictionary_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM report_dictionaries
        WHERE id=%s
    """,(dictionary_id,))

    dictionary = cursor.fetchone()

    if request.method=="POST":

        value = request.form["value_text"]

        cursor.execute("""
            INSERT INTO report_dictionary_values
            (
                dictionary_id,
                value_text,
                display_order
            )
            VALUES
            (%s,%s,1)
        """,(dictionary_id,value))

        db.commit()

        return redirect(
            url_for(
                "test_builder.manage_dictionary",
                dictionary_id=dictionary_id
            )
        )

    cursor.execute("""
        SELECT *
        FROM report_dictionary_values
        WHERE dictionary_id=%s
        ORDER BY
            display_order,
            id
    """,(dictionary_id,))

    values = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "test_builder/manage_dictionary.html",
        dictionary=dictionary,
        values=values
    )
@test_builder_bp.route("/report-formulas")
def report_formulas():

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM report_formulas
        ORDER BY formula_name
    """)

    formulas = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
    "formulas/formula_list.html",
    formulas=formulas
)
@test_builder_bp.route("/report-formulas/add", methods=["GET", "POST"])
def add_formula():

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        formula_name = request.form["formula_name"].strip()

        formula_expression = request.form["formula_expression"].strip()

        description = request.form.get("description", "").strip()

        category = request.form.get("category", "").strip()

        status = request.form.get("status", "active")

        cursor.execute("""
            INSERT INTO report_formulas
            (
                formula_name,
                formula_expression,
                description,
                category,
                status
            )
            VALUES
            (
                %s, %s, %s, %s, %s
            )
        """, (

            formula_name,
            formula_expression,
            description,
            category,
            status

        ))

        db.commit()

        flash(
            "Formula added successfully.",
            "success"
        )

        cursor.close()
        db.close()

        return redirect(
            url_for("test_builder.report_formulas")
        )

    cursor.close()
    db.close()

    return render_template(
        "formulas/add_formula.html"
    )
@test_builder_bp.route("/report-formulas/edit/<int:formula_id>", methods=["GET", "POST"])
def edit_formula(formula_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # -------------------------------
    # Get Formula
    # -------------------------------

    cursor.execute("""
        SELECT *
        FROM report_formulas
        WHERE id = %s
    """, (formula_id,))

    formula = cursor.fetchone()

    if not formula:

        flash("Formula not found.", "danger")

        cursor.close()
        db.close()

        return redirect(
            url_for("test_builder.report_formulas")
        )

    # -------------------------------
    # Update Formula
    # -------------------------------

    if request.method == "POST":

        formula_name = request.form["formula_name"].strip()

        formula_expression = request.form["formula_expression"].strip()

        description = request.form.get("description", "").strip()

        category = request.form.get("category", "").strip()

        status = request.form.get("status", "active")

        cursor.execute("""
            UPDATE report_formulas
            SET
                formula_name=%s,
                formula_expression=%s,
                description=%s,
                category=%s,
                status=%s
            WHERE id=%s
        """, (

            formula_name,
            formula_expression,
            description,
            category,
            status,
            formula_id

        ))

        db.commit()

        flash(
            "Formula updated successfully.",
            "success"
        )

        cursor.close()
        db.close()

        return redirect(
            url_for("test_builder.report_formulas")
        )

    cursor.close()
    db.close()

    return render_template(
        "formulas/edit_formula.html",
        formula=formula
    )
@test_builder_bp.route("/formula-master/delete/<int:formula_id>")
def delete_formula(formula_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        DELETE
        FROM report_formulas
        WHERE id=%s
    """,(formula_id,))

    db.commit()

    cursor.close()
    db.close()

    flash("Formula Deleted","success")

    return redirect(
        url_for("test_builder.report_formulas")
    )
@test_builder_bp.route("/configure-parameter/<int:parameter_id>")
def configure_parameter(parameter_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT
        pd.*
    FROM parameter_definition pd
    JOIN report_components rc
        ON pd.component_id=rc.id
    JOIN tests t
        ON rc.test_id=t.id
    WHERE pd.id=%s
      AND (
          %s = 'Developer'
          OR t.lab_id=%s
          OR t.lab_id IS NULL
      )
      AND pd.lab_id <=> t.lab_id
""", (
    parameter_id,
    session.get("role"),
    session["lab_id"]
))

    parameter = cursor.fetchone()

    if not parameter:
        flash("Parameter not found.", "danger")
        cursor.close()
        db.close()
        return redirect(request.referrer)

    cursor.close()
    db.close()

    return render_template(
        "test_builder/configure_parameter.html",
        parameter=parameter
    )
@test_builder_bp.route('/delete-component/<int:component_id>', methods=['POST'])

def delete_component(component_id):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if "lab_id" not in session:
     return redirect(url_for("login"))

    cursor.execute("""
    SELECT
        rc.*,
        t.lab_id AS test_lab_id
    FROM report_components rc
    JOIN tests t
        ON rc.test_id=t.id
    WHERE rc.id=%s
      AND (
          %s = 'Developer'
          OR t.lab_id=%s
      )
""", (
    component_id,
    session.get("role"),
    session["lab_id"]
))

    component = cursor.fetchone()

    if not component:
     flash(
        "Component not found or access denied.",
        "danger"
    )
     cursor.close()
     db.close()
     return redirect(request.referrer)

    # If parameter component, delete all parameters first
    if component["component_type"].lower() in ["parameter", "parameter table"]:

        cursor.execute("""
            DELETE FROM parameter_definition
            WHERE component_id=%s
        """, (component_id,))

    # Finally delete component
    cursor.execute("""
        DELETE FROM report_components
        WHERE id=%s
    """, (component_id,))

    db.commit()

    flash("Component deleted successfully.", "success")

    return redirect(
        url_for(
            "test_builder.configure_test",
            test_id=component["test_id"]
        )
    )
@test_builder_bp.route(
    "/edit-dictionary-result/<int:component_id>",
    methods=["GET", "POST"]
)
def edit_dictionary_result(component_id):

    # ==========================================================
    # 1. CHECK LOGIN
    # ==========================================================

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = None
    cursor = None

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # ======================================================
        # 2. LOAD COMPONENT AND VALIDATE ACCESS
        # ======================================================

        cursor.execute(
            """
            SELECT
                rc.*,
                t.lab_id AS test_lab_id
            FROM report_components rc
            JOIN tests t
                ON rc.test_id = t.id
            WHERE rc.id = %s
              AND (
                    %s = 'Developer'
                    OR t.lab_id = %s
              )
            """,
            (
                component_id,
                session.get("role"),
                session["lab_id"]
            )
        )

        component = cursor.fetchone()

        current_app.logger.info(
            "DICTIONARY EDIT | component_id=%s | role=%s | "
            "lab_id=%s | component_found=%s",
            component_id,
            session.get("role"),
            session.get("lab_id"),
            bool(component)
        )

        if not component:
            flash(
                "Component not found or access denied.",
                "danger"
            )

            return redirect(
                url_for("test_builder.configure_test")
            )

        # ======================================================
        # 3. VALIDATE COMPONENT TYPE
        # ======================================================

        if component.get("component_type") != "dictionary_result":

            flash(
                "Invalid Dictionary Result component.",
                "danger"
            )

            return redirect(
                url_for(
                    "test_builder.component_list",
                    section_id=component["section_id"]
                )
            )

        # ======================================================
        # 4. READ DICTIONARY ID FROM COMPONENT CONTENT
        # ======================================================

        dictionary_id = None

        component_content = component.get("component_content")

        try:
            if component_content:

                if isinstance(component_content, str):
                    content = json.loads(component_content)
                else:
                    content = component_content

                if isinstance(content, dict):
                    raw_dictionary_id = content.get("dictionary_id")

                    if raw_dictionary_id is not None:
                        dictionary_id = int(raw_dictionary_id)

        except (ValueError, TypeError, json.JSONDecodeError):

            current_app.logger.exception(
                "Invalid component_content for component_id=%s",
                component_id
            )

        current_app.logger.info(
            "DICTIONARY ID DEBUG | component_id=%s | "
            "component_content=%r | dictionary_id=%r",
            component_id,
            component_content,
            dictionary_id
        )

        # ======================================================
        # 5. VALIDATE DICTIONARY ID
        # ======================================================

        if not dictionary_id or dictionary_id <= 0:

            flash(
                "Dictionary ID is missing or invalid. "
                "Please check the component configuration.",
                "danger"
            )

            return redirect(
                url_for(
                    "test_builder.component_list",
                    section_id=component["section_id"]
                )
            )

        # ======================================================
        # 6. LOAD ASSOCIATED DICTIONARY
        # ======================================================

        cursor.execute(
            """
            SELECT
                id,
                dictionary_name,
                description
            FROM report_dictionaries
            WHERE id = %s
            """,
            (dictionary_id,)
        )

        dictionary = cursor.fetchone()

        if not dictionary:

            flash(
                "Associated dictionary was not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "test_builder.component_list",
                    section_id=component["section_id"]
                )
            )

        # ======================================================
        # 7. HANDLE FORM SUBMISSION
        # ======================================================

        if request.method == "POST":

            component_name = request.form.get(
                "component_name",
                ""
            ).strip()

            display_order_raw = request.form.get(
                "display_order",
                ""
            ).strip()

            values = request.form.getlist(
                "dictionary_values[]"
            )

            # --------------------------------------------------
            # VALIDATE COMPONENT NAME
            # --------------------------------------------------

            if not component_name:

                flash(
                    "Component name is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "test_builder.edit_dictionary_result",
                        component_id=component_id
                    )
                )

            # --------------------------------------------------
            # VALIDATE DISPLAY ORDER
            # --------------------------------------------------

            try:
                display_order = int(display_order_raw)

                if display_order < 1:
                    raise ValueError

            except (ValueError, TypeError):

                flash(
                    "Display order must be a positive integer.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "test_builder.edit_dictionary_result",
                        component_id=component_id
                    )
                )

            # --------------------------------------------------
            # CLEAN DICTIONARY VALUES
            # --------------------------------------------------

            cleaned_values = [
                value.strip()
                for value in values
                if value and value.strip()
            ]

            if not cleaned_values:

                flash(
                    "Enter at least one dictionary value.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "test_builder.edit_dictionary_result",
                        component_id=component_id
                    )
                )

            # --------------------------------------------------
            # REMOVE DUPLICATE VALUES
            # --------------------------------------------------

            normalized_values = [
                value.casefold()
                for value in cleaned_values
            ]

            if len(normalized_values) != len(set(normalized_values)):

                flash(
                    "Duplicate dictionary values are not allowed.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "test_builder.edit_dictionary_result",
                        component_id=component_id
                    )
                )

            # --------------------------------------------------
            # UPDATE DATABASE TRANSACTIONALLY
            # --------------------------------------------------

            try:

                # Update component information.
                cursor.execute(
                    """
                    UPDATE report_components
                    SET
                        component_name = %s,
                        display_order = %s
                    WHERE id = %s
                    """,
                    (
                        component_name,
                        display_order,
                        component_id
                    )
                )

                # Delete old values belonging to this dictionary.
                cursor.execute(
                    """
                    DELETE FROM report_dictionary_values
                    WHERE dictionary_id = %s
                    """,
                    (dictionary_id,)
                )

                # Insert the new values.
                for order, value in enumerate(
                    cleaned_values,
                    start=1
                ):

                    cursor.execute(
                        """
                        INSERT INTO report_dictionary_values
                        (
                            dictionary_id,
                            value_text,
                            display_order
                        )
                        VALUES (%s, %s, %s)
                        """,
                        (
                            dictionary_id,
                            value,
                            order
                        )
                    )

                # Commit only after all operations succeed.
                db.commit()

                flash(
                    "Dictionary Result updated successfully.",
                    "success"
                )

                return redirect(
                    url_for(
                        "test_builder.component_list",
                        section_id=component["section_id"]
                    )
                )

            except Exception:

                db.rollback()

                current_app.logger.exception(
                    "Dictionary Result update failed "
                    "for component_id=%s",
                    component_id
                )

                flash(
                    "Update failed. Database changes were rolled back.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "test_builder.edit_dictionary_result",
                        component_id=component_id
                    )
                )

        # ======================================================
        # 8. LOAD EXISTING DICTIONARY VALUES
        # ======================================================

        cursor.execute(
            """
            SELECT
                id,
                dictionary_id,
                value_text,
                display_order
            FROM report_dictionary_values
            WHERE dictionary_id = %s
            ORDER BY display_order, id
            """,
            (dictionary_id,)
        )

        dictionary_values = cursor.fetchall()

        # ======================================================
        # 9. RENDER EDITOR TEMPLATE
        # ======================================================

        return render_template(
            "test_builder/edit_dictionary_result.html",
            component=component,
            dictionary=dictionary,
            dictionary_values=dictionary_values
        )

    except Exception as e:

        if db:
            try:
                db.rollback()
            except Exception:
                current_app.logger.exception(
                    "Database rollback failed."
                )

        current_app.logger.exception(
            "Error loading Dictionary Result editor "
            "for component_id=%s",
            component_id
        )

        flash(
            f"Dictionary Result editor error: {str(e)}",
            "danger"
        )

        return redirect(
            url_for("test_builder.configure_test")
        )

    finally:

        if cursor:
            try:
                cursor.close()
            except Exception:
                current_app.logger.exception(
                    "Failed to close database cursor."
                )

        if db:
            try:
                db.close()
            except Exception:
                current_app.logger.exception(
                    "Failed to close database connection."
                )
    ############################################################
# EDIT PARAMETER
############################################################

@test_builder_bp.route(
    "/parameters/edit/<int:parameter_id>",
    methods=["GET", "POST"]
)
def edit_parameter(parameter_id):

    if "lab_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:

        # -------------------------------------------------
        # LOAD PARAMETER
        # -------------------------------------------------
        cursor.execute("""
            SELECT
                pd.*
            FROM parameter_definition pd
            WHERE pd.id = %s
        """, (parameter_id,))

        parameter = cursor.fetchone()

        if not parameter:

            flash(
                "Parameter not found.",
                "danger"
            )

            return redirect(
                request.referrer or
                url_for(
                    "test_builder.configure_test_list"
                )
            )

        # -------------------------------------------------
        # UPDATE PARAMETER
        # -------------------------------------------------
        if request.method == "POST":

            display_name = request.form.get(
                "display_name",
                ""
            ).strip()

            short_name = request.form.get(
                "short_name",
                ""
            ).strip()

            unit = request.form.get(
                "unit",
                ""
            ).strip()

            method = request.form.get(
                "method",
                ""
            ).strip()

            reference_type = request.form.get(
                "reference_type",
                "normal"
            )

            data_type = request.form.get(
                "data_type",
                "numeric"
            )

            display_order = request.form.get(
                "display_order",
                1
            )

            editable = (
                1
                if request.form.get("editable")
                else 0
            )

            optional_field = (
                1
                if request.form.get("optional_field")
                else 0
            )

            highlight_abnormal = (
                1
                if request.form.get("highlight_abnormal")
                else 0
            )

            machine_readable = (
                1
                if request.form.get("machine_readable")
                else 0
            )

            # -------------------------------------------------
            # UPDATE
            # -------------------------------------------------
            cursor.execute("""
                UPDATE parameter_definition
                SET
                    display_name = %s,
                    short_name = %s,
                    unit = %s,
                    method = %s,
                    reference_type = %s,
                    data_type = %s,
                    display_order = %s,
                    editable = %s,
                    optional_field = %s,
                    highlight_abnormal = %s,
                    machine_readable = %s
                WHERE id = %s
            """, (
                display_name,
                short_name,
                unit,
                method,
                reference_type,
                data_type,
                display_order,
                editable,
                optional_field,
                highlight_abnormal,
                machine_readable,
                parameter_id
            ))

            db.commit()

            flash(
                "Parameter updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "test_builder.parameter_list",
                    component_id=parameter["component_id"]
                )
            )

        # -------------------------------------------------
        # SHOW EDIT PAGE
        # -------------------------------------------------
        return render_template(
            "test_builder/edit_parameter.html",
            parameter=parameter
        )

    except Exception:

        db.rollback()
        raise

    finally:

        cursor.close()
        db.close()