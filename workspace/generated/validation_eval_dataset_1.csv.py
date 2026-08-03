import pandas as pd
import json
from pathlib import Path

try:
    transformed_file = "C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\temp\\transformed_eval_dataset_1.csv"
    silver_file = "C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\output\\silver\\eval_dataset_1.csv"
    quarantine_file = "C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\output\\quarantine\\quarantine_eval_dataset_1.csv"
    
    df = pd.read_csv(transformed_file)
    
    schema = {
        "id": {"type": "int", "nullable": False, "min": None, "max": None},
        "name": {"type": "str", "nullable": False, "min": None, "max": None},
        "age": {"type": "int", "nullable": False, "min": 18.0, "max": 70.0},
        "salary": {"type": "float", "nullable": False, "min": 0.0, "max": None},
        "department": {"type": "str", "nullable": False, "min": None, "max": None}
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
            
            if rules["nullable"] is False and pd.isna(value):
                row_errors.append(f"Non-nullable column '{col}' has null value")
                continue
            
            if pd.isna(value):
                continue
            
            if rules["type"] == "int":
                try:
                    int_val = int(value)
                except (ValueError, TypeError):
                    row_errors.append(f"Column '{col}' cannot be coerced to int: {value}")
                    continue
                
                if rules["min"] is not None and int_val < rules["min"]:
                    row_errors.append(f"Column '{col}' value {int_val} is below minimum {rules['min']}")
                
                if rules["max"] is not None and int_val > rules["max"]:
                    row_errors.append(f"Column '{col}' value {int_val} exceeds maximum {rules['max']}")
            
            elif rules["type"] == "float":
                try:
                    float_val = float(value)
                except (ValueError, TypeError):
                    row_errors.append(f"Column '{col}' cannot be coerced to float: {value}")
                    continue
                
                if rules["min"] is not None and float_val < rules["min"]:
                    row_errors.append(f"Column '{col}' value {float_val} is below minimum {rules['min']}")
                
                if rules["max"] is not None and float_val > rules["max"]:
                    row_errors.append(f"Column '{col}' value {float_val} exceeds maximum {rules['max']}")
            
            elif rules["type"] == "str":
                if not isinstance(value, str):
                    row_errors.append(f"Column '{col}' is not a string: {value}")
        
        if row_errors:
            quarantined_row = row.to_dict()
            quarantined_row["quarantine_reason"] = "; ".join(row_errors)
            quarantined_rows.append(quarantined_row)
            errors.extend(row_errors)
        else:
            valid_rows.append(row)
    
    valid_df = pd.DataFrame(valid_rows) if valid_rows else df.iloc[0:0]
    valid_df.to_csv(silver_file, index=False)
    
    if quarantined_rows:
        quarantined_df = pd.DataFrame(quarantined_rows)
        quarantined_df.to_csv(quarantine_file, index=False)
    
    status = "PASS" if len(valid_rows) > 0 else "FAIL"
    
    print(json.dumps({
        "status": status,
        "valid_rows": len(valid_rows),
        "quarantined_rows": len(quarantined_rows),
        "errors": errors[:10]
    }))

except Exception as e:
    print(json.dumps({
        "status": "FAIL",
        "valid_rows": 0,
        "quarantined_rows": 0,
        "errors": [str(e)]
    }))