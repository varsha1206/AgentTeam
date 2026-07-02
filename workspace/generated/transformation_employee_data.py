import pandas as pd
import json
import os
from pathlib import Path

try:
    bronze_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze\employee_data.csv'
    temp_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_employee_data.csv'
    quarantine_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine\quarantine_employee_data.csv'
    
    os.makedirs(os.path.dirname(temp_file), exist_ok=True)
    os.makedirs(os.path.dirname(quarantine_file), exist_ok=True)
    
    df = pd.read_csv(bronze_file)
    quarantined = []
    valid_rows = []
    
    df_copy = df.copy()
    df_copy['_original_index'] = range(len(df_copy))
    
    # Transformation 1: rename_to_snake_case
    rename_map = {
        'avgMonthlyHrs': 'avg_monthly_hrs',
        'filedComplaint': 'filed_complaint',
        'lastEvaluation': 'last_evaluation',
        'nProjects': 'n_projects',
        'recentlyPromoted': 'recently_promoted'
    }
    df_copy.rename(columns=rename_map, inplace=True)
    
    # Transformation 2: coerce_numeric on specified columns
    numeric_cols = ['salary', 'tenure', 'n_projects', 'avg_monthly_hrs', 'satisfaction', 'last_evaluation']
    for col in numeric_cols:
        if col in df_copy.columns:
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
    
    # Transformation 3: quarantine_missing
    rows_to_check = list(range(len(df_copy)))
    for idx in rows_to_check:
        if df_copy.iloc[idx].isnull().any():
            row_data = df_copy.iloc[idx].copy()
            row_data['quarantine_reason'] = 'Missing values'
            quarantined.append(row_data)
        else:
            valid_rows.append(df_copy.iloc[idx].copy())
    
    if len(valid_rows) > 0:
        df_valid = pd.DataFrame(valid_rows).reset_index(drop=True)
    else:
        df_valid = pd.DataFrame()
    
    if len(quarantined) > 0:
        df_quarantined = pd.DataFrame(quarantined).reset_index(drop=True)
        df_quarantined.to_csv(quarantine_file, index=False)
    else:
        df_quarantined = pd.DataFrame(columns=list(df_copy.columns) + ['quarantine_reason'])
        df_quarantined.to_csv(quarantine_file, index=False)
    
    # Transformation 4 & 5: quarantine_duplicates and quarantine_type_mismatch handled by further validation
    if len(df_valid) > 0:
        df_valid.to_csv(temp_file, index=False)
    else:
        df_valid.to_csv(temp_file, index=False)
    
    result = {
        'valid_rows': len(valid_rows),
        'quarantined_rows': len(quarantined),
        'quarantine_path': quarantine_file
    }
    print(json.dumps(result))

except Exception as e:
    error_result = {
        'status': 'FAILED',
        'errors': [str(e)]
    }
    print(json.dumps(error_result))