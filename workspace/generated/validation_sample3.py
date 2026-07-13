import pandas as pd
import json
from pathlib import Path

try:
    file_path = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze\sample3.csv'
    df = pd.read_csv(file_path)
    
    errors = []
    
    # Check for expected columns
    expected_columns = {'shop_id', 'shop_name', 'shop_code', 'shop_revenue'}
    actual_columns = set(df.columns)
    missing_columns = expected_columns - actual_columns
    extra_columns = actual_columns - expected_columns
    
    if missing_columns:
        errors.append(f"Missing columns: {missing_columns}")
    if extra_columns:
        errors.append(f"Unexpected columns: {extra_columns}")
    
    # Check for null values in non-nullable columns
    non_nullable = ['shop_id', 'shop_name', 'shop_code', 'shop_revenue']
    for col in non_nullable:
        if col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                errors.append(f"Column '{col}' has {null_count} null values")
    
    # Check data types
    type_checks = {
        'shop_id': 'int64',
        'shop_name': 'object',
        'shop_code': 'int64',
        'shop_revenue': 'int64'
    }
    
    for col, expected_type in type_checks.items():
        if col in df.columns:
            actual_type = str(df[col].dtype)
            if actual_type != expected_type:
                errors.append(f"Column '{col}' has type {actual_type}, expected {expected_type}")
    
    # Check for duplicate rows
    duplicate_count = df.duplicated().sum()
    if duplicate_count > 0:
        errors.append(f"Found {duplicate_count} duplicate rows")
    
    # Check for negative or zero revenue
    if 'shop_revenue' in df.columns:
        invalid_revenue = (df['shop_revenue'] <= 0).sum()
        if invalid_revenue > 0:
            errors.append(f"Found {invalid_revenue} rows with shop_revenue <= 0")
    
    # Determine overall status
    status = "FAIL" if errors else "PASS"
    
    result = {
        "status": status,
        "errors": errors
    }
    
    print(json.dumps(result))

except Exception as e:
    result = {
        "status": "FAIL",
        "errors": [str(e)]
    }
    print(json.dumps(result))
