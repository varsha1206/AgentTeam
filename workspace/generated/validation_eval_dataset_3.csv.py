import pandas as pd
import json
from pathlib import Path

try:
    temp_file = Path(r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_eval_dataset_3.csv")
    silver_dir = Path(r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\silver")
    quarantine_dir = Path(r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine")
    
    silver_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(temp_file)
    
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
        row_valid = True
        quarantine_reason = ""
        
        for col, rules in schema.items():
            value = row[col]
            
            if pd.isna(value) or value == "":
                if not rules["nullable"]:
                    row_valid = False
                    quarantine_reason = f"Column '{col}' is non-nullable but has null value"
                    break
            else:
                if rules["type"] == "int":
                    try:
                        int_val = int(value)
                        if rules["min"] is not None and int_val < rules["min"]:
                            row_valid = False
                            quarantine_reason = f"Column '{col}' value {int_val} below minimum {rules['min']}"
                            break
                        if rules["max"] is not None and int_val > rules["max"]:
                            row_valid = False
                            quarantine_reason = f"Column '{col}' value {int_val} exceeds maximum {rules['max']}"
                            break
                    except (ValueError, TypeError):
                        row_valid = False
                        quarantine_reason = f"Column '{col}' cannot be converted to int: {value}"
                        break
                
                elif rules["type"] == "float":
                    try:
                        float_val = float(value)
                        if rules["min"] is not None and float_val < rules["min"]:
                            row_valid = False
                            quarantine_reason = f"Column '{col}' value {float_val} below minimum {rules['min']}"
                            break
                        if rules["max"] is not None and float_val > rules["max"]:
                            row_valid = False
                            quarantine_reason = f"Column '{col}' value {float_val} exceeds maximum {rules['max']}"
                            break
                    except (ValueError, TypeError):
                        row_valid = False
                        quarantine_reason = f"Column '{col}' cannot be converted to float: {value}"
                        break
                
                elif rules["type"] == "str":
                    if not isinstance(value, str):
                        row_valid = False
                        quarantine_reason = f"Column '{col}' is not a string: {value}"
                        break
        
        if row_valid:
            valid_rows.append(row)
        else:
            row_copy = row.copy()
            row_copy["quarantine_reason"] = quarantine_reason
            quarantined_rows.append(row_copy)
            errors.append(quarantine_reason)
    
    valid_df = pd.DataFrame(valid_rows)
    silver_output = silver_dir / "eval_dataset_3.csv"
    if len(valid_df) > 0:
        valid_df.to_csv(silver_output, index=False)
    else:
        valid_df.to_csv(silver_output, index=False)
    
    if len(quarantined_rows) > 0:
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_output = quarantine_dir / "quarantine_eval_dataset_3.csv"
        quarantine_df.to_csv(quarantine_output, index=False)
    
    status = "PASS" if len(valid_rows) > 0 else "FAIL"
    
    print(json.dumps({
        "status": status,
        "valid_rows": len(valid_rows),
        "quarantined_rows": len(quarantined_rows),
        "errors": errors
    }))

except Exception as e:
    print(json.dumps({
        "status": "FAIL",
        "valid_rows": 0,
        "quarantined_rows": 0,
        "errors": [str(e)]
    }))