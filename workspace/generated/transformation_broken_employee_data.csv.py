import pandas as pd
import json
from pathlib import Path

try:
    bronze_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze\broken_employee_data.csv'
    temp_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp')
    quarantine_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine')
    
    temp_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(bronze_file)
    original_count = len(df)
    
    quarantined = []
    valid_rows = []
    
    for idx, row in df.iterrows():
        reason = None
        
        if pd.isna(row['id']) or pd.isna(row['name']) or pd.isna(row['department']):
            reason = 'Missing critical field (id, name, or department)'
        elif pd.isna(row['age']):
            reason = 'Missing age'
        elif pd.isna(row['salary']):
            reason = 'Missing salary'
        
        if reason is None:
            try:
                age_val = int(float(str(row['age']).strip()))
                if age_val < 0 or age_val > 120:
                    reason = 'Age out of valid range (0-120)'
            except:
                reason = 'Invalid age format'
        
        if reason is None:
            try:
                salary_val = float(str(row['salary']).strip())
                if salary_val < 0:
                    reason = 'Negative salary'
            except:
                reason = 'Invalid salary format'
        
        if reason is not None:
            row_dict = row.to_dict()
            row_dict['quarantine_reason'] = reason
            quarantined.append(row_dict)
        else:
            valid_rows.append(row)
    
    valid_df = pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)
    
    temp_file = temp_dir / 'transformed_broken_employee_data.csv'
    valid_df.to_csv(temp_file, index=False)
    
    if quarantined:
        quarantine_df = pd.DataFrame(quarantined)
        quarantine_file = quarantine_dir / 'quarantine_broken_employee_data.csv'
        quarantine_df.to_csv(quarantine_file, index=False)
        quarantine_path = str(quarantine_file)
    else:
        quarantine_path = str(quarantine_dir / 'quarantine_broken_employee_data.csv')
    
    result = {
        'valid_rows': len(valid_rows),
        'quarantined_rows': len(quarantined),
        'quarantine_path': quarantine_path
    }
    print(json.dumps(result))
    
except Exception as e:
    print(json.dumps({'status': 'ERROR', 'message': str(e)}))
