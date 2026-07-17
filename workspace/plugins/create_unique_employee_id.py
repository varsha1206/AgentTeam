import pandas as pd
import hashlib
from agentteam.models.structured_outputs import TransformationRule

def create_unique_employee_id(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    def generate_hash_id(row):
        row_str = ''.join(str(v) for v in row if pd.notna(v))
        return hashlib.md5(row_str.encode()).hexdigest()[:16]
    
    df['unique_employee_id'] = df.apply(generate_hash_id, axis=1)
    return df