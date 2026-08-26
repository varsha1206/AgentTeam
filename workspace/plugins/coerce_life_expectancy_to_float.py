import pandas as pd
from agentteam.models.structured_outputs import TransformationRule

def coerce_life_expectancy_to_float(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    df = df.copy()
    life_expectancy_cols = ['life_expectancy_total', 'life_expectancy_male', 'life_expectancy_female']
    
    for col in life_expectancy_cols:
        if col in df.columns:
            def convert_to_float(val):
                if pd.isna(val):
                    return val
                if isinstance(val, (int, float)):
                    return float(val)
                if isinstance(val, str):
                    val = val.strip().lower()
                    word_map = {
                        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
                        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
                        'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
                        'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
                        'eighty': 80, 'ninety': 90
                    }
                    if 'point' in val:
                        parts = val.split('point')
                        if len(parts) == 2:
                            integer_word = parts[0].strip()
                            decimal_word = parts[1].strip()
                            integer_val = word_map.get(integer_word)
                            decimal_val = word_map.get(decimal_word)
                            if integer_val is not None and decimal_val is not None:
                                return float(f"{integer_val}.{decimal_val}")
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return pd.NA
                return pd.NA
            
            df[col] = df[col].apply(convert_to_float)
    
    return df