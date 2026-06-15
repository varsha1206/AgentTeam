import pandas as pd
from pathlib import Path

try:
    # Define input and output paths
    input_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\input')
    output_dir = Path(r'C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output')
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all CSV files
    csv_files = list(input_dir.glob('*.csv'))
    
    if not csv_files:
        print("ERROR: No CSV files found in input directory.")
    else:
        print(f"Found {len(csv_files)} CSV file(s).\n")
        
        for csv_file in csv_files:
            print(f"Processing: {csv_file.name}")
            print("=" * 60)
            
            # Read the CSV file
            df = pd.read_csv(csv_file)
            
            # Print summary information
            print(f"Row count: {len(df)}")
            print(f"\nColumn names: {list(df.columns)}")
            
            # Calculate null counts per column
            null_counts = df.isnull().sum()
            print(f"\nNull counts per column:")
            for col in df.columns:
                print(f"  {col}: {null_counts[col]}")
            
            # Write raw data to output folder
            output_file = output_dir / csv_file.name
            df.to_csv(output_file, index=False)
            print(f"\nData written to: {output_file}")
            print("=" * 60)
            print()
        
        print("Retrieval and processing completed successfully.")

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
