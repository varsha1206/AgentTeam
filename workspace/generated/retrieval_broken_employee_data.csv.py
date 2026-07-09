import pandas as pd
import json
from pathlib import Path

try:
    input_path = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\broken_employee_data.csv"
    bronze_dir = Path(r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze")
    bronze_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(input_path)
    
    num_rows = len(df)
    columns = df.columns.tolist()
    nulls = {col: int(df[col].isna().sum()) for col in columns}
    
    output = {
        "rows": num_rows,
        "columns": columns,
        "nulls": nulls
    }
    print(json.dumps(output))
    
    output_file = bronze_dir / "broken_employee_data.csv"
    df.to_csv(output_file, index=False)
    
except Exception as e:
    error_output = {"error": str(e), "type": type(e).__name__}
    print(json.dumps(error_output))