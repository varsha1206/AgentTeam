import pandas as pd
from agentteam.models.structured_outputs import TransformationRule

def coerce_percentage_to_float(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    df = df.copy()
    
    def parse_percentage(val):
        if pd.isna(val):
            return float('nan')
        
        val_str = str(val).strip()
        
        if '%' in val_str:
            val_str = val_str.replace('%', '').strip()
        
        percentage_words = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
            'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13',
            'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
            'eighteen': '18', 'nineteen': '19', 'twenty': '20', 'thirty': '30',
            'forty': '40', 'fifty': '50', 'sixty': '60', 'seventy': '70',
            'eighty': '80', 'ninety': '90', 'hundred': '100'
        }
        
        val_lower = val_str.lower()
        for word, num in percentage_words.items():
            if word in val_lower:
                val_str = val_str.replace(word, num)
        
        val_str = val_str.replace(' point ', '.')
        val_str = val_str.replace(' ', '')
        
        try:
            return float(val_str)
        except ValueError:
            return float('nan')
    
    if rule.columns:
        target_cols = rule.columns
    else:
        target_cols = df.columns.tolist()
    
    for col in target_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_percentage)
    
    return df