import pandas as pd
from pathlib import Path

try:
    input_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\employee_data.csv'
    output_dir = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze'
    
    df = pd.read_csv(input_file)
    
    print('=== DATA RETRIEVAL SUMMARY ===')
    print(f'File: employee_data.csv')
    print(f'Row count: {len(df)}')
    print(f'Column count: {len(df.columns)}')
    print(f'Column names: {list(df.columns)}')
    print('\nNull counts per column:')
    null_counts = df.isnull().sum()
    for col, null_count in null_counts.items():
        print(f'  {col}: {null_count}')
    
    output_file = Path(output_dir) / 'employee_data.csv'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    
    print(f'\nSUCCESS: Raw data written to {output_file}')
    
except Exception as e:
    print(f'ERROR: {str(e)}')
    import traceback
    traceback.print_exc()
