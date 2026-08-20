import pandas as pd
from agentteam.models.structured_outputs import TransformationRule

def trim_string_columns(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    df = df.copy()
    string_cols = df.select_dtypes(include=['object']).columns
    for col in string_cols:
        df[col] = df[col].str.strip()
    return df