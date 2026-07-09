import pandas as pd
import json
from pathlib import Path

try:
    temp_path = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_broken_employee_data.csv')
    silver_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\silver')
    quarantine_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine')
    
    silver_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(temp_path)
    
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    schema = {
        'id': {'type': 'int', 'nullable': False},
        'employee_name': {'type': 'str', 'nullable': True},
        'employee_age': {'type': 'int', 'nullable': True, 'min': 18, 'max': 65},
        'salary': {'type': 'float', 'nullable': False, 'min': 0},
        'department': {'type': 'str', 'nullable': False}
    }
    
    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        quarantine_reason = None
        
        for col_name, col_rules in schema.items():
            value = row_dict.get(col_name)
            
            if pd.isna(value) or value is None:
                if not col_rules['nullable']:
                    quarantine_reason = 'Non-nullable column {0} contains null'.format(col_name)
                    break
            else:
                expected_type = col_rules['type']
                
                if expected_type == 'int':
                    if not isinstance(value, (int, float)) or (isinstance(value, float) and pd.isna(value)):
                        quarantine_reason = 'Column {0} has type mismatch: expected int'.format(col_name)
                        break
                elif expected_type == 'float':
                    if not isinstance(value, (int, float)) or (isinstance(value, float) and pd.isna(value)):
                        quarantine_reason = 'Column {0} has type mismatch: expected float'.format(col_name)
                        break
                elif expected_type == 'str':
                    if not isinstance(value, str):
                        quarantine_reason = 'Column {0} has type mismatch: expected str'.format(col_name)
                        break
                
                if 'min' in col_rules and not pd.isna(value):
                    if value < col_rules['min']:
                        quarantine_reason = 'Column {0} value {1} is below minimum {2}'.format(col_name, value, col_rules['min'])
                        break
                
                if 'max' in col_rules and not pd.isna(value):
                    if value > col_rules['max']:
                        quarantine_reason = 'Column {0} value {1} is above maximum {2}'.format(col_name, value, col_rules['max'])
                        break
        
        if quarantine_reason:
            row_dict['quarantine_reason'] = quarantine_reason
            quarantined_rows.append(row_dict)
            errors.append(quarantine_reason)
        else:
            valid_rows.append(row_dict)
    
    valid_df = pd.DataFrame(valid_rows)
    if not valid_df.empty:
        valid_df.to_csv(silver_dir / 'broken_employee_data.csv', index=False)
    
    if quarantined_rows:
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_df.to_csv(quarantine_dir / 'quarantine_broken_employee_data.csv', index=False)
    
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