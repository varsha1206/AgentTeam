import pandas as pd
import hashlib
from agentteam.models.structured_outputs import TransformationRule

def create_unique_employee_id(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    df_copy = df.copy()
    hash_ids = []
    for idx, row in df_copy.iterrows():
        row_str = '_'.join(str(v) for v in row.values)
        hash_id = hashlib.md5(row_str.encode()).hexdigest()[:8]
        hash_ids.append(hash_id)
    df_copy['unique_employee_id'] = hash_ids
    return df_copy