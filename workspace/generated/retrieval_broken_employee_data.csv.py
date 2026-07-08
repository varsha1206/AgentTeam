import pandas as pd
import json
from pathlib import Path

try:
    source_path = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\broken_employee_data.csv'
    bronze_dir = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze'
    output_filename = 'broken_employee_data.csv'
    
    df = pd.read_csv(source_path)
    
    rows = len(df)
    columns = list(df.columns)
    
    nulls = {}
    for col in columns:
        null_count = df[col].isna().sum()
        if null_count > 0:
            nulls[col] = int(null_count)
    
    metadata = {
        "rows": rows,
        "columns": columns,
        "nulls": nulls
    }
    
    print(json.dumps(metadata))
    
    Path(bronze_dir).mkdir(parents=True, exist_ok=True)
    output_path = Path(bronze_dir) / output_filename
    df.to_csv(output_path, index=False)
    
except Exception as e:
    error_json = {
        "error": str(e),
        "type": type(e).__name__
    }
    print(json.dumps(error_json))
