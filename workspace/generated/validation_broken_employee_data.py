import pandas as pd
import json
from pathlib import Path

try:
    transformed_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_broken_employee_data.csv'
    silver_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\silver')
    quarantine_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine')
    
    silver_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(transformed_file)
    
    schema = {
        'id': {'type': 'int', 'nullable': False, 'min': None, 'max': None},
        'employeeName': {'type': 'str', 'nullable': True, 'min': None, 'max': None},
        'employeeAge': {'type': 'int', 'nullable': True, 'min': 0.0, 'max': None},
        'salary': {'type': 'float', 'nullable': False, 'min': 0.0, 'max': None},
        'department': {'type': 'str', 'nullable': True, 'min': None, 'max': None}
    }
    
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    for idx, row in df.iterrows():
        row_errors = []
        is_valid = True
        
        for col, rules in schema.items():
            if col not in df.columns:
                continue
            
            value = row[col]
            
            if pd.isna(value):
                if not rules['nullable']:
                    row_errors.append('Column ' + col + ' is not nullable but contains null')
                    is_valid = False
                continue
            
            if rules['type'] == 'int':
                if not isinstance(value, (int, pd.Int64Dtype)) and not (isinstance(value, float) and value == int(value)):
                    row_errors.append('Column ' + col + ' should be int but got ' + str(type(value)))
                    is_valid = False
            elif rules['type'] == 'float':
                if not isinstance(value, (int, float)):
                    row_errors.append('Column ' + col + ' should be float but got ' + str(type(value)))
                    is_valid = False
            elif rules['type'] == 'str':
                if not isinstance(value, str):
                    row_errors.append('Column ' + col + ' should be str but got ' + str(type(value)))
                    is_valid = False
            
            if rules['min'] is not None and not pd.isna(value):
                try:
                    if float(value) < rules['min']:
                        row_errors.append('Column ' + col + ' value ' + str(value) + ' is less than minimum ' + str(rules['min']))
                        is_valid = False
                except (ValueError, TypeError):
                    pass
            
            if rules['max'] is not None and not pd.isna(value):
                try:
                    if float(value) > rules['max']:
                        row_errors.append('Column ' + col + ' value ' + str(value) + ' exceeds maximum ' + str(rules['max']))
                        is_valid = False
                except (ValueError, TypeError):
                    pass
        
        if is_valid:
            valid_rows.append(row)
        else:
            quarantine_row = row.copy()
            quarantine_row['quarantine_reason'] = '; '.join(row_errors)
            quarantined_rows.append(quarantine_row)
            errors.extend(row_errors)
    
    silver_file = silver_dir / 'broken_employee_data.csv'
    quarantine_file = quarantine_dir / 'quarantine_broken_employee_data.csv'
    
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
    error_result = {
        'status': 'FAIL',
        'valid_rows': 0,
        'quarantined_rows': 0,
        'errors': [str(e)]
    }
    print(json.dumps(error_result))