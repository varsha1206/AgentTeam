import pandas as pd
from agentteam.models.structured_outputs import TransformationRule

def normalize_department_name(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    df = df.copy()
    df['department'] = df['department'].str.strip().str.upper()
    return df