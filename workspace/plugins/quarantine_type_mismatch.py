import pandas as pd

def quarantine_type_mismatch(df: pd.DataFrame, rule) -> pd.DataFrame:
    """Quarantine rows where specified columns cannot be coerced to the expected numeric type."""
    columns = rule.get('columns', [])
    
    quarantined_list = []
    valid = df.copy()
    
    for col in columns:
        if col in valid.columns:
            # Try to convert to numeric
            before_count = len(valid)
            temp = pd.to_numeric(valid[col], errors='coerce')
            
            # Find rows that couldn't be converted (became NaN after coerce)
            mask = temp.isnull() & valid[col].notnull()
            
            if mask.any():
                quarantined = valid[mask].copy()
                quarantined['quarantine_reason'] = 'Type mismatch in column: ' + col
                quarantined_list.append(quarantined)
                valid = valid[~mask].copy()
    
    # Combine all quarantined rows
    if quarantined_list:
        all_quarantined = pd.concat(quarantined_list, ignore_index=True)
    else:
        all_quarantined = pd.DataFrame(columns=valid.columns.tolist() + ['quarantine_reason'])
    
    return valid, all_quarantined
