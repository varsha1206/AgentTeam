import pandas as pd
import json
from pathlib import Path

try:
    # Read transformed file
    transformed_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_broken_employee_data.csv'
    df = pd.read_csv(transformed_file)
    
    # Define silver and quarantine output paths
    silver_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\silver\broken_employee_data.csv'
    quarantine_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine\quarantine_broken_employee_data.csv'
    
    # Ensure output directories exist
    Path(silver_file).parent.mkdir(parents=True, exist_ok=True)
    Path(quarantine_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Define validation rules
    schema = {
        "id": {"type": "int", "nullable": False, "min": None, "max": None},
        "salary": {"type": "float", "nullable": False, "min": 0.0, "max": None},
        "employeeName": {"type": "str", "nullable": True, "min": None, "max": None},
        "employeeAge": {"type": "int", "nullable": False, "min": 0.0, "max": None},
        "department": {"type": "str", "nullable": True, "min": None, "max": None}
    }
    
    valid_rows = []
    quarantined_rows = []
    errors = []
    
    for idx, row in df.iterrows():
        row_errors = []
        
        # Validate each column
        for col, rules in schema.items():
            if col not in df.columns:
                row_errors.append(f"Column {col} missing")
                continue
            
            value = row[col]
            is_null = pd.isna(value)
            
            # Check nullable constraint
            if is_null and not rules["nullable"]:
                row_errors.append(f"Column {col} is null but not nullable")
                continue
            
            if is_null:
                continue
            
            # Check type constraint
            type_name = rules["type"]
            if type_name == "int":
                try:
                    int_val = int(float(str(value)))
                    if rules["min"] is not None and int_val < rules["min"]:
                        row_errors.append(f"Column {col} value {int_val} below minimum {rules['min']}")
                    if rules["max"] is not None and int_val > rules["max"]:
                        row_errors.append(f"Column {col} value {int_val} above maximum {rules['max']}")
                except (ValueError, TypeError):
                    row_errors.append(f"Column {col} cannot be coerced to int: {value}")
            
            elif type_name == "float":
                try:
                    float_val = float(str(value))
                    if rules["min"] is not None and float_val < rules["min"]:
                        row_errors.append(f"Column {col} value {float_val} below minimum {rules['min']}")
                    if rules["max"] is not None and float_val > rules["max"]:
                        row_errors.append(f"Column {col} value {float_val} above maximum {rules['max']}")
                except (ValueError, TypeError):
                    row_errors.append(f"Column {col} cannot be coerced to float: {value}")
            
            elif type_name == "str":
                if not isinstance(value, str):
                    row_errors.append(f"Column {col} is not a string: {value}")
        
        # Add row to valid or quarantined
        if row_errors:
            row_copy = row.copy()
            row_copy['quarantine_reason'] = '; '.join(row_errors)
            quarantined_rows.append(row_copy)
            errors.extend(row_errors)
        else:
            valid_rows.append(row)
    
    # Write valid rows to silver
    if valid_rows:
        valid_df = pd.DataFrame(valid_rows)
        valid_df.to_csv(silver_file, index=False)
    else:
        # Write header only
        df[list(schema.keys())].head(0).to_csv(silver_file, index=False)
    
    # Write quarantined rows
    if quarantined_rows:
        quarantined_df = pd.DataFrame(quarantined_rows)
        quarantined_df.to_csv(quarantine_file, index=False)
    
    # Determine status
    status = "PASS" if len(valid_rows) > 0 else "FAIL"
    
    # Print result
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
