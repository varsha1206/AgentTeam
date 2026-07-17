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
        'salary': {'type': 'float', 'nullable': False, 'min': 0.0, 'max': None},
        'employeeName': {'type': 'str', 'nullable': True},
        'employeeAge': {'type': 'str', 'nullable': True},
        'department': {'type': 'str', 'nullable': True}
    }
    
    valid_rows = []
    quarantine_rows = []
    errors = []
    
    for idx, row in df.iterrows():
        row_errors = []
        
        for col, col_rule in schema.items():
            if col not in df.columns:
                continue
            
            value = row[col]
            is_null = pd.isna(value) or (isinstance(value, str) and value.strip() == '')
            
            if is_null and not col_rule['nullable']:
                row_errors.append(f"Column {col} is non-nullable but got null")
            elif not is_null:
                if col_rule['type'] == 'int':
                    try:
                        int_val = int(float(value))
                    except (ValueError, TypeError):
                        row_errors.append(f"Column {col} expected int but got {value}")
                elif col_rule['type'] == 'float':
                    try:
                        float_val = float(value)
                        if col_rule['min'] is not None and float_val < col_rule['min']:
                            row_errors.append(f"Column {col} value {float_val} is less than min {col_rule['min']}")
                    except (ValueError, TypeError):
                        row_errors.append(f"Column {col} expected float but got {value}")
                elif col_rule['type'] == 'str':
                    if not isinstance(value, str):
                        try:
                            str(value)
                        except:
                            row_errors.append(f"Column {col} cannot be converted to string")
        
        if row_errors:
            quarantine_rows.append({**row.to_dict(), 'quarantine_reason': '; '.join(row_errors)})
            errors.extend(row_errors)
        else:
            valid_rows.append(row.to_dict())
    
    if valid_rows:
        valid_df = pd.DataFrame(valid_rows)
        valid_df.to_csv(silver_dir / 'broken_employee_data.csv', index=False)
    else:
        valid_df = pd.DataFrame(columns=df.columns)
        valid_df.to_csv(silver_dir / 'broken_employee_data.csv', index=False)
    
    if quarantine_rows:
        quarantine_df = pd.DataFrame(quarantine_rows)
        quarantine_df.to_csv(quarantine_dir / 'quarantine_broken_employee_data.csv', index=False)
    
    status = 'PASS' if len(valid_rows) > 0 else 'FAIL'
    print(json.dumps({
        'status': status,
        'valid_rows': len(valid_rows),
        'quarantined_rows': len(quarantine_rows),
        'errors': errors
    }))

except Exception as e:
    print(json.dumps({
        'status': 'FAIL',
        'valid_rows': 0,
        'quarantined_rows': 0,
        'errors': [str(e)]
    }))