import pandas as pd
import json
import shutil
from pathlib import Path

try:
    input_path = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\broken_employee_data.csv"
    output_path = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze\broken_employee_data.csv"
    
    # Read CSV file
    df = pd.read_csv(input_path)
    
    # Count rows and columns
    num_rows = len(df)
    columns = df.columns.tolist()
    
    # Count nulls per column
    null_counts = df.isnull().sum().to_dict()
    nulls = {col: int(count) for col, count in null_counts.items()}
    
    # Copy file to bronze directory
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(input_path, output_path)
    
    # Print analysis as JSON
    result = {
        "files": [
            {
                "filename": "broken_employee_data.csv",
                "rows": num_rows,
                "columns": columns,
                "nulls": nulls
            }
        ]
    }
    print(json.dumps(result))
    
except Exception as e:
    error_result = {
        "error": str(e),
        "type": type(e).__name__
    }
    print(json.dumps(error_result))
