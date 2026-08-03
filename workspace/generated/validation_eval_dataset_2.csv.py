import pandas as pd
import json
from pathlib import Path

try:
    # Paths
    temp_file = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_eval_dataset_2.csv')
    silver_file = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\silver\eval_dataset_2.csv')
    quarantine_file = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine\quarantine_eval_dataset_2.csv')
    
    # Create output directories if needed
    silver_file.parent.mkdir(parents=True, exist_ok=True)
    quarantine_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Read transformed data
    df = pd.read_csv(temp_file)
    
    # Define schema validation rules
    schema = {
        'id': {'type': 'int', 'nullable': False, 'min': None, 'max': None},
        'name': {'type': 'str', 'nullable': False, 'min': None, 'max': None},
        'age': {'type': 'int', 'nullable': False, 'min': 18.0, 'max': 70.0},
        'salary': {'type': 'float', 'nullable': False, 'min': 0.0, 'max': None},
        'department': {'type': 'str', 'nullable': False, 'min': None, 'max': None}
    }
    
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    # Validate each row
    for idx, row in df.iterrows():
        row_errors = []
        
        # Check each column against schema
        for col, rule in schema.items():
            if col not in df.columns:
                continue
            
            value = row[col]
            
            # Check nullability
            if pd.isna(value):
                if not rule['nullable']:
                    row_errors.append(f"Column '{col}' is not nullable but has null value")
                continue
            
            # Check type
            if rule['type'] == 'int':
                try:
                    if not pd.api.types.is_integer(value):
                        row_errors.append(f"Column '{col}' expected int but got {type(value).__name__}")
                except:
                    row_errors.append(f"Column '{col}' type validation failed")
            elif rule['type'] == 'float':
                try:
                    float_val = float(value)
                except:
                    row_errors.append(f"Column '{col}' expected float but cannot convert")
            elif rule['type'] == 'str':
                if not isinstance(value, str):
                    row_errors.append(f"Column '{col}' expected str but got {type(value).__name__}")
            
            # Check min/max constraints
            if rule['min'] is not None and not pd.isna(value):
                try:
                    if float(value) < rule['min']:
                        row_errors.append(f"Column '{col}' value {value} is less than minimum {rule['min']}")
                except:
                    pass
            
            if rule['max'] is not None and not pd.isna(value):
                try:
                    if float(value) > rule['max']:
                        row_errors.append(f"Column '{col}' value {value} is greater than maximum {rule['max']}")
                except:
                    pass
        
        # Categorize row
        if row_errors:
            quarantine_row = row.copy()
            quarantine_row['quarantine_reason'] = '; '.join(row_errors)
            quarantined_rows.append(quarantine_row)
            errors.extend(row_errors)
        else:
            valid_rows.append(row)
    
    # Write valid rows to silver
    if valid_rows:
        valid_df = pd.DataFrame(valid_rows)
        valid_df.to_csv(silver_file, index=False)
    else:
        # Write header only if no valid rows
        df.iloc[:0].to_csv(silver_file, index=False)
    
    # Write quarantined rows if any
    if quarantined_rows:
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_df.to_csv(quarantine_file, index=False)
    
    # Determine status
    status = 'PASS' if len(valid_rows) > 0 else 'FAIL'
    
    # Print result as JSON
    result = {
        'status': status,
        'valid_rows': len(valid_rows),
        'quarantined_rows': len(quarantined_rows),
        'errors': list(set(errors))
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
