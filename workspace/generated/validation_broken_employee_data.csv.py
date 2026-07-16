import pandas as pd
import json
from pathlib import Path

try:
    input_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_broken_employee_data.csv'
    silver_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\silver\broken_employee_data.csv'
    quarantine_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine\quarantine_broken_employee_data.csv'
    
    df = pd.read_csv(input_file)
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    schema = {
        'id': {'type': 'int', 'nullable': False, 'min': None, 'max': None},
        'employeeName': {'type': 'str', 'nullable': True, 'min': None, 'max': None},
        'employeeAge': {'type': 'int', 'nullable': True, 'min': None, 'max': None},
        'salary': {'type': 'float', 'nullable': False, 'min': 0.0, 'max': None},
        'department': {'type': 'str', 'nullable': True, 'min': None, 'max': None}
    }
    
    for idx, row in df.iterrows():
        row_valid = True
        row_errors = []
        
        for col, col_rule in schema.items():
            if col not in df.columns:
                continue
            
            value = row[col]
            is_null = pd.isna(value) or (isinstance(value, str) and value.strip() == '')
            
            if is_null and not col_rule['nullable']:
                row_valid = False
                row_errors.append(f'Column {col} is non-nullable but has null value')
                continue
            
            if is_null:
                continue
            
            col_type = col_rule['type']
            
            if col_type == 'int':
                try:
                    int_val = int(float(str(value)))
                except (ValueError, TypeError):
                    row_valid = False
                    row_errors.append(f'Column {col} has non-integer value: {value}')
                    continue
            
            elif col_type == 'float':
                try:
                    float_val = float(str(value))
                    if col_rule['min'] is not None and float_val < col_rule['min']:
                        row_valid = False
                        row_errors.append(f'Column {col} value {float_val} is below minimum {col_rule["min"]}')
                except (ValueError, TypeError):
                    row_valid = False
                    row_errors.append(f'Column {col} has non-float value: {value}')
                    continue
            
            elif col_type == 'str':
                if not isinstance(value, str):
                    value = str(value)
        
        if row_valid:
            valid_rows.append(row)
        else:
            row_copy = row.copy()
            row_copy['quarantine_reason'] = '; '.join(row_errors)
            quarantined_rows.append(row_copy)
            errors.extend(row_errors)
    
    if valid_rows:
        valid_df = pd.DataFrame(valid_rows)
        valid_df.to_csv(silver_file, index=False)
    else:
        header_df = pd.DataFrame(columns=df.columns)
        header_df.to_csv(silver_file, index=False)
    
    if quarantined_rows:
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_df.to_csv(quarantine_file, index=False)
    
    status = 'PASS' if len(valid_rows) > 0 else 'FAIL'
    result = {
        'status': status,
        'valid_rows': len(valid_rows),
        'quarantined_rows': len(quarantined_rows),
        'errors': errors
    }
    print(json.dumps(result))
    
except Exception as e:
    print(json.dumps({'status': 'FAIL', 'valid_rows': 0, 'quarantined_rows': 0, 'errors': [str(e)]}))
