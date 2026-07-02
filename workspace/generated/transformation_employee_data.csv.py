import pandas as pd
import json
from pathlib import Path

try:
    # Read the bronze file
    bronze_file = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\bronze\employee_data.csv"
    df = pd.read_csv(bronze_file)
    
    total_rows_input = len(df)
    quarantined_rows_list = []
    
    # Step 1: rename_to_snake_case
    df.columns = df.columns.str.replace(r'(?<!^)(?=[A-Z])', '_', regex=True).str.lower()
    
    # Step 2: coerce_numeric on tenure, satisfaction, last_evaluation
    for col in ['tenure', 'satisfaction', 'last_evaluation']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Step 3: fill_missing_value for filed_complaint with '0'
    if 'filed_complaint' in df.columns:
        df['filed_complaint'] = df['filed_complaint'].fillna(0)
    
    # Step 4: fill_missing_value for recently_promoted with '0'
    if 'recently_promoted' in df.columns:
        df['recently_promoted'] = df['recently_promoted'].fillna(0)
    
    # Step 5: fill_missing_value for department with 'unknown'
    if 'department' in df.columns:
        df['department'] = df['department'].fillna('unknown')
    
    # Step 6: quarantine_missing - rows with any NULL values in non-nullable columns
    nullable_cols = {'department', 'tenure', 'recently_promoted', 'satisfaction', 'last_evaluation', 'filed_complaint'}
    non_nullable_cols = {'status', 'salary', 'n_projects', 'avg_monthly_hrs'}
    
    missing_mask = df[list(non_nullable_cols)].isna().any(axis=1)
    quarantined_missing = df[missing_mask].copy()
    quarantined_missing['quarantine_reason'] = 'Missing required fields'
    quarantined_rows_list.append(quarantined_missing)
    
    df = df[~missing_mask]
    
    # Step 7: quarantine_duplicates
    duplicates_mask = df.duplicated(keep=False)
    quarantined_duplicates = df[duplicates_mask].copy()
    quarantined_duplicates['quarantine_reason'] = 'Duplicate row'
    quarantined_rows_list.append(quarantined_duplicates)
    
    df = df[~duplicates_mask]
    
    # Combine all quarantined rows
    if quarantined_rows_list:
        quarantined_df = pd.concat(quarantined_rows_list, ignore_index=True)
    else:
        quarantined_df = pd.DataFrame(columns=list(df.columns) + ['quarantine_reason'])
    
    total_rows_output = len(df)
    total_quarantined = len(quarantined_df)
    
    # Write transformed data to temp
    output_file = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\temp\transformed_employee_data.csv"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    
    # Write quarantined data
    quarantine_file = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\output\quarantine\quarantine_employee_data.csv"
    Path(quarantine_file).parent.mkdir(parents=True, exist_ok=True)
    quarantined_df.to_csv(quarantine_file, index=False)
    
    # Print result JSON
    result = {
        "valid_rows": total_rows_output,
        "quarantined_rows": total_quarantined,
        "quarantine_path": quarantine_file
    }
    print(json.dumps(result))

except Exception as e:
    print(json.dumps({"error": str(e)}))
