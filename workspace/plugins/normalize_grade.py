import pandas as pd
from agentteam.models.structured_outputs import TransformationRule

def normalize_grade(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    df = df.copy()
    target_cols = rule.columns if rule.columns else ['grade']
    
    for col in target_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
    
    return df