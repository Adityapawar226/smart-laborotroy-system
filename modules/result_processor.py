from modules.formula_service import calculate_all_formulas


class ResultProcessor:

    def __init__(self, db):
        self.db = db
        self.cursor = db.cursor(pymysql.cursors.DictCursor)

    def process(
        self,
        patient_id,
        test_id,
        parameter_values
    ):

        # 1. Calculate formulas
        calculated_results = calculate_all_formulas(
           cursor,
          patient_id,
          lab_id,
          parameter_values,
           formula_parameters
)

        # 2. Save calculated results
        self.save_formula_results(
            patient_id,
            calculated_results
        )

        return calculated_results


    def save_formula_results(
        self,
        patient_id,
        calculated_results
    ):

        pass