import pandas as pd
import json
from pathlib import Path

try:
    output_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output')
    
    errors = []
    total_rows = 0
    total_cols = 0
    
    csv_files = sorted(list(output_dir.glob('*.csv')))
    
    if not csv_files:
        print(json.dumps({"status": "FAIL", "errors": ["No CSV files found in output directory"]}))
        exit(1)
    
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        total_rows += len(df)
        if total_cols == 0:
            total_cols = len(df.columns)
        
        filename = csv_file.name
        
        if len(df) == 0:
            errors.append(f"{filename}: Dataset is empty (0 rows)")
            continue
        
        if len(df.columns) == 0:
            errors.append(f"{filename}: Dataset has no columns")
            continue
        
        expected_cols_sample = {
            'sample.csv': ['id', 'name', 'age', 'salary'],
            'sample2.csv': ['student_id', 'student_name', 'age', 'city']
        }
        
        expected_cols = expected_cols_sample.get(filename, df.columns.tolist())
        if list(df.columns) != expected_cols:
            errors.append(f"{filename}: Unexpected columns. Expected {expected_cols}, got {list(df.columns)}")
        
        if filename == 'sample.csv':
            if df['id'].isnull().sum() > 0:
                errors.append(f"{filename}: Column 'id' (primary key) has null values")
            
            if df['name'].isnull().sum() > 0:
                errors.append(f"{filename}: Column 'name' has null values: {df['name'].isnull().sum()} rows")
            
            if df['age'].isnull().sum() > 0:
                errors.append(f"{filename}: Column 'age' has null values: {df['age'].isnull().sum()} rows")
            
            if df['salary'].isnull().sum() > 0:
                errors.append(f"{filename}: Column 'salary' has null values: {df['salary'].isnull().sum()} rows")
            
            non_numeric_age = df[~df['age'].isnull()][df[~df['age'].isnull()]['age'].astype(str).str.contains(r'^[0-9]+$', na=False) == False]
            if len(non_numeric_age) > 0:
                errors.append(f"{filename}: Column 'age' contains non-numeric values: {non_numeric_age['age'].tolist()}")
            
            if not pd.api.types.is_numeric_dtype(df['salary']):
                non_numeric_sal = df[~df['salary'].isnull()][~pd.to_numeric(df[~df['salary'].isnull()]['salary'], errors='coerce').notna()]
                if len(non_numeric_sal) > 0:
                    errors.append(f"{filename}: Column 'salary' contains non-numeric values")
        
        elif filename == 'sample2.csv':
            if df['student_id'].isnull().sum() > 0:
                errors.append(f"{filename}: Column 'student_id' (primary key) has null values")
            
            if df['student_name'].isnull().sum() > 0:
                errors.append(f"{filename}: Column 'student_name' has null values: {df['student_name'].isnull().sum()} rows")
            
            if df['age'].isnull().sum() > 0:
                errors.append(f"{filename}: Column 'age' has null values: {df['age'].isnull().sum()} rows")
            
            if df['city'].isnull().sum() > 0:
                errors.append(f"{filename}: Column 'city' has null values: {df['city'].isnull().sum()} rows")
            
            non_numeric_age = df[~df['age'].isnull()][df[~df['age'].isnull()]['age'].astype(str).str.contains(r'^[0-9]+$', na=False) == False]
            if len(non_numeric_age) > 0:
                errors.append(f"{filename}: Column 'age' contains non-numeric values: {non_numeric_age['age'].tolist()}")
        
        duplicates = df.duplicated().sum()
        if duplicates > 0:
            errors.append(f"{filename}: Dataset has {duplicates} duplicate rows")
    
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}))
    else:
        print(json.dumps({"status": "PASS", "errors": []}))

except Exception as e:
    print(json.dumps({"status": "FAIL", "errors": [f"Validation script error: {str(e)}"]}))
