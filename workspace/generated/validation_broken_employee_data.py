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
        'employeeName': {'type': 'str', 'nullable': True, 'min': None, 'max': None},
        'employeeAge': {'type': 'int', 'nullable': True, 'min': None, 'max': None},
        'salary': {'type': 'float', 'nullable': False, 'min': 0.0, 'max': None},
        'department': {'type': 'str', 'nullable': False, 'min': None, 'max': None}
    }
    
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    for idx, row in df.iterrows():
        row_valid = True
        row_errors = []
        
        for col, col_schema in schema.items():
            if col not in df.columns:
                continue
            
            value = row[col]
            is_null = pd.isna(value)
            
            if is_null and not col_schema['nullable']:
                row_valid = False
                row_errors.append(f"Column {col}: null value not allowed")
                continue
            
            if is_null:
                continue
            
            if col_schema['type'] == 'int':
                try:
                    int_val = int(float(str(value)))
                    if col_schema['min'] is not None and int_val < col_schema['min']:
                        row_valid = False
                        row_errors.append(f"Column {col}: value {value} below minimum {col_schema['min']}")
                    if col_schema['max'] is not None and int_val > col_schema['max']:
                        row_valid = False
                        row_errors.append(f"Column {col}: value {value} above maximum {col_schema['max']}")
                except (ValueError, TypeError):
                    row_valid = False
                    row_errors.append(f"Column {col}: cannot convert '{value}' to int")
            
            elif col_schema['type'] == 'float':
                try:
                    float_val = float(value)
                    if col_schema['min'] is not None and float_val < col_schema['min']:
                        row_valid = False
                        row_errors.append(f"Column {col}: value {value} below minimum {col_schema['min']}")
                    if col_schema['max'] is not None and float_val > col_schema['max']:
                        row_valid = False
                        row_errors.append(f"Column {col}: value {value} above maximum {col_schema['max']}")
                except (ValueError, TypeError):
                    row_valid = False
                    row_errors.append(f"Column {col}: cannot convert '{value}' to float")
            
            elif col_schema['type'] == 'str':
                if not isinstance(value, str):
                    row_valid = False
                    row_errors.append(f"Column {col}: expected str, got {type(value).__name__}")
        
        if row_valid:
            valid_rows.append(row.to_dict())
        else:
            quarantine_row = row.to_dict()
            quarantine_row['quarantine_reason'] = '; '.join(row_errors)
            quarantined_rows.append(quarantine_row)
            errors.extend(row_errors)
    
    valid_df = pd.DataFrame(valid_rows) if valid_rows else df[0:0]
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