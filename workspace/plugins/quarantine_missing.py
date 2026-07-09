import pandas as pd

def quarantine_missing(df: pd.DataFrame, rule) -> pd.DataFrame:
    """Quarantine rows with missing values in specified columns."""
    columns = rule.get('columns', [])
    
    # Find rows where any of the specified columns are null
    mask = df[columns].isnull().any(axis=1)
    quarantined = df[mask].copy()
    valid = df[~mask].copy()
    
    # Add quarantine reason
    quarantined['quarantine_reason'] = 'Missing value in required column: ' + quarantined[columns].isnull().idxmax(axis=1)
    
    return valid, quarantined
