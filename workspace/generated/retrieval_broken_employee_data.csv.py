import pandas as pd
import json
from pathlib import Path

try:
    # Read the CSV file
    source_path = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\broken_employee_data.csv"
    df = pd.read_csv(source_path)
    
    # Analyze the data
    num_rows = len(df)
    columns = df.columns.tolist()
    
    # Count nulls per column
    nulls = {}
    for col in columns:
        null_count = df[col].isna().sum()
        if null_count > 0:
            nulls[col] = int(null_count)
    
    # Print JSON report to stdout
    report = {
        "rows": num_rows,
        "columns": columns,
        "nulls": nulls
    }
    print(json.dumps(report))
    
    # Write raw data to bronze output
    output_path = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze\broken_employee_data.csv"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
except Exception as e:
    error_report = {
        "error": str(e),
        "type": type(e).__name__
    }
    print(json.dumps(error_report))
