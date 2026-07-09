import pandas as pd
import json
from pathlib import Path

def main():
    try:
        input_path = Path("C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\temp\\transformed_broken_employee_data.csv")
        silver_path = Path("C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\output\\silver\\broken_employee_data.csv")
        quarantine_path = Path("C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\output\\quarantine\\quarantine_broken_employee_data.csv")
        
        df = pd.read_csv(input_path)
        
        silver_path.parent.mkdir(parents=True, exist_ok=True)
        quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        
        valid_rows = []
        quarantined_rows = []
        errors = []
        
        for idx, row in df.iterrows():
            quarantine_reasons = []
            
            # Check id: must be non-null and numeric
            if pd.isna(row['id']):
                quarantine_reasons.append("id is null")
            elif not isinstance(row['id'], (int, float)) or pd.isna(row['id']):
                quarantine_reasons.append("id is not numeric")
            
            # Check employee_name: nullable allowed
            if pd.isna(row['employee_name']):
                quarantine_reasons.append("employee_name is null")
            
            # Check employee_age: must be positive numeric, allow null for now
            if not pd.isna(row['employee_age']):
                if not isinstance(row['employee_age'], (int, float)):
                    quarantine_reasons.append("employee_age is not numeric")
                elif row['employee_age'] <= 0:
                    quarantine_reasons.append("employee_age must be positive")
            else:
                quarantine_reasons.append("employee_age is null")
            
            # Check salary: must be positive numeric, allow null for now
            if not pd.isna(row['salary']):
                if not isinstance(row['salary'], (int, float)):
                    quarantine_reasons.append("salary is not numeric")
                elif row['salary'] <= 0:
                    quarantine_reasons.append("salary must be positive")
            else:
                quarantine_reasons.append("salary is null")
            
            # Check department: must be non-null string
            if pd.isna(row['department']):
                quarantine_reasons.append("department is null")
            
            if quarantine_reasons:
                row_with_reason = row.copy()
                row_with_reason['quarantine_reason'] = "; ".join(quarantine_reasons)
                quarantined_rows.append(row_with_reason)
            else:
                valid_rows.append(row)
        
        if valid_rows:
            valid_df = pd.DataFrame(valid_rows)
            valid_df.to_csv(silver_path, index=False)
        
        if quarantined_rows:
            quarantine_df = pd.DataFrame(quarantined_rows)
            quarantine_df.to_csv(quarantine_path, index=False)
        
        status = "PASS" if valid_rows else "FAIL"
        result = {
            "status": status,
            "valid_rows": len(valid_rows),
            "quarantined_rows": len(quarantined_rows),
            "errors": errors
        }
        print(json.dumps(result))
        
    except Exception as e:
        error_result = {
            "status": "FAIL",
            "valid_rows": 0,
            "quarantined_rows": 0,
            "errors": [str(e)]
        }
        print(json.dumps(error_result))

if __name__ == "__main__":
    main()
