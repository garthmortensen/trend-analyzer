from sqlalchemy import func, case, literal_column

class TrendMetrics:
    """
    Central repository for actuarial metric calculations.
    Returns SQLAlchemy expressions to be injected into queries.
    """

    @staticmethod
    def total_allowed(claims_table):
        """
        Calculation: Sum(Allowed)
        """
        return func.sum(claims_table.c.allowed).label("total_allowed")

    @staticmethod
    def total_utilization(claims_table):
        """
        Calculation: Sum(Utilization)
        """
        return func.sum(claims_table.c.utilization).label("total_utilization")

    @staticmethod
    def total_units_days(claims_table):
        """
        Calculation: Sum(Units/Days)
        """
        # Updated to match data warehouse schema: hcg_units_days
        if 'hcg_units_days' in claims_table.c:
             return func.sum(claims_table.c.hcg_units_days).label("total_units_days")
        # Fallback for legacy/alternative naming
        if 'units_days' in claims_table.c:
             return func.sum(claims_table.c.units_days).label("total_units_days")
        return literal_column("0").label("total_units_days")

    @staticmethod
    def member_months(members_table):
        """
        Calculation: Sum(Member Months)
        """
        return func.sum(members_table.c.member_months).label("member_months")

    @staticmethod
    def allowed_pmpm(claims_table, members_table):
        """
        Calculation: Sum(Allowed) / Sum(Member Months)
        """
        numerator = func.sum(claims_table.c.allowed)
        denominator = func.sum(members_table.c.member_months)

        # Handle division by zero safely
        return case(
            (denominator == 0, 0),
            else_=numerator / denominator
        ).label("allowed_pmpm")

    @staticmethod
    def utilization_pkpy(claims_table, members_table):
        """
        Calculation: (Sum(Utilization) * 12000) / Sum(Member Months)
        Per Thousand Per Year
        """
        numerator = func.sum(claims_table.c.utilization) * 12000
        denominator = func.sum(members_table.c.member_months)

        return case(
            (denominator == 0, 0),
            else_=numerator / denominator
        ).label("utilization_pkpy")

    @staticmethod
    def cost_per_service(claims_table, members_table):
        """
        Calculation: Sum(Allowed) / Sum(Utilization)
        """
        numerator = func.sum(claims_table.c.allowed)
        denominator = func.sum(claims_table.c.utilization)

        return case(
            (denominator == 0, 0),
            else_=numerator / denominator
        ).label("cost_per_service")
    
    @staticmethod
    def length_of_stay(claims_table, members_table):
        """
        Calculation: Sum(Units Days) / Sum(Utilization)
        """
        # Updated to match data warehouse schema: hcg_units_days
        if 'hcg_units_days' in claims_table.c:
            numerator = func.sum(claims_table.c.hcg_units_days)
        elif 'units_days' in claims_table.c:
            numerator = func.sum(claims_table.c.units_days)
        else:
            numerator = 0
            
        denominator = func.sum(claims_table.c.utilization)

        return case(
            (denominator == 0, 0),
            else_=numerator / denominator
        ).label("length_of_stay")

    @staticmethod
    def allowed_to_billed_ratio(claims_table):
        """
        Calculation: Sum(Allowed) / Sum(Charges)
        """
        if 'total_charges' in claims_table.c:
            numerator = func.sum(claims_table.c.allowed)
            denominator = func.sum(claims_table.c.total_charges)
            return case(
                (denominator == 0, 0),
                else_=numerator / denominator
            ).label("allowed_to_billed_ratio")
        return literal_column("0").label("allowed_to_billed_ratio")
