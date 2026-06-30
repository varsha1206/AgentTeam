import pandas as pd
import json
from pathlib import Path

try:
    file_path = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze\sample.csv'
    df = pd.read_csv(file_path)
    
    errors = []
    
    # Expected schema
    expected_columns = ['id', 'name', 'age', 'salary']
    expected_types = {
        'id': ['int64', 'float64'],
        'name': ['object', 'str'],
        'age': ['object', 'str', 'int64', 'float64'],
        'salary': ['float64', 'int64']
    }
    
    # Check for unexpected or missing columns
    actual_columns = list(df.columns)
    if actual_columns != expected_columns:
        errors.append(f"Column mismatch. Expected {expected_columns}, got {actual_columns}")
    
    # Check for missing values in non-nullable columns (id is primary key, required)
    if df['id'].isna().any():
        null_count = df['id'].isna().sum()
        errors.append(f"Column 'id' has {null_count} null values (non-nullable)")
    
    # Check for missing values in name (should not be null)
    if df['name'].isna().any():
        null_count = df['name'].isna().sum()
        errors.append(f"Column 'name' has {null_count} null values")
    
    # Check data types
    for col in expected_columns:
        if col in df.columns:
            dtype_str = str(df[col].dtype)
            if expected_types[col]:
                if dtype_str not in expected_types[col]:
                    errors.append(f"Column '{col}' has dtype '{dtype_str}', expected one of {expected_types[col]}")
    
    # Check age column - should be numeric, but is string
    if 'age' in df.columns:
        age_col = df['age']
        non_null_ages = age_col.dropna()
        for val in non_null_ages:
            if not str(val).isdigit() and not (isinstance(val, (int, float))):
                errors.append(f"Column 'age' contains non-numeric value: '{val}'")
    
    # Check for duplicate rows
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        errors.append(f"Found {duplicates} duplicate rows")
    
    # Check for duplicate IDs
    if 'id' in df.columns:
        id_duplicates = df['id'].duplicated().sum()
        if id_duplicates > 0:
            errors.append(f"Found {id_duplicates} duplicate id values")
    
    row_count = len(df)
    column_count = len(df.columns)
    
    status = "PASS" if len(errors) == 0 else "FAIL"
    
    result = {
        "status": status,
        "errors": errors,
        "row_count": row_count,
        "column_count": column_count
    }
    
    print(json.dumps(result))
    
except Exception as e:
    result = {
        "status": "FAIL",
        "errors": [str(e)]
    }
    print(json.dumps(result))
