import pandas as pd
import json
from pathlib import Path

try:
    source_path = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\eval_dataset_3.csv"
    output_dir = Path(r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = "eval_dataset_3.csv"
    output_path = output_dir / output_filename
    
    df = pd.read_csv(source_path)
    
    num_rows = len(df)
    columns = df.columns.tolist()
    
    nulls = {}
    for col in columns:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            nulls[col] = int(null_count)
    
    df.to_csv(output_path, index=False)
    
    result = {
        "rows": num_rows,
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
