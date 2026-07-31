import pandas as pd
import json
from pathlib import Path

try:
    # Read the transformed file
    input_file = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_broken_employee_data.csv')
    df = pd.read_csv(input_file)
    
    # Define schema rules
    schema = {
        'id': {'type': 'int', 'nullable': False, 'min': None, 'max': None},
        'salary': {'type': 'float', 'nullable': False, 'min': 0.0, 'max': None},
        'employeeName': {'type': 'str', 'nullable': False, 'min': None, 'max': None},
        'employeeAge': {'type': 'int', 'nullable': False, 'min': 0.0, 'max': None},
        'department': {'type': 'str', 'nullable': True, 'min': None, 'max': None}
    }
    
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    for idx, row in df.iterrows():
        row_errors = []
        
        # Check each column against schema
        for col, rule in schema.items():
            if col not in df.columns:
                continue
                
            value = row[col]
            
            # Check nullable constraint
            if pd.isna(value) or (isinstance(value, str) and value.strip() == ''):
                if not rule['nullable']:
                    row_errors.append(f"Column '{col}' is non-nullable but has null/empty value")
                continue
            
            # Check type
            if rule['type'] == 'int':
                try:
                    int_val = int(float(str(value)))
                except (ValueError, TypeError):
                    row_errors.append(f"Column '{col}' expected int but got '{value}'")
                    continue
                # Check min constraint
                if rule['min'] is not None and int_val < rule['min']:
                    row_errors.append(f"Column '{col}' value {int_val} is below minimum {rule['min']}")
            
            elif rule['type'] == 'float':
                try:
                    float_val = float(str(value))
                except (ValueError, TypeError):
                    row_errors.append(f"Column '{col}' expected float but got '{value}'")
                    continue
                # Check min constraint
                if rule['min'] is not None and float_val < rule['min']:
                    row_errors.append(f"Column '{col}' value {float_val} is below minimum {rule['min']}")
            
            elif rule['type'] == 'str':
                if not isinstance(value, str):
                    try:
                        str(value)
                    except:
                        row_errors.append(f"Column '{col}' expected str but got {type(value).__name__}")
        
        if row_errors:
            quarantine_reason = "; ".join(row_errors)
            quarantine_row = row.copy()
            quarantine_row['quarantine_reason'] = quarantine_reason
            quarantined_rows.append(quarantine_row)
            errors.extend(row_errors)
        else:
            valid_rows.append(row)
    
    # Write valid rows to silver
    silver_file = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\silver\broken_employee_data.csv')
    silver_file.parent.mkdir(parents=True, exist_ok=True)
    if valid_rows:
        valid_df = pd.DataFrame(valid_rows)
        valid_df.to_csv(silver_file, index=False)
    else:
        # Write header only if no valid rows
        df_header = df.iloc[:0]
        df_header.to_csv(silver_file, index=False)
    
    # Write quarantined rows to quarantine
    quarantine_file = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine\quarantine_broken_employee_data.csv')
    quarantine_file.parent.mkdir(parents=True, exist_ok=True)
    if quarantined_rows:
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_df.to_csv(quarantine_file, index=False)
    
    # Determine status
    status = 'PASS' if len(valid_rows) > 0 else 'FAIL'
    
    # Print result
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
