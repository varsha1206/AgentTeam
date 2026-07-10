import pandas as pd
import json
from pathlib import Path

try:
    source_path = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\broken_employee_data.csv"
    output_dir = Path(r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(source_path)
    
    rows = len(df)
    columns = df.columns.tolist()
    nulls = df.isnull().sum().to_dict()
    
    result = {
        "rows": rows,
        "columns": columns,
        "nulls": nulls
    }
    print(json.dumps(result))
    
    output_file = output_dir / "broken_employee_data.csv"
    df.to_csv(output_file, index=False)
    
except Exception as e:
    error_result = {
        "error": str(e),
        "type": type(e).__name__
    }
    print(json.dumps(error_result))
