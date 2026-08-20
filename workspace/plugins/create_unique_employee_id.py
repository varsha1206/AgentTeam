import pandas as pd
from agentteam.models.structured_outputs import TransformationRule

def create_unique_employee_id(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    df = df.copy()
    df['employee_id'] = df['id'].astype(str).str.zfill(6)
    return df