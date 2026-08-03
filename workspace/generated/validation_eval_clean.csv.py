import pandas as pd
import json
from pathlib import Path

try:
    # Read the transformed file
    transformed_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_eval_clean.csv'
    df = pd.read_csv(transformed_file)
    
    # Define schema rules
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
        row_valid = True
        quarantine_reason = []
        
        for col, rule in schema.items():
            if col not in row.index:
                row_valid = False
                quarantine_reason.append(f'Column {col} missing')
                continue
            
            value = row[col]
            
            # Check nullable constraint
            if pd.isna(value):
                if not rule['nullable']:
                    row_valid = False
                    quarantine_reason.append(f'Column {col} is null but not nullable')
                continue
            
            # Type validation
            try:
                if rule['type'] == 'int':
                    if not isinstance(value, (int, float)) or (isinstance(value, float) and value != int(value)):
                        if str(value).strip() != '':
                            int(value)
                    typed_value = int(value)
                elif rule['type'] == 'float':
                    typed_value = float(value)
                elif rule['type'] == 'str':
                    typed_value = str(value)
                else:
                    typed_value = value
            except (ValueError, TypeError):
                row_valid = False
                quarantine_reason.append(f'Column {col} type mismatch: expected {rule["type"]}, got {type(value).__name__}')
                continue
            
            # Range validation
            if rule['min'] is not None and typed_value < rule['min']:
                row_valid = False
                quarantine_reason.append(f'Column {col} value {typed_value} below minimum {rule["min"]}')
            
            if rule['max'] is not None and typed_value > rule['max']:
                row_valid = False
                quarantine_reason.append(f'Column {col} value {typed_value} above maximum {rule["max"]}')
        
        if row_valid:
            valid_rows.append(row)
        else:
            quarantined_row = row.copy()
            quarantined_row['quarantine_reason'] = '; '.join(quarantine_reason)
            quarantined_rows.append(quarantined_row)
    
    # Write valid rows to silver
    silver_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\silver\eval_clean.csv'
    Path(silver_file).parent.mkdir(parents=True, exist_ok=True)
    if valid_rows:
        valid_df = pd.DataFrame(valid_rows)
        valid_df.to_csv(silver_file, index=False)
    else:
        df.iloc[:0].to_csv(silver_file, index=False)
    
    # Write quarantined rows
    quarantine_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine\quarantine_eval_clean.csv'
    Path(quarantine_file).parent.mkdir(parents=True, exist_ok=True)
    if quarantined_rows:
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_df.to_csv(quarantine_file, index=False)
    else:
        quarantine_df = df.iloc[:0].copy()
        quarantine_df['quarantine_reason'] = ''
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
