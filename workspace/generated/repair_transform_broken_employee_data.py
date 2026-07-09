import pandas as pd
import json
from pathlib import Path

try:
    source_path = Path("C:/Users/Varsha/OneDrive/Documents/Github/AgentTeam/workspace/output/bronze/broken_employee_data.csv")
    output_dir = Path("C:/Users/Varsha/OneDrive/Documents/Github/AgentTeam/workspace/temp")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "transformed_broken_employee_data.csv"
    quarantine_file = output_dir / "quarantined_broken_employee_data.csv"
    
    df = pd.read_csv(source_path)
    
    valid_rows = []
    quarantined_rows = []
    
    for idx, row in df.iterrows():
        valid = True
        row_data = row.to_dict()
        
        try:
            if 'employeeAge' in row_data:
                if pd.notna(row_data['employeeAge']):
                    row_data['employeeAge'] = pd.to_numeric(row_data['employeeAge'], errors='coerce')
                    if pd.isna(row_data['employeeAge']):
                        valid = False
            
            if 'salary' in row_data:
                if pd.notna(row_data['salary']):
                    row_data['salary'] = pd.to_numeric(row_data['salary'], errors='coerce')
                    if pd.isna(row_data['salary']):
                        valid = False
        except:
            valid = False
        
        if valid:
            valid_rows.append(row_data)
        else:
            quarantined_rows.append(row_data)
    
    valid_df = pd.DataFrame(valid_rows)
    
    if len(valid_df) > 0:
        valid_df.columns = [col.lower().replace(' ', '_') for col in valid_df.columns]
        valid_df.to_csv(output_file, index=False)
    else:
        valid_df.to_csv(output_file, index=False)
    
    if len(quarantined_rows) > 0:
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_df.to_csv(quarantine_file, index=False)
    
    result = {
        "valid_rows": len(valid_rows),
        "quarantined_rows": len(quarantined_rows),
        "quarantine_path": str(quarantine_file) if len(quarantined_rows) > 0 else ""
    }
    print(json.dumps(result))

except Exception as e:
    error_result = {
        "error": str(e),
        "valid_rows": 0,
        "quarantined_rows": 0,
        "quarantine_path": ""
    }
    print(json.dumps(error_result))
