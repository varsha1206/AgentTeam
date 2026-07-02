import pandas as pd
import json

try:
    # Read the transformed file
    transformed_file = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_employee_data.csv"
    df = pd.read_csv(transformed_file)
    
    errors = []
    
    # Define schema rules
    schema_rules = {
        "status": {"type": "str", "nullable": False},
        "department": {"type": "str", "nullable": True},
        "salary": {"type": "str", "nullable": False},
        "tenure": {"type": "float", "nullable": True, "min": 0.0, "max": 50.0},
        "recently_promoted": {"type": "float", "nullable": True},
        "n_projects": {"type": "int", "nullable": False, "min": 0.0, "max": 30.0},
        "avg_monthly_hrs": {"type": "int", "nullable": False, "min": 0.0, "max": 400.0},
        "satisfaction": {"type": "float", "nullable": True, "min": 0.0, "max": 1.0},
        "last_evaluation": {"type": "float", "nullable": True, "min": 0.0, "max": 1.0},
        "filed_complaint": {"type": "float", "nullable": True}
    }
    
    # Validate each column
    for col, rules in schema_rules.items():
        if col not in df.columns:
            errors.append("Column '{}' not found in dataset".format(col))
            continue
        
        # Check nullability
        if not rules["nullable"]:
            null_count = df[col].isna().sum()
            if null_count > 0:
                errors.append("Column '{}' has {} null values but is non-nullable".format(col, null_count))
        
        # Check data type
        expected_type = rules["type"]
        if expected_type == "int":
            if not pd.api.types.is_integer_dtype(df[col]):
                non_int_count = df[col].apply(lambda x: not isinstance(x, (int, float)) or (isinstance(x, float) and x != int(x))).sum()
                if non_int_count > 0:
                    errors.append("Column '{}' has {} non-integer values".format(col, non_int_count))
        elif expected_type == "float":
            if not pd.api.types.is_numeric_dtype(df[col]):
                errors.append("Column '{}' is not numeric".format(col))
        elif expected_type == "str":
            if not pd.api.types.is_string_dtype(df[col]) and not pd.api.types.is_object_dtype(df[col]):
                errors.append("Column '{}' is not string type".format(col))
        
        # Check min/max constraints
        if "min" in rules and rules["min"] is not None:
            min_val = rules["min"]
            invalid_count = (df[col] < min_val).sum()
            if invalid_count > 0:
                errors.append("Column '{}' has {} values below minimum {}".format(col, invalid_count, min_val))
        
        if "max" in rules and rules["max"] is not None:
            max_val = rules["max"]
            invalid_count = (df[col] > max_val).sum()
            if invalid_count > 0:
                errors.append("Column '{}' has {} values above maximum {}".format(col, invalid_count, max_val))
    
    # Determine status
    status = "PASS" if len(errors) == 0 else "FAIL"
    
    # Print result JSON
    result = {
        "status": status,
        "errors": errors
    }
    print(json.dumps(result))

except Exception as e:
    print(json.dumps({"status": "FAIL", "errors": [str(e)]}))
