import pandas as pd
from agentteam.models.structured_outputs import TransformationRule

def trim_string_columns(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == 'object' or df[col].dtype == 'string':
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
    return df