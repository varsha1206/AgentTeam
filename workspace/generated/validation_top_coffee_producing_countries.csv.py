import pandas as pd
import json
from pathlib import Path

try:
    transformed_file = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_top_coffee_producing_countries.csv')
    silver_file = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\silver\top_coffee_producing_countries.csv')
    quarantine_file = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine\quarantine_top_coffee_producing_countries.csv')
    
    df = pd.read_csv(transformed_file)
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    schema = {
        'country': {'type': 'str', 'nullable': False, 'min': None, 'max': None},
        'major_regions': {'type': 'str', 'nullable': False, 'min': None, 'max': None},
        'percentage_of_world_production': {'type': 'float', 'nullable': False, 'min': 0.0, 'max': 100.0}
    }
    
    for idx, row in df.iterrows():
        row_errors = []
        
        for col, rules in schema.items():
            value = row[col]
            
            if pd.isna(value):
                if not rules['nullable']:
                    row_errors.append(f"Column '{col}' is non-nullable but has null value")
            else:
                if rules['type'] == 'float':
                    try:
                        float_val = float(value)
                        if rules['min'] is not None and float_val < rules['min']:
                            row_errors.append(f"Column '{col}' value {float_val} is below minimum {rules['min']}")
                        if rules['max'] is not None and float_val > rules['max']:
                            row_errors.append(f"Column '{col}' value {float_val} exceeds maximum {rules['max']}")
                    except (ValueError, TypeError):
                        row_errors.append(f"Column '{col}' value '{value}' cannot be coerced to float")
                elif rules['type'] == 'str':
                    if not isinstance(value, str):
                        row_errors.append(f"Column '{col}' value '{value}' is not a string")
        
        if row_errors:
            quarantine_reason = '; '.join(row_errors)
            row_with_reason = row.copy()
            row_with_reason['quarantine_reason'] = quarantine_reason
            quarantined_rows.append(row_with_reason)
            errors.append(quarantine_reason)
        else:
            valid_rows.append(row)
    
    valid_df = pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)
    valid_df.to_csv(silver_file, index=False)
    
    if quarantined_rows:
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_df.to_csv(quarantine_file, index=False)
    
    status = 'PASS' if len(valid_rows) > 0 else 'FAIL'
    output = {
        'status': status,
        'valid_rows': len(valid_rows),
        'quarantined_rows': len(quarantined_rows),
        'errors': errors
    }
    print(json.dumps(output))

except Exception as e:
    print(json.dumps({'status': 'FAIL', 'valid_rows': 0, 'quarantined_rows': 0, 'errors': [str(e)]}))