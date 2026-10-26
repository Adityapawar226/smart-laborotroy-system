import ast
import math
import operator
import re


# ============================================================
# SUPPORTED MATHEMATICAL OPERATORS
# ============================================================

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
}


# ============================================================
# NORMALIZE PARAMETER NAMES
# ============================================================

def normalize_parameter_name(name):
    """
    Normalize parameter names for formula matching.

    Examples:
        RBC Count       -> RBC_COUNT
        R.B.C Count     -> RBC_COUNT
        R.B.C_COUNT     -> RBC_COUNT
        rbc_count       -> RBC_COUNT
        Hemoglobin      -> HEMOGLOBIN
        Packed Cell Volume (HCT) -> PACKED_CELL_VOLUME_HCT
    """

    name = str(name).strip().upper()

    # Remove periods within abbreviations:
    # R.B.C -> RBC
    name = re.sub(r"(?<=[A-Z0-9])\.(?=[A-Z0-9])", "", name)

    # Replace remaining punctuation and spaces with underscores.
    name = re.sub(r"[^A-Z0-9]+", "_", name)

    return name.strip("_")


# ============================================================
# SAFE MATHEMATICAL EXPRESSION EVALUATOR
# ============================================================

def evaluate_expression(expression):
    """
    Evaluate a mathematical expression without eval().

    Supported:
        Addition
        Subtraction
        Multiplication
        Division
        Exponentiation
        Modulo
        Parentheses
        Unary plus and minus
        Numeric constants
    """

    tree = ast.parse(expression, mode="eval")

    def evaluate(node):

        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant):

            if (
                isinstance(node.value, bool)
                or not isinstance(node.value, (int, float))
            ):
                raise ValueError("Invalid numeric constant.")

            return node.value

        if isinstance(node, ast.BinOp):

            operation = OPERATORS.get(type(node.op))

            if operation is None:
                raise ValueError("Unsupported mathematical operator.")

            left = evaluate(node.left)
            right = evaluate(node.right)

            # Avoid unreasonable exponent calculations.
            if isinstance(node.op, ast.Pow):

                if abs(right) > 100:
                    raise ValueError("Exponent is outside the allowed range.")

                if abs(left) > 1e100:
                    raise ValueError("Base is outside the allowed range.")

            result = operation(left, right)

            if not isinstance(result, (int, float)):
                raise ValueError("Expression did not produce a number.")

            if not math.isfinite(float(result)):
                raise ValueError("Expression produced a non-finite result.")

            return result

        if isinstance(node, ast.UnaryOp):

            operation = OPERATORS.get(type(node.op))

            if operation is None:
                raise ValueError("Unsupported unary operator.")

            return operation(evaluate(node.operand))

        raise ValueError(
            f"Unsupported expression element: {type(node).__name__}"
        )

    return evaluate(tree)


# ============================================================
# FORMULA CALCULATION
# ============================================================

def calculate_formula(formula_expression, parameter_values):
    """
    Calculate a formula using parameter values.

    Example:
        Formula:
            (HB * 10) / RBC_COUNT

        Values:
            {
                "HB": 11,
                "RBC_COUNT": 4.5
            }

        Result:
            24.44

    Returns:
        float: Successful calculation.
        None: Missing variables or invalid formula.
    """

    # --------------------------------------------------------
    # STEP 1: VALIDATE INPUT
    # --------------------------------------------------------

    if formula_expression is None:

        print("[FORMULA ERROR] Formula expression is None.")

        return None

    expression = str(formula_expression).strip()

    if not expression:

        print("[FORMULA ERROR] Formula expression is empty.")

        return None

    if not isinstance(parameter_values, dict):

        print("[FORMULA ERROR] Parameter values must be a dictionary.")

        return None

    # --------------------------------------------------------
    # STEP 2: NORMALIZE PARAMETER KEYS
    # --------------------------------------------------------

    normalized_values = {}

    for key, value in parameter_values.items():

        if value is None:
            continue

        if str(value).strip() == "":
            continue

        try:

            numeric_value = float(value)

        except (TypeError, ValueError):

            continue

        if not math.isfinite(numeric_value):

            print(
                "[FORMULA WARNING] Non-finite parameter:",
                key,
                value
            )

            continue

        normalized_key = normalize_parameter_name(key)

        if not normalized_key:
            continue

        normalized_values[normalized_key] = numeric_value

    # --------------------------------------------------------
    # STEP 3: NORMALIZE FORMULA SYMBOLS
    # --------------------------------------------------------

    # Support the common multiplication symbol.
    expression = expression.replace("×", "*")

    # Support the division symbol.
    expression = expression.replace("÷", "/")

    # Replace parameter names with their numeric values.
    #
    # Longer names are processed first to reduce the chance
    # of replacing part of a longer parameter name.

    for key in sorted(
        normalized_values.keys(),
        key=len,
        reverse=True
    ):

        value = normalized_values[key]

        expression = re.sub(
            rf"(?<![A-Za-z0-9_]){re.escape(key)}(?![A-Za-z0-9_])",
            repr(value),
            expression,
            flags=re.IGNORECASE
        )

    # --------------------------------------------------------
    # STEP 4: DETECT UNRESOLVED VARIABLES
    # --------------------------------------------------------

    unresolved_variables = re.findall(
        r"\b[A-Za-z_][A-Za-z0-9_]*\b",
        expression
    )

    if unresolved_variables:

        print("[FORMULA ERROR] Unresolved variables:")
        print(unresolved_variables)

        print("[FORMULA ERROR] Original formula:")
        print(formula_expression)

        print("[FORMULA ERROR] Processed formula:")
        print(expression)

        print("[FORMULA DEBUG] Available parameter names:")
        print(list(normalized_values.keys()))

        return None

    # --------------------------------------------------------
    # STEP 5: CALCULATE
    # --------------------------------------------------------

    try:

        result = evaluate_expression(expression)

        result = float(result)

        if not math.isfinite(result):

            raise ValueError(
                "Calculation produced an invalid numeric result."
            )

        result = round(result, 2)

        print(
            "[FORMULA SUCCESS]",
            formula_expression,
            "=",
            result
        )

        return result

    except ZeroDivisionError:

        print(
            "[FORMULA ERROR] Division by zero:",
            formula_expression
        )

        return None

    except (
        SyntaxError,
        ValueError,
        TypeError,
        OverflowError
    ) as error:

        print("[FORMULA ERROR]", error)

        print("[FORMULA DEBUG] Original formula:")
        print(formula_expression)

        print("[FORMULA DEBUG] Processed formula:")
        print(expression)

        return None