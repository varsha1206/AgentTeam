import pandas as pd
from agentteam.models.structured_outputs import TransformationRule

def coerce_employee_age_to_int(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    df = df.copy()
    target_col = 'employeeAge' if rule.columns is None or len(rule.columns) == 0 else rule.columns[0]
    if target_col in df.columns:
        df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
        df[target_col] = df[target_col].astype('Int64')
    return df