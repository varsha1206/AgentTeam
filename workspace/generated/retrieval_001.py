import pandas as pd
from pathlib import Path

try:
    input_file = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\employee_data.csv'
    output_dir = r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze'
    
    df = pd.read_csv(input_file)
    
    print("=" * 60)
    print("DATA RETRIEVAL SUMMARY")
    print("=" * 60)
    print(f"File: employee_data.csv")
    print(f"Row count: {len(df)}")
    print(f"\nColumn names: {list(df.columns)}")
    print(f"\nNull counts per column:")
    for col in df.columns:
        null_count = df[col].isnull().sum()
        print(f"  {col}: {null_count}")
    
    output_path = Path(output_dir) / 'employee_data.csv'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
    print("\n" + "=" * 60)
    print("Raw data written to: " + str(output_path))
    print("Status: SUCCESS")
    print("=" * 60)
    
except Exception as e:
    print("ERROR: " + str(e))
    raise
