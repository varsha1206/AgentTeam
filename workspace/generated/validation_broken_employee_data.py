import pandas as pd
import json
from pathlib import Path

try:
    # Read transformed data
    temp_file = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_broken_employee_data.csv')
    df = pd.read_csv(temp_file)
    
    # Define schema rules
    schema = {
        "id": {"type": "int", "nullable": False, "min": None, "max": None},
        "salary": {"type": "float", "nullable": False, "min": 0.0, "max": None},
        "employeeName": {"type": "str", "nullable": False, "min": None, "max": None},
        "employeeAge": {"type": "int", "nullable": False, "min": 0.0, "max": None},
        "department": {"type": "str", "nullable": True, "min": None, "max": None}
    }
    
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    for idx, row in df.iterrows():
        row_errors = []
        
        for col, rules in schema.items():
            if col not in df.columns:
                continue
            
            value = row[col]
            
            # Check nullable constraint
            if pd.isna(value):
                if not rules["nullable"]:
                    row_errors.append(f"Column '{col}' is non-nullable but has null value")
                continue
            
            # Check type
            if rules["type"] == "int":
                try:
                    int_val = int(value)
                except (ValueError, TypeError):
                    row_errors.append(f"Column '{col}' expected int but got {type(value).__name__}")
                    continue
                
                # Check min constraint
                if rules["min"] is not None and int_val < rules["min"]:
                    row_errors.append(f"Column '{col}' value {int_val} below minimum {rules['min']}")
            
            elif rules["type"] == "float":
                try:
                    float_val = float(value)
                except (ValueError, TypeError):
                    row_errors.append(f"Column '{col}' expected float but got {type(value).__name__}")
                    continue
                
                # Check min constraint
                if rules["min"] is not None and float_val < rules["min"]:
                    row_errors.append(f"Column '{col}' value {float_val} below minimum {rules['min']}")
            
            elif rules["type"] == "str":
                if not isinstance(value, str):
                    row_errors.append(f"Column '{col}' expected str but got {type(value).__name__}")
        
        if row_errors:
            quarantine_row = row.copy()
            quarantine_row['quarantine_reason'] = '; '.join(row_errors)
            quarantined_rows.append(quarantine_row)
            errors.extend(row_errors)
        else:
            valid_rows.append(row)
    
    # Write valid rows to silver
    silver_path = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\silver\broken_employee_data.csv')
    silver_path.parent.mkdir(parents=True, exist_ok=True)
    
    if valid_rows:
        valid_df = pd.DataFrame(valid_rows)
        valid_df.to_csv(silver_path, index=False)
    else:
        # Write header only
        valid_df = pd.DataFrame(columns=df.columns)
        valid_df.to_csv(silver_path, index=False)
    
    # Write quarantined rows
    quarantine_path = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine\quarantine_broken_employee_data.csv')
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    
    if quarantined_rows:
        quarantine_df = pd.DataFrame(quarantined_rows)
        quarantine_df.to_csv(quarantine_path, index=False)
    
    # Determine status
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