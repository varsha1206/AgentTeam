import pandas as pd
import json
from pathlib import Path

try:
    source_path = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\broken_employee_data.csv"
    output_dir = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze"
    output_filename = "broken_employee_data.csv"
    
    df = pd.read_csv(source_path)
    
    rows = len(df)
    columns = df.columns.tolist()
    nulls = {col: int(df[col].isnull().sum()) for col in columns}
    
    result = {
        "files": [
            {
                "filename": output_filename,
                "rows": rows,
                "columns": columns,
                "nulls": nulls
            }
        ]
    }
    
    output_path = Path(output_dir) / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(output_path, index=False)
    
    print(json.dumps(result))
    
except Exception as e:
    error_result = {
        "error": str(e),
        "type": type(e).__name__
    }
    print(json.dumps(error_result))
