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
    
    # Schema adjusted for snake_case column names from transformation
    schema = {
        'id': {'type': 'int', 'nullable': False},
        'employee_name': {'type': 'str', 'nullable': False},
        'employee_age': {'type': 'int', 'nullable': False, 'min': 0, 'max': 150},
        'salary': {'type': 'float', 'nullable': False, 'min': 0.0, 'max': 999999.0},
        'department': {'type': 'str', 'nullable': False},
        'unique_employee_id': {'type': 'str', 'nullable': False}
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
            
            # Check for null/empty values
            if pd.isna(value) or str(value).strip() == '':
                if not rules['nullable']:
                    row_errors.append(f'{col} is null but not nullable')
                continue
            
            # Type checking and conversion
            if rules['type'] == 'int':
                try:
                    val = int(value)
                    if 'min' in rules and rules['min'] is not None and val < rules['min']:
                        row_errors.append(f'{col} value {val} below minimum {rules["min"]}')
                    if 'max' in rules and rules['max'] is not None and val > rules['max']:
                        row_errors.append(f'{col} value {val} above maximum {rules["max"]}')
                except (ValueError, TypeError):
                    row_errors.append(f'{col} cannot be converted to int: {value}')
            
            elif rules['type'] == 'float':
                try:
                    val = float(value)
                    if 'min' in rules and rules['min'] is not None and val < rules['min']:
                        row_errors.append(f'{col} value {val} below minimum {rules["min"]}')
                    if 'max' in rules and rules['max'] is not None and val > rules['max']:
                        row_errors.append(f'{col} value {val} above maximum {rules["max"]}')
                except (ValueError, TypeError):
                    row_errors.append(f'{col} cannot be converted to float: {value}')
            
            elif rules['type'] == 'str':
                if not isinstance(value, str):
                    try:
                        str(value)
                    except:
                        row_errors.append(f'{col} cannot be converted to string: {type(value).__name__}')
        
        if row_errors:
            quarantine_row = row.copy()
            quarantine_row['quarantine_reason'] = '; '.join(row_errors)
            quarantined_rows.append(quarantine_row)
            errors.extend(row_errors)
        else:
            valid_rows.append(row)
    
    valid_df = pd.DataFrame(valid_rows) if valid_rows else df.iloc[0:0]
    
    silver_file = silver_dir / 'broken_employee_data.csv'
    valid_df.to_csv(silver_file, index=False)
    
    output_file = Path('C:/Users/Varsha/OneDrive/Documents/Github/AgentTeam/workspace/temp/transformed_broken_employee_data.csv')
    valid_df.to_csv(output_file, index=False)
    
    if quarantined_rows:
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_file = quarantine_dir / 'quarantine_broken_employee_data.csv'
        quarantine_df.to_csv(quarantine_file, index=False)
    
    quarantine_path = str(quarantine_dir / 'quarantine_broken_employee_data.csv') if quarantined_rows else None
    
    result = {
        'valid_rows': len(valid_rows),
        'quarantined_rows': len(quarantined_rows),
        'quarantine_path': quarantine_path
    }
    
    print(json.dumps(result))

except Exception as e:
    error_result = {
        'valid_rows': 0,
        'quarantined_rows': 0,
        'quarantine_path': None,
        'error': str(e)
    }
    print(json.dumps(error_result))