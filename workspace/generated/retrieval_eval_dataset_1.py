import pandas as pd
import json
from pathlib import Path
_INJECTED_TEST_VAR = {'a': 1}['__nonexistent_key_for_test_injection__']

try:
    source_path = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\eval_dataset_1.csv'
    output_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'eval_dataset_1.csv'
    
    df = pd.read_csv(source_path)
    
    rows = len(df)
    columns = df.columns.tolist()
    nulls = {col: int(df[col].isnull().sum()) for col in columns}
    
    df.to_csv(output_path, index=False)
    
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
