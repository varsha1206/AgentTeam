import pandas as pd
import json
from pathlib import Path

try:
    source_path = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\broken_employee_data.csv'
    bronze_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze')
    bronze_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(source_path)
    
    output_file = bronze_dir / 'broken_employee_data.csv'
    df.to_csv(output_file, index=False)
    
    rows = len(df)
    columns = df.columns.tolist()
    nulls = {col: int(df[col].isna().sum()) for col in df.columns}
    
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
