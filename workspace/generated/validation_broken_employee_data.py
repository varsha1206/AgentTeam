import pandas as pd
import json
from pathlib import Path

try:
    transformed_file = Path('C:/Users/Varsha/OneDrive/Documents/Github/AgentTeam/workspace/temp/transformed_broken_employee_data.csv')
    silver_dir = Path('C:/Users/Varsha/OneDrive/Documents/Github/AgentTeam/workspace/output/silver')
    quarantine_dir = Path('C:/Users/Varsha/OneDrive/Documents/Github/AgentTeam/workspace/output/quarantine')
    
    silver_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(transformed_file)
    
    schema = {
        'id': {'type': 'int', 'nullable': False, 'min': None, 'max': None},
        'employeeName': {'type': 'str', 'nullable': False, 'min': None, 'max': None},
        'employeeAge': {'type': 'int', 'nullable': False, 'min': 0.0, 'max': 150.0},
        'salary': {'type': 'float', 'nullable': False, 'min': 0.0, 'max': 999999.0},
        'department': {'type': 'str', 'nullable': False, 'min': None, 'max': None}
    }
    
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    for idx, row in df.iterrows():
        row_errors = []
        
        for col, rules in schema.items():
            if col not in df.columns:
                row_errors.append(f'Column {col} missing')
                continue
            
            value = row[col]
            
            if pd.isna(value) or value == '':
                if not rules['nullable']:
                    row_errors.append(f'{col} is null but not nullable')
                continue
            
            if rules['type'] == 'int':
                try:
                    val = int(value)
                    if rules['min'] is not None and val < rules['min']:
                        row_errors.append(f'{col} value {val} below minimum {rules["min"]}')
                    if rules['max'] is not None and val > rules['max']:
                        row_errors.append(f'{col} value {val} above maximum {rules["max"]}')
                except (ValueError, TypeError):
                    row_errors.append(f'{col} cannot be converted to int: {value}')
            
            elif rules['type'] == 'float':
                try:
                    val = float(value)
                    if rules['min'] is not None and val < rules['min']:
                        row_errors.append(f'{col} value {val} below minimum {rules["min"]}')
                    if rules['max'] is not None and val > rules['max']:
                        row_errors.append(f'{col} value {val} above maximum {rules["max"]}')
                except (ValueError, TypeError):
                    row_errors.append(f'{col} cannot be converted to float: {value}')
            
            elif rules['type'] == 'str':
                if not isinstance(value, str):
                    row_errors.append(f'{col} is not a string: {type(value).__name__}')
        
        if row_errors:
            quarantine_row = row.copy()
            quarantine_row['quarantine_reason'] = '; '.join(row_errors)
            quarantined_rows.append(quarantine_row)
            errors.extend(row_errors)
        else:
            valid_rows.append(row)
    
    valid_df = pd.DataFrame(valid_rows) if valid_rows else df.iloc[0:0]
    quarantine_df = pd.DataFrame(quarantined_rows) if quarantined_rows else None
    
    silver_file = silver_dir / 'broken_employee_data.csv'
    valid_df.to_csv(silver_file, index=False)
    
    if quarantine_df is not None and len(quarantine_df) > 0:
        quarantine_file = quarantine_dir / 'quarantine_broken_employee_data.csv'
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