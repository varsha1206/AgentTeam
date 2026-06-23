import pandas as pd
from pathlib import Path

try:
    input_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input')
    output_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output')
    
    csv_file = input_dir / 'sample.csv'
    
    if not csv_file.exists():
        print(f"ERROR: File not found - {csv_file}")
        exit(1)
    
    df = pd.read_csv(csv_file)
    
    print("=" * 80)
    print("DATA RETRIEVAL SUMMARY")
    print("=" * 80)
    print(f"\nFile: {csv_file.name}")
    print(f"Row count: {len(df)}")
    print(f"Column count: {len(df.columns)}")
    print(f"\nColumn names:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")
    
    print(f"\nNull counts per column:")
    null_counts = df.isnull().sum()
    for col in df.columns:
        print(f"  {col}: {null_counts[col]}")
    
    print(f"\nData types:")
    for col in df.columns:
        print(f"  {col}: {df[col].dtype}")
    
    output_file = output_dir / 'sample.csv'
    df.to_csv(output_file, index=False)
    
    print(f"\n[OK] Raw data successfully written to: {output_file}")
    print("=" * 80)

except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)