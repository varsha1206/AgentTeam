import pandas as pd
import json
from pathlib import Path

try:
    # Load the transformed file
    temp_file = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_broken_employee_data.csv')
    silver_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\silver')
    quarantine_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine')
    
    silver_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(temp_file)
    
    # Define schema rules
    schema = {
        'id': {'type': 'int', 'nullable': False},
        'employeeName': {'type': 'str', 'nullable': False},
        'employeeAge': {'type': 'int', 'nullable': False, 'min': 0, 'max': 150},
        'salary': {'type': 'float', 'nullable': False, 'min': 0, 'max': 999999},
        'department': {'type': 'str', 'nullable': False},
        'unique_employee_id': {'type': 'str', 'nullable': False}
    }
    
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    for idx, row in df.iterrows():
        row_errors = []
        
        # Validate each column
        for col, rules in schema.items():
            if col not in df.columns:
                row_errors.append('Missing column: {}'.format(col))
                continue
            
            value = row[col]
            
            # Check nullability
            if pd.isna(value) or (isinstance(value, str) and value.strip() == ''):
                if not rules['nullable']:
                    row_errors.append('Column {} is non-nullable but got null'.format(col))
                continue
            
            # Type validation
            if rules['type'] == 'int':
                try:
                    val = int(value)
                    # Range validation
                    if 'min' in rules and val < rules['min']:
                        row_errors.append('Column {} value {} is below minimum {}'.format(col, val, rules['min']))
                    if 'max' in rules and val > rules['max']:
                        row_errors.append('Column {} value {} exceeds maximum {}'.format(col, val, rules['max']))
                except (ValueError, TypeError):
                    row_errors.append('Column {} has non-integer value: {}'.format(col, value))
            
            elif rules['type'] == 'float':
                try:
                    val = float(value)
                    # Range validation
                    if 'min' in rules and val < rules['min']:
                        row_errors.append('Column {} value {} is below minimum {}'.format(col, val, rules['min']))
                    if 'max' in rules and val > rules['max']:
                        row_errors.append('Column {} value {} exceeds maximum {}'.format(col, val, rules['max']))
                except (ValueError, TypeError):
                    row_errors.append('Column {} has non-float value: {}'.format(col, value))
            
            elif rules['type'] == 'str':
                if not isinstance(value, str):
                    row_errors.append('Column {} expected string but got {}'.format(col, type(value).__name__))
        
        # Categorize row
        if row_errors:
            row_dict = row.to_dict()
            row_dict['quarantine_reason'] = '; '.join(row_errors)
            quarantined_rows.append(row_dict)
            errors.extend(row_errors)
        else:
            valid_rows.append(row)
    
    # Write valid rows to silver
    silver_file = silver_dir / 'broken_employee_data.csv'
    if valid_rows:
        valid_df = pd.DataFrame(valid_rows)
        valid_df.to_csv(silver_file, index=False)
    else:
        # Write header only
        df[df.columns[:-0]].head(0).to_csv(silver_file, index=False)
    
    # Write quarantined rows
    if quarantined_rows:
        quarantine_file = quarantine_dir / 'quarantine_broken_employee_data.csv'
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_df.to_csv(quarantine_file, index=False)
    
    # Determine status
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
