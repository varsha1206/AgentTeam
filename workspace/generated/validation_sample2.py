import pandas as pd
import json
from pathlib import Path

try:
    file_path = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze\sample2.csv'
    
    df = pd.read_csv(file_path)
    
    errors = []
    
    # Check expected columns
    expected_columns = ['student_id', 'student_name', 'age', 'city']
    actual_columns = list(df.columns)
    if actual_columns != expected_columns:
        errors.append(f"Column mismatch. Expected: {expected_columns}, Got: {actual_columns}")
    
    # Check for missing values in non-nullable columns
    if df['student_id'].isnull().any():
        errors.append("Column 'student_id' contains null values")
    
    if df['student_name'].isnull().any():
        null_count = df['student_name'].isnull().sum()
        errors.append(f"Column 'student_name' contains {null_count} null values")
    
    if df['age'].isnull().any():
        null_count = df['age'].isnull().sum()
        errors.append(f"Column 'age' contains {null_count} null values")
    
    if df['city'].isnull().any():
        null_count = df['city'].isnull().sum()
        errors.append(f"Column 'city' contains {null_count} null values")
    
    # Check data types
    if not pd.api.types.is_integer_dtype(df['student_id']):
        errors.append(f"Column 'student_id' should be integer, got {df['student_id'].dtype}")
    
    # Check for age to be numeric (if not null)
    age_non_null = df['age'].dropna()
    if len(age_non_null) > 0:
        try:
            pd.to_numeric(age_non_null)
        except ValueError:
            invalid_ages = [val for val in age_non_null if not str(val).replace('.','',1).isdigit()]
            errors.append(f"Column 'age' contains non-numeric values: {invalid_ages[:5]}")
    
    # Check for duplicate rows
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        errors.append(f"Found {duplicates} duplicate rows")
    
    # Check for rows with all nulls
    all_null_rows = df.isnull().all(axis=1).sum()
    if all_null_rows > 0:
        errors.append(f"Found {all_null_rows} rows with all null values")
    
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