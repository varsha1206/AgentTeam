import pandas as pd
from pathlib import Path

input_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input')
output_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output')

output_dir.mkdir(parents=True, exist_ok=True)

csv_files = list(input_dir.glob('*.csv'))

if not csv_files:
    print("ERROR: No CSV files found in input directory")
    exit(1)

print("RETRIEVAL SUMMARY")
print("=" * 80)

for csv_file in csv_files:
    try:
        df = pd.read_csv(csv_file)
        
        print(f"\nFile: {csv_file.name}")
        print(f"Row count: {len(df)}")
        print(f"Column names: {list(df.columns)}")
        
        print("Null counts per column:")
        null_counts = df.isnull().sum()
        for col in df.columns:
            print(f"  {col}: {null_counts[col]}")
        
        output_file = output_dir / csv_file.name
        df.to_csv(output_file, index=False)
        print(f"Written to: {output_file}")
        
    except Exception as e:
        print(f"ERROR processing {csv_file.name}: {str(e)}")

print("\n" + "=" * 80)
print("RETRIEVAL COMPLETE")
