import pandas as pd
import json
from pathlib import Path

try:
    temp_file = Path("C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\temp\\transformed_broken_employee_data.csv")
    silver_dir = Path("C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\output\\silver")
    quarantine_dir = Path("C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\output\\quarantine")
    
    silver_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(temp_file)
    
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    for idx, row in df.iterrows():
        row_errors = []
        
        if pd.isna(row['id']) or pd.isna(row['employeeName']) or pd.isna(row['employeeAge']) or pd.isna(row['salary']) or pd.isna(row['department']):
            row_errors.append("contains_null_in_non_nullable_column")
        
        if not row_errors:
            try:
                if not isinstance(row['id'], (int, float)) or pd.isna(row['id']):
                    row_errors.append("id_type_mismatch")
                elif row['id'] < 1:
                    row_errors.append("id_min_value_violation")
            except:
                row_errors.append("id_type_mismatch")
        
        if not row_errors:
            try:
                if not isinstance(row['employeeName'], str) or len(row['employeeName'].strip()) == 0:
                    row_errors.append("employeeName_invalid")
            except:
                row_errors.append("employeeName_type_mismatch")
        
        if not row_errors:
            try:
                if not isinstance(row['employeeAge'], (int, float)) or pd.isna(row['employeeAge']):
                    row_errors.append("employeeAge_type_mismatch")
                elif row['employeeAge'] < 18 or row['employeeAge'] > 75:
                    row_errors.append("employeeAge_range_violation")
            except:
                row_errors.append("employeeAge_type_mismatch")
        
        if not row_errors:
            try:
                if not isinstance(row['salary'], (int, float)) or pd.isna(row['salary']):
                    row_errors.append("salary_type_mismatch")
                elif row['salary'] < 0:
                    row_errors.append("salary_negative_violation")
            except:
                row_errors.append("salary_type_mismatch")
        
        if not row_errors:
            allowed_depts = ['Eng', 'HR', 'Sales', 'IT']
            if row['department'] not in allowed_depts:
                row_errors.append("department_invalid_value")
        
        if row_errors:
            quarantine_row = row.copy()
            quarantine_row['quarantine_reason'] = '; '.join(row_errors)
            quarantined_rows.append(quarantine_row)
            errors.extend([f"Row {idx}: {err}" for err in row_errors])
        else:
            valid_rows.append(row)
    
    valid_df = pd.DataFrame(valid_rows) if valid_rows else df.iloc[0:0]
    silver_output = silver_dir / "validated_broken_employee_data.csv"
    valid_df.to_csv(silver_output, index=False)
    
    if quarantined_rows:
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_output = quarantine_dir / "quarantine_broken_employee_data.csv"
        quarantine_df.to_csv(quarantine_output, index=False)
    
    status = "PASS" if len(valid_rows) > 0 else "FAIL"
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
