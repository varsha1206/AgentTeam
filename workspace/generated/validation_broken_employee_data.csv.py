import pandas as pd
import json
from pathlib import Path

try:
    temp_file = Path('C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\temp\\transformed_broken_employee_data.csv')
    silver_dir = Path('C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\output\\silver')
    quarantine_dir = Path('C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\output\\quarantine')
    
    silver_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(temp_file)
    
    schema = {
        'id': {'type': 'int', 'nullable': False},
        'employee_name': {'type': 'str', 'nullable': True},
        'employee_age': {'type': 'int', 'nullable': False},
        'salary': {'type': 'float', 'nullable': False},
        'department': {'type': 'str', 'nullable': False}
    }
    
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    for idx, row in df.iterrows():
        row_errors = []
        
        for col, rules in schema.items():
            if col not in df.columns:
                row_errors.append(f"Column {col} missing")
                continue
            
            value = row[col]
            
            if pd.isna(value):
                if not rules['nullable']:
                    row_errors.append(f"Column {col} is non-nullable but has null value")
            else:
                expected_type = rules['type']
                if expected_type == 'int':
                    try:
                        int(float(value))
                    except (ValueError, TypeError):
                        row_errors.append(f"Column {col} value '{value}' cannot be coerced to int")
                elif expected_type == 'float':
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        row_errors.append(f"Column {col} value '{value}' cannot be coerced to float")
                elif expected_type == 'str':
                    if not isinstance(value, str):
                        row_errors.append(f"Column {col} expected str but got {type(value).__name__}")
        
        if row_errors:
            row_copy = row.copy()
            row_copy['quarantine_reason'] = '; '.join(row_errors)
            quarantined_rows.append(row_copy)
            errors.append({'row': idx, 'reasons': row_errors})
        else:
            valid_rows.append(row)
    
    valid_df = pd.DataFrame(valid_rows) if valid_rows else df.iloc[:0]
    silver_file = silver_dir / 'validated_broken_employee_data.csv'
    valid_df.to_csv(silver_file, index=False)
    
    if quarantined_rows:
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_file = quarantine_dir / 'quarantine_broken_employee_data.csv'
        quarantine_df.to_csv(quarantine_file, index=False)
    
    valid_count = len(valid_rows)
    quarantine_count = len(quarantined_rows)
    status = 'PASS' if valid_count > 0 else 'FAIL'
    
    result = {
        'status': status,
        'valid_rows': valid_count,
        'quarantined_rows': quarantine_count,
        'errors': errors
    }
    
    print(json.dumps(result))

except Exception as e:
    error_result = {
        'status': 'FAIL',
        'valid_rows': 0,
        'quarantined_rows': 0,
        'errors': [{'error': str(e)}]
    }
    print(json.dumps(error_result))