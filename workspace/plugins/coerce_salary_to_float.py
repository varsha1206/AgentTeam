import pandas as pd
from agentteam.models.structured_outputs import TransformationRule

def coerce_salary_to_float(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    df_copy = df.copy()
    target_cols = rule.columns if rule.columns else df_copy.columns
    for col in target_cols:
        if col in df_copy.columns:
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').astype('float64')
    return df_copy