import json
import pandas as pd
from pathlib import Path

try:
    # Read CSV
    csv_path = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\broken_employee_data.csv'
    df = pd.read_csv(csv_path)
    
    # Get statistics
    rows = len(df)
    columns = list(df.columns)
    nulls = {col: int(df[col].isnull().sum()) for col in columns}
    
    # Print JSON statistics to stdout
    stats = {
        'rows': rows,
        'columns': columns,
        'nulls': nulls
    }
    print(json.dumps(stats))
    
    # Write raw data to bronze
    output_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'broken_employee_data.csv'
    
    df.to_csv(output_path, index=False)
    
except Exception as e:
    error_json = {
        'error': str(e),
        'type': type(e).__name__
    }
    print(json.dumps(error_json))
