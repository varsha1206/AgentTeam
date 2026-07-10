import pandas as pd
import hashlib
from agentteam.models.structured_outputs import TransformationRule

def create_unique_employee_id(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    def generate_hash(row):
        id_val = row.get('id', '')
        name_val = row.get('employeeName', '')
        age_val = row.get('employeeAge', '')
        combined = str(id_val) + str(name_val) + str(age_val)
        return hashlib.md5(combined.encode()).hexdigest()[:12]
    
    df['unique_employee_id'] = df.apply(generate_hash, axis=1)
    return df