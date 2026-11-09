from processing.rules_engine import apply_compliance_rules


def add_rule_flags(df):
    return apply_compliance_rules(df)
