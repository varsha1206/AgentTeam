import pandas as pd
from pathlib import Path
import json
import shutil

try:
    source_path = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\broken_employee_data.csv"
    output_dir = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze"
    output_filename = "broken_employee_data.csv"
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(source_path)
    
    output_path = Path(output_dir) / output_filename
    shutil.copy(source_path, output_path)
    
    rows = len(df)
    columns = df.columns.tolist()
    nulls = df.isnull().sum().to_dict()
    
    result = {
        "rows": rows,
        "columns": columns,
        "nulls": nulls
    }
    
    print(json.dumps(result))
    
except Exception as e:
    error_result = {
        "error": str(e)
    }
    print(json.dumps(error_result))
