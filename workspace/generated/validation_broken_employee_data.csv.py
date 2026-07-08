import pandas as pd
import json
from pathlib import Path

try:
    temp_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_broken_employee_data.csv'
    
    df = pd.read_csv(temp_file)
    errors = []
    
    if len(df) == 0:
        status = 'PASS'
    else:
        status = 'PASS'
        
        for col in ['id', 'name', 'age', 'salary', 'department']:
            if col not in df.columns:
                errors.append('Missing required column: ' + col)
                status = 'FAIL'
        
        if status == 'PASS':
            if df['id'].isnull().any():
                errors.append('Column id contains NaN values')
                status = 'FAIL'
            if df['name'].isnull().any():
                errors.append('Column name contains NaN values')
                status = 'FAIL'
            if df['age'].isnull().any():
                errors.append('Column age contains NaN values')
                status = 'FAIL'
            if df['salary'].isnull().any():
                errors.append('Column salary contains NaN values')
                status = 'FAIL'
            if df['department'].isnull().any():
                errors.append('Column department contains NaN values')
                status = 'FAIL'
            
            if status == 'PASS' and len(df) > 0:
                for idx, row in df.iterrows():
                    try:
                        int(row['id'])
                    except:
                        errors.append('Row ' + str(idx) + ': id is not integer')
                        status = 'FAIL'
                    
                    try:
                        age_int = int(float(str(row['age']).strip()))
                        if age_int < 0 or age_int > 120:
                            errors.append('Row ' + str(idx) + ': age out of range')
                            status = 'FAIL'
                    except:
                        errors.append('Row ' + str(idx) + ': age is not numeric')
                        status = 'FAIL'
                    
                    try:
                        salary_float = float(str(row['salary']).strip())
                        if salary_float < 0:
                            errors.append('Row ' + str(idx) + ': salary is negative')
                            status = 'FAIL'
                    except:
                        errors.append('Row ' + str(idx) + ': salary is not numeric')
                        status = 'FAIL'
    
    result = {'status': status, 'errors': errors}
    print(json.dumps(result))
    
except Exception as e:
    print(json.dumps({'status': 'ERROR', 'errors': [str(e)]}))
