import pandas as pd
from agentteam.models.structured_outputs import TransformationRule

def coerce_employee_age_to_int(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    df = df.copy()
    df['age'] = pd.to_numeric(df['age'], errors='coerce').fillna(0).astype(int)
    return df