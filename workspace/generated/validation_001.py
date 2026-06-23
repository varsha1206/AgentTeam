import pandas as pd
import json
from pathlib import Path

try:
    csv_path = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\sample.csv')
    df = pd.read_csv(csv_path)
    
    errors = []
    
    expected_columns = ['id', 'name', 'age', 'salary']
    actual_columns = list(df.columns)
    
    if actual_columns != expected_columns:
        errors.append(f'Column mismatch. Expected: {expected_columns}, Got: {actual_columns}')
    
    if len(df) == 0:
        errors.append('Dataset is empty')
    
    if 'id' in df.columns:
        if df['id'].isnull().any():
            null_ids = df[df['id'].isnull()].index.tolist()
            errors.append(f'Column "id" contains null values at rows: {null_ids}')
        try:
            pd.to_numeric(df['id'])
        except:
            errors.append('Column "id" contains non-numeric values')
    
    if 'name' in df.columns:
        if df['name'].isnull().any():
            null_names = df[df['name'].isnull()].index.tolist()
            errors.append(f'Column "name" contains null values at rows: {null_names}')
    
    if 'age' in df.columns:
        if df['age'].isnull().any():
            null_ages = df[df['age'].isnull()].index.tolist()
            errors.append(f'Column "age" contains null values at rows: {null_ages}')
        try:
            pd.to_numeric(df['age'])
        except:
            non_numeric_ages = df[pd.to_numeric(df['age'], errors='coerce').isnull() & df['age'].notna()].index.tolist()
            errors.append(f'Column "age" contains non-numeric values at rows: {non_numeric_ages}')
    
    if 'salary' in df.columns:
        if df['salary'].isnull().any():
            null_salaries = df[df['salary'].isnull()].index.tolist()
            errors.append(f'Column "salary" contains null values at rows: {null_salaries}')
        try:
            pd.to_numeric(df['salary'])
        except:
            errors.append('Column "salary" contains non-numeric values')
    
    duplicate_rows = df.duplicated().sum()
    if duplicate_rows > 0:
        errors.append(f'Dataset contains {duplicate_rows} duplicate row(s)')
    
    row_count = len(df)
    column_count = len(df.columns)
    
    status = 'PASS' if len(errors) == 0 else 'FAIL'
    
    result = {
        'status': status,
        'errors': errors,
        'row_count': row_count,
        'column_count': column_count
    }
    
    print(json.dumps(result))
    
except Exception as e:
    error_result = {
        'status': 'FAIL',
        'errors': [f'Validation script error: {str(e)}'],
        'row_count': 0,
        'column_count': 0
    }
    print(json.dumps(error_result))
