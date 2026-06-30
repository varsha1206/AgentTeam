import pandas as pd
from pathlib import Path

try:
    input_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input')
    output_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    csv_files = [
        input_dir / 'sample.csv',
        input_dir / 'sample2.csv',
        input_dir / 'sample3.csv'
    ]
    
    print('=' * 80)
    print('DATA RETRIEVAL SUMMARY')
    print('=' * 80)
    
    for csv_file in csv_files:
        if csv_file.exists():
            print(f'\nProcessing: {csv_file.name}')
            print('-' * 80)
            
            df = pd.read_csv(csv_file)
            
            print(f'Row Count: {len(df)}')
            print(f'Column Names: {list(df.columns)}')
            print(f'Null Counts per Column:')
            for col in df.columns:
                null_count = df[col].isnull().sum()
                print(f'  {col}: {null_count}')
            
            output_file = output_dir / csv_file.name
            df.to_csv(output_file, index=False)
            print(f'SUCCESS: Written to {output_file}')
        else:
            print(f'ERROR: File not found - {csv_file}')
    
    print('\n' + '=' * 80)
    print('RETRIEVAL COMPLETE')
    print('=' * 80)

except Exception as e:
    print(f'ERROR: {str(e)}')
    import traceback
    traceback.print_exc()
