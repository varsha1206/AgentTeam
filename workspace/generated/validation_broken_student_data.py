import pandas as pd
import json
from pathlib import Path

def main():
    try:
        input_file = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_broken_student_data.csv')
        silver_file = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\silver\broken_student_data.csv')
        quarantine_file = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine\quarantine_broken_student_data.csv')
        
        df = pd.read_csv(input_file)
        
        schema = {
            'id': {'type': 'int', 'nullable': False, 'min': None, 'max': None},
            'studentName': {'type': 'str', 'nullable': True, 'min': None, 'max': None},
            'studentAge': {'type': 'int', 'nullable': False, 'min': 18.0, 'max': None},
            'grade': {'type': 'str', 'nullable': True, 'min': None, 'max': None},
            'department': {'type': 'str', 'nullable': True, 'min': None, 'max': None}
        }
        
        valid_rows = []
        quarantine_rows = []
        errors = []
        
        for idx, row in df.iterrows():
            row_errors = []
            
            for col, rule in schema.items():
                if col not in df.columns:
                    continue
                
                value = row[col]
                
                if pd.isna(value):
                    if not rule['nullable']:
                        row_errors.append(f'Column {col} is not nullable but value is null')
                    continue
                
                if rule['type'] == 'int':
                    try:
                        int_val = int(float(str(value)))
                        if rule['min'] is not None and int_val < rule['min']:
                            row_errors.append(f'Column {col} value {int_val} is below minimum {rule["min"]}')
                        if rule['max'] is not None and int_val > rule['max']:
                            row_errors.append(f'Column {col} value {int_val} is above maximum {rule["max"]}')
                    except (ValueError, TypeError):
                        row_errors.append(f'Column {col} value {value} cannot be converted to int')
                
                elif rule['type'] == 'str':
                    if not isinstance(value, str):
                        try:
                            str(value)
                        except:
                            row_errors.append(f'Column {col} value {value} cannot be converted to str')
            
            if row_errors:
                row_copy = row.copy()
                row_copy['quarantine_reason'] = '; '.join(row_errors)
                quarantine_rows.append(row_copy)
                errors.extend(row_errors)
            else:
                valid_rows.append(row)
        
        valid_df = pd.DataFrame(valid_rows) if valid_rows else df.iloc[0:0]
        valid_df.to_csv(silver_file, index=False)
        
        if quarantine_rows:
            quarantine_df = pd.DataFrame(quarantine_rows)
            quarantine_df.to_csv(quarantine_file, index=False)
        
        status = 'PASS' if len(valid_rows) > 0 else 'FAIL'
        
        output = {
            'status': status,
            'valid_rows': len(valid_rows),
            'quarantined_rows': len(quarantine_rows),
            'errors': errors
        }
        
        print(json.dumps(output))
        
    except Exception as e:
        output = {
            'status': 'FAIL',
            'valid_rows': 0,
            'quarantined_rows': 0,
            'errors': [str(e)]
        }
        print(json.dumps(output))

if __name__ == '__main__':
    main()
