import pandas as pd
import pathlib
import json
import shutil

try:
    input_path = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\broken_employee_data.csv'
    bronze_dir = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze'
    output_filename = 'broken_employee_data.csv'
    
    pathlib.Path(bronze_dir).mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(input_path)
    
    output_path = pathlib.Path(bronze_dir) / output_filename
    shutil.copy(input_path, output_path)
    
    rows = len(df)
    columns = list(df.columns)
    nulls = {col: int(df[col].isna().sum()) for col in df.columns}
    
    result = {
        'files': [
            {
                'filename': output_filename,
                'rows': rows,
                'columns': columns,
                'nulls': nulls
            }
        ]
    }
    
    print(json.dumps(result))
    
except Exception as e:
    error_result = {'error': str(e)}
    print(json.dumps(error_result))
