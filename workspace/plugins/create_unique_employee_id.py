import pandas as pd
import hashlib
from agentteam.models.structured_outputs import TransformationRule

def create_unique_employee_id(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    df = df.copy()
    
    def generate_hash(row):
        combined = str(row.get('id', '')) + str(row.get('employee_name', '')) + str(row.get('employee_age', ''))
        return hashlib.md5(combined.encode()).hexdigest()[:16]
    
    df['unique_employee_id'] = df.apply(generate_hash, axis=1)
    return df