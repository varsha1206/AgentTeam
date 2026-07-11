import pandas as pd
import json
from pathlib import Path

try:
    temp_file = Path("C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\temp\\transformed_broken_employee_data.csv")
    silver_file = Path("C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\output\\silver\\broken_employee_data.csv")
    quarantine_file = Path("C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\output\\quarantine\\quarantine_broken_employee_data.csv")
    
    df = pd.read_csv(temp_file)
    
    schema = {
        "id": {"type": "int", "nullable": False},
        "employeeName": {"type": "str", "nullable": False},
        "employeeAge": {"type": "int", "nullable": False, "min": 0.0, "max": 150.0},
        "salary": {"type": "float", "nullable": False, "min": 0.0, "max": 999999.0},
        "department": {"type": "str", "nullable": False},
        "unique_employee_id": {"type": "str", "nullable": False}
    }
    
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    for idx, row in df.iterrows():
        row_errors = []
        
        for col, rules in schema.items():
            if col not in df.columns:
                row_errors.append(f"Missing column: {col}")
                continue
            
            value = row[col]
            
            if pd.isna(value) or (isinstance(value, str) and value.strip() == ""):
                if not rules["nullable"]:
                    row_errors.append(f"Column {col} is non-nullable but has null/empty value")
                continue
            
            expected_type = rules["type"]
            
            try:
                if expected_type == "int":
                    int_val = int(float(str(value)))
                    if "min" in rules and int_val < rules["min"]:
                        row_errors.append(f"Column {col}: value {int_val} below minimum {rules['min']}")
                    if "max" in rules and int_val > rules["max"]:
                        row_errors.append(f"Column {col}: value {int_val} above maximum {rules['max']}")
                
                elif expected_type == "float":
                    float_val = float(str(value))
                    if "min" in rules and float_val < rules["min"]:
                        row_errors.append(f"Column {col}: value {float_val} below minimum {rules['min']}")
                    if "max" in rules and float_val > rules["max"]:
                        row_errors.append(f"Column {col}: value {float_val} above maximum {rules['max']}")
                
                elif expected_type == "str":
                    pass
            except (ValueError, TypeError) as e:
                row_errors.append(f"Column {col}: type conversion error")
        
        if row_errors:
            quarantined_row = row.copy()
            quarantined_row["quarantine_reason"] = "; ".join(row_errors)
            quarantined_rows.append(quarantined_row)
            errors.extend(row_errors)
        else:
            valid_rows.append(row)
    
    valid_df = pd.DataFrame(valid_rows) if valid_rows else df.head(0)
    valid_df.to_csv(silver_file, index=False)
    
    if quarantined_rows:
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_df.to_csv(quarantine_file, index=False)
    
    status = "PASS" if len(valid_rows) > 0 else "FAIL"
    output = {
        "status": status,
        "valid_rows": len(valid_rows),
        "quarantined_rows": len(quarantined_rows),
        "errors": errors
    }
    print(json.dumps(output))

except Exception as e:
    output = {
        "status": "FAIL",
        "valid_rows": 0,
        "quarantined_rows": 0,
        "errors": [str(e)]
    }
    print(json.dumps(output))