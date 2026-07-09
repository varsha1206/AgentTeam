import pandas as pd

def quarantine_duplicates(df: pd.DataFrame, rule) -> pd.DataFrame:
    """Quarantine rows with duplicate values in specified columns."""
    try:
        columns = list(rule.columns) if hasattr(rule, 'columns') else []
    except:
        columns = []
    
    if not columns or len(columns) == 0:
        return df
    
    valid_df = df.copy()
    
    for col in columns:
        if col not in valid_df.columns:
            continue
        
        dup_mask = valid_df.duplicated(subset=[col], keep='first')
        valid_df = valid_df[~dup_mask]
    
    return valid_df
