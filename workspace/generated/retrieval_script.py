import pandas as pd
import json
from pathlib import Path

try:
    output_dir = Path("C:/Users/Varsha/OneDrive/Documents/Github/AgentTeam/workspace/output/bronze")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    files_metadata = []
    
    csv_path = "C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\input\\broken_employee_data.csv"
    df_csv = pd.read_csv(csv_path)
    
    null_counts = {}
    for col in df_csv.columns:
        null_counts[col] = int(df_csv[col].isnull().sum())
    
    files_metadata.append({
        "filename": "broken_employee_data.csv",
        "rows": len(df_csv),
        "columns": df_csv.columns.tolist(),
        "nulls": null_counts
    })
    
    csv_output_path = output_dir / "broken_employee_data.csv"
    df_csv.to_csv(csv_output_path, index=False)
    
    json_path = "C:\\Users\\Varsha\\OneDrive\\Documents\\Github\\AgentTeam\\workspace\\input\\broken_student_data.json"
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    
    if isinstance(json_data, list):
        df_json = pd.DataFrame(json_data)
    else:
        df_json = pd.DataFrame([json_data])
    
    null_counts_json = {}
    for col in df_json.columns:
        null_counts_json[col] = int(df_json[col].isnull().sum())
    
    files_metadata.append({
        "filename": "broken_student_data.json",
        "rows": len(df_json),
        "columns": df_json.columns.tolist(),
        "nulls": null_counts_json
    })
    
    json_output_path = output_dir / "broken_student_data.json"
    with open(json_output_path, 'w') as f:
        json.dump(json_data, f)
    
    result = {"files": files_metadata}
    print(json.dumps(result))

except Exception as e:
    error_result = {"error": str(e), "type": type(e).__name__}
    print(json.dumps(error_result))
