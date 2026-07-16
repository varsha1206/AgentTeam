import pandas as pd
import hashlib
from agentteam.models.structured_outputs import TransformationRule

def create_unique_employee_id(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    def generate_hash_id(row):
        combined = str(row.get('employeeName', '')) + str(row.get('employeeAge', '')) + str(row.get('department', ''))
        return hashlib.md5(combined.encode()).hexdigest()[:16]
    
    df['employee_hash_id'] = df.apply(generate_hash_id, axis=1)
    return df