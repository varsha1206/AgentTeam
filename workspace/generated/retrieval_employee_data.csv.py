import pandas as pd
import json
from pathlib import Path

try:
    source_path = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\employee_data.csv'
    output_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze')
    output_filename = 'employee_data.csv'
    
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
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_filename
    df.to_csv(output_path, index=False)
    
except Exception as e:
    error_json = {
        "error": str(e),
        "type": type(e).__name__
    }
    print(json.dumps(error_json))
