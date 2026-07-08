import pandas as pd
import json
from pathlib import Path

try:
    source_file = Path("C:/Users/Varsha/OneDrive/Documents/Github/AgentTeam/workspace/output/bronze/broken_employee_data.csv")
    output_file = Path("C:/Users/Varsha/OneDrive/Documents/Github/AgentTeam/workspace/temp/transformed_broken_employee_data.csv")
    quarantine_file = Path("C:/Users/Varsha/OneDrive/Documents/Github/AgentTeam/workspace/temp/quarantine_broken_employee_data.csv")
    
    df = pd.read_csv(source_file)
    
    quarantined = []
    valid = []
    
    for idx, row in df.iterrows():
        try:
            record = row.to_dict()
            
            if pd.isna(record.get('id')) or record.get('id') == '':
                quarantined.append(record)
                continue
            
            if pd.isna(record.get('name')) or record.get('name') == '':
                record['name'] = 'Unknown'
            
            if pd.isna(record.get('department')) or record.get('department') == '':
                record['department'] = 'Unassigned'
            
            age_val = record.get('age')
            if pd.isna(age_val) or age_val == '':
                record['age'] = 0
            else:
                try:
                    record['age'] = int(age_val)
                except (ValueError, TypeError):
                    record['age'] = 0
            
            salary_val = record.get('salary')
            if pd.isna(salary_val) or salary_val == '':
                record['salary'] = 0.0
            else:
                try:
                    sal_float = float(salary_val)
                    if sal_float < 0:
                        record['salary'] = 0.0
                    else:
                        record['salary'] = sal_float
                except (ValueError, TypeError):
                    record['salary'] = 0.0
            
            valid.append(record)
        except Exception as row_err:
            quarantined.append(row.to_dict())
    
    valid_df = pd.DataFrame(valid)
    if len(valid_df) > 0:
        valid_df.to_csv(output_file, index=False)
    
    quarantined_df = pd.DataFrame(quarantined)
    if len(quarantined_df) > 0:
        quarantined_df.to_csv(quarantine_file, index=False)
    
    print(json.dumps({"valid_rows": len(valid), "quarantined_rows": len(quarantined), "quarantine_path": str(quarantine_file)}))

except Exception as e:
    print(json.dumps({"error": str(e), "valid_rows": 0, "quarantined_rows": 0}))