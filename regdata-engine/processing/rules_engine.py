import os
import yaml
from pyspark.sql import functions as F


def _load_rules(yaml_path):
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)["rules"]


def _build_condition(rule):
    ctype = rule["condition_type"]

    if ctype == "col_neq_col":
        return F.when(
            F.col(rule["left_col"]) != F.col(rule["right_col"]),
            F.lit(rule["flag"])
        )

    if ctype == "col_gte_val":
        return F.when(
            (F.col(rule["currency_col"]) == rule["currency_val"]) &
            (F.col(rule["col"]).cast("double") >= rule["threshold"]),
            F.lit(rule["flag"])
        )

    if ctype == "col_eq_val":
        return F.when(
            F.col(rule["col"]) == rule["value"],
            F.lit(rule["flag"])
        )

    if ctype == "col_null_or_invalid_regex":
        return F.when(
            F.col(rule["col"]).isNull() |
            ~F.col(rule["col"]).rlike(rule["regex"]),
            F.lit(rule["flag"])
        )

    raise ValueError(f"Unknown condition_type: {ctype}")


def apply_compliance_rules(df, yaml_path=None):
    if yaml_path is None:
        yaml_path = os.path.join(
            os.path.dirname(__file__),
            "..", "rules", "compliance_rules.yaml"
        )

    rules = _load_rules(yaml_path)
    conditions = [_build_condition(rule) for rule in rules]

    return df.withColumn(
        "rule_flags",
        F.filter(F.array(*conditions), lambda x: x.isNotNull())
    )
