import pandas as pd
from pathlib import Path

try:
    input_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input')
    output_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output')
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    input_file = input_dir / 'sample.csv'
    
    df = pd.read_csv(input_file)
    
    print('='*60)
    print('DATA RETRIEVAL SUMMARY')
    print('='*60)
    print(f'File: {input_file.name}')
    print(f'Total rows: {len(df)}')
    print(f'Total columns: {len(df.columns)}')
    print(f'\nColumn names:')
    for i, col in enumerate(df.columns, 1):
        print(f'  {i}. {col}')
    
    print(f'\nNull counts per column:')
    null_counts = df.isnull().sum()
    for col, count in null_counts.items():
        print(f'  {col}: {count}')
    
    output_file = output_dir / 'sample.csv'
    df.to_csv(output_file, index=False)
    
    print(f'\nOutput file written to: {output_file}')
    print('='*60)
    print('RETRIEVAL COMPLETE - SUCCESS')
    print('='*60)
    
except Exception as e:
    print(f'ERROR: {str(e)}')
    import traceback
    traceback.print_exc()
