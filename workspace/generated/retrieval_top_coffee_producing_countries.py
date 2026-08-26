import json
import pandas as pd
from pathlib import Path

try:
    input_path = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\top_coffee_producing_countries.json'
    output_path = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze\top_coffee_producing_countries.json'
    
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(data, f)
    
    df = pd.json_normalize(data) if isinstance(data, list) else pd.DataFrame([data])
    
    rows = len(df)
    columns = list(df.columns)
    nulls = {col: int(df[col].isna().sum()) for col in columns}
    
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
