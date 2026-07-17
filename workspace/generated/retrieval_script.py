import pandas as pd
import json
from pathlib import Path

try:
    source_path = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\broken_employee_data.csv"
    output_dir = Path(r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze")
    output_filename = "broken_employee_data.csv"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_filename
    
    df = pd.read_csv(source_path)
    
    df.to_csv(output_path, index=False)
    
    rows = len(df)
    columns = df.columns.tolist()
    
    nulls = {}
    for col in columns:
        null_count = df[col].isna().sum()
        if null_count > 0:
            nulls[col] = int(null_count)
    
    result = {
        "rows": rows,
        "columns": columns,
        "nulls": nulls
    }
    
    print(json.dumps(result))

except Exception as e:
    error_result = {
        "error": str(e),
        "type": type(e).__name__
    }
    print(json.dumps(error_result))
