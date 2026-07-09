import pandas as pd
import json
from pathlib import Path

try:
    source_path = "C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\input\\broken_employee_data.csv"
    output_dir = "C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\output\\bronze"
    output_filename = "broken_employee_data.csv"
    
    df = pd.read_csv(source_path)
    
    rows = len(df)
    columns = df.columns.tolist()
    nulls = df.isnull().sum().to_dict()
    
    metadata = {
        "rows": rows,
        "columns": columns,
        "nulls": nulls
    }
    
    print(json.dumps(metadata))
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_path = Path(output_dir) / output_filename
    df.to_csv(output_path, index=False)
    
except Exception as e:
    error_output = {
        "error": str(e),
        "type": type(e).__name__
    }
    print(json.dumps(error_output))
