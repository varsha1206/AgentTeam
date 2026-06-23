import pandas as pd
from pathlib import Path

try:
    # Define paths
    input_file = Path(r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input\sample.csv")
    output_dir = Path(r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output")
    output_file = output_dir / "sample.csv"
    
    # Read the CSV file
    df = pd.read_csv(input_file)
    
    # Print summary information
    print("=" * 60)
    print("DATA RETRIEVAL SUMMARY")
    print("=" * 60)
    print(f"File: sample.csv")
    print(f"Row Count: {len(df)}")
    print(f"\nColumn Names: {list(df.columns)}")
    print(f"Total Columns: {len(df.columns)}")
    print("\nNull Counts per Column:")
    null_counts = df.isnull().sum()
    for col, null_count in null_counts.items():
        print(f"  {col}: {null_count}")
    print("\nData Types:")
    for col, dtype in df.dtypes.items():
        print(f"  {col}: {dtype}")
    print("=" * 60)
    
    # Write raw data to output folder
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    
    print(f"\n✓ Raw data successfully written to: {output_file}")
    print(f"✓ Retrieval completed successfully.")
    
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
