import pandas as pd
import json
from pathlib import Path

try:
    # Read transformed file
    input_file = Path('C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\temp\\transformed_broken_employee_data.csv')
    df = pd.read_csv(input_file)
    
    # Define schema rules
    schema = {
        'id': {'type': 'int', 'nullable': False, 'min': None, 'max': None},
        'employeeName': {'type': 'str', 'nullable': True, 'min': None, 'max': None},
        'employeeAge': {'type': 'str', 'nullable': True, 'min': None, 'max': None},
        'salary': {'type': 'float', 'nullable': False, 'min': 0.0, 'max': None},
        'department': {'type': 'str', 'nullable': True, 'min': None, 'max': None}
    }
    
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    for idx, row in df.iterrows():
        row_errors = []
        
        # Check id (int, non-nullable)
        if pd.isna(row['id']):
            row_errors.append('id is null but nullable=false')
        else:
            try:
                int(row['id'])
            except (ValueError, TypeError):
                row_errors.append('id is not int type')
        
        # Check employeeName (str, nullable)
        if not pd.isna(row['employeeName']):
            if not isinstance(row['employeeName'], str):
                row_errors.append('employeeName is not str type')
        
        # Check employeeAge (str, nullable)
        if not pd.isna(row['employeeAge']):
            if not isinstance(row['employeeAge'], str):
                row_errors.append('employeeAge is not str type')
        
        # Check salary (float, non-nullable, min 0.0)
        if pd.isna(row['salary']):
            row_errors.append('salary is null but nullable=false')
        else:
            try:
                sal_val = float(row['salary'])
                if sal_val < 0.0:
                    row_errors.append('salary is less than min value 0.0')
            except (ValueError, TypeError):
                row_errors.append('salary is not float type')
        
        # Check department (str, nullable)
        if not pd.isna(row['department']):
            if not isinstance(row['department'], str):
                row_errors.append('department is not str type')
        
        if row_errors:
            row_copy = row.copy()
            row_copy['quarantine_reason'] = '; '.join(row_errors)
            quarantined_rows.append(row_copy)
            errors.extend(row_errors)
        else:
            valid_rows.append(row)
    
    # Convert valid rows back to dataframe
    if valid_rows:
        valid_df = pd.DataFrame(valid_rows)
    else:
        valid_df = pd.DataFrame(columns=df.columns)
    
    # Write valid rows to silver
    silver_file = Path('C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\output\\silver\\broken_employee_data.csv')
    silver_file.parent.mkdir(parents=True, exist_ok=True)
    valid_df.to_csv(silver_file, index=False)
    
    # Write quarantined rows if any
    if quarantined_rows:
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_file = Path('C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\output\\quarantine\\quarantine_broken_employee_data.csv')
        quarantine_file.parent.mkdir(parents=True, exist_ok=True)
        quarantine_df.to_csv(quarantine_file, index=False)
    
    status = 'PASS' if len(valid_rows) > 0 else 'FAIL'
    result = {
        'status': status,
        'valid_rows': len(valid_rows),
        'quarantined_rows': len(quarantined_rows),
        'errors': list(set(errors))
    }
    print(json.dumps(result))
    
except Exception as e:
    error_result = {
        'status': 'FAIL',
        'valid_rows': 0,
        'quarantined_rows': 0,
        'errors': [str(e)]
    }
    print(json.dumps(error_result))
