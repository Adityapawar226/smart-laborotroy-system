from modules.formula_engine import calculate_formula

values = {
    "HB":13.8,
    "RBC":4.71
}

formula = "(HB*10)/RBC"

print(calculate_formula(formula, values))