import pandas as pd
import json
import os

try:
    temp_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_employee_data.csv'
    
    df = pd.read_csv(temp_file)
    errors = []
    
    # Schema validation rules
    schema_rules = {
        'status': {'type': 'str', 'nullable': False},
        'department': {'type': 'str', 'nullable': False},
        'salary': {'type': 'float', 'nullable': False, 'min': 0.0},
        'tenure': {'type': 'float', 'nullable': False, 'min': 0.0, 'max': 50.0},
        'recently_promoted': {'type': 'bool', 'nullable': False},
        'n_projects': {'type': 'int', 'nullable': False, 'min': 0.0, 'max': 30.0},
        'avg_monthly_hrs': {'type': 'float', 'nullable': False, 'min': 0.0, 'max': 400.0},
        'satisfaction': {'type': 'float', 'nullable': False, 'min': 0.0, 'max': 1.0},
        'last_evaluation': {'type': 'float', 'nullable': False, 'min': 0.0, 'max': 1.0},
        'filed_complaint': {'type': 'bool', 'nullable': False}
    }
    
    # Check if dataframe is empty
    if len(df) == 0:
        errors.append('No valid rows in transformed data')
    else:
        # Check each column
        for col, rules in schema_rules.items():
            if col not in df.columns:
                errors.append(f'Missing column: {col}')
                continue
            
            # Check nullability
            null_count = df[col].isnull().sum()
            if not rules['nullable'] and null_count > 0:
                errors.append(f'Column {col} has {null_count} null values but nullability is False')
            
            # Check type
            if rules['type'] == 'float':
                non_numeric = df[col].notna() & ~pd.to_numeric(df[col], errors='coerce').notna()
                if non_numeric.any():
                    errors.append(f'Column {col} has non-numeric values')
            elif rules['type'] == 'int':
                non_int = df[col].notna() & (pd.to_numeric(df[col], errors='coerce') != pd.to_numeric(df[col], errors='coerce').astype('Int64'))
                if non_int.any():
                    errors.append(f'Column {col} has non-integer values')
            elif rules['type'] == 'bool':
                valid_bools = df[col].isin([0, 1, True, False, 'True', 'False', 'true', 'false'])
                if df[col].notna().sum() > 0 and not valid_bools.all():
                    errors.append(f'Column {col} has non-boolean values')
            
            # Check range constraints
            if 'min' in rules and rules['min'] is not None:
                below_min = (df[col] < rules['min']).sum()
                if below_min > 0:
                    errors.append(f'Column {col} has {below_min} values below minimum {rules["min"]}')
            
            if 'max' in rules and rules['max'] is not None:
                above_max = (df[col] > rules['max']).sum()
                if above_max > 0:
                    errors.append(f'Column {col} has {above_max} values above maximum {rules["max"]}')
    
    status = 'FAIL' if errors else 'PASS'
    result = {
        'status': status,
        'errors': errors
    }
    print(json.dumps(result))

except Exception as e:
    error_result = {
        'status': 'FAILED',
        'errors': [str(e)]
    }
    print(json.dumps(error_result))