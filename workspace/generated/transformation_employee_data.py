import pandas as pd
import json
from pathlib import Path
from io import StringIO

try:
    bronze_path = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze\employee_data.csv'
    silver_path = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\silver\employee_data.csv'
    
    df = pd.read_csv(bronze_path)
    original_row_count = len(df)
    
    def camel_to_snake(name):
        result = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result.append('_')
                result.append(char.lower())
            else:
                result.append(char.lower())
        return ''.join(result)
    
    df.columns = [camel_to_snake(col) for col in df.columns]
    
    numeric_cols = ['salary', 'tenure', 'n_projects', 'avg_monthly_hrs', 'satisfaction', 'last_evaluation']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df['filed_complaint'] = df['filed_complaint'].astype('bool')
    df['recently_promoted'] = df['recently_promoted'].astype('bool')
    
    quarantine_list = []
    
    missing_mask = df.isnull().any(axis=1)
    quarantine_list.append(df[missing_mask].copy())
    df = df[~missing_mask]
    
    if len(df) > 0:
        dup_mask = df.duplicated(keep=False)
        quarantine_list.append(df[dup_mask].copy())
        df = df[~dup_mask]
    
    valid_rows = len(df)
    
    if len(quarantine_list) > 0:
        quarantine_df = pd.concat(quarantine_list, ignore_index=True)
        quarantine_df['quarantine_reason'] = 'Missing values or duplicates'
        quarantine_csv = quarantine_df.to_csv(index=False)
        quarantine_count = len(quarantine_df)
    else:
        quarantine_count = 0
        quarantine_csv = ''
    
    df.to_csv(silver_path, index=False)
    
    result = {
        'valid_rows': valid_rows,
        'quarantined_rows': quarantine_count,
        'quarantine_csv': quarantine_csv
    }
    print(json.dumps(result))

except Exception as e:
    error_result = {
        'status': 'ERROR',
        'errors': [str(e)]
    }
    print(json.dumps(error_result))
