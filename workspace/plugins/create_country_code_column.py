import pandas as pd
from agentteam.models.structured_outputs import TransformationRule

def create_country_code_column(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame:
    df = df.copy()
    
    def extract_country_code(country):
        if pd.isna(country):
            return None
        
        country_str = str(country).strip().upper()
        
        country_codes = {
            'BRAZIL': 'BR', 'VIETNAM': 'VN', 'COLOMBIA': 'CO', 'INDONESIA': 'ID',
            'ETHIOPIA': 'ET', 'UGANDA': 'UG', 'INDIA': 'IN', 'PERU': 'PE',
            'MEXICO': 'MX', 'GUATEMALA': 'GT', 'NICARAGUA': 'NI', 'CHINA': 'CN',
            'MALAYSIA': 'MY', 'COSTA RICA': 'CR', 'COTE D\'IVOIRE': 'CI',
            'IVORY COAST': 'CI', 'TANZANIA': 'TZ', 'PAPUA NEW GUINEA': 'PG',
            'KENYA': 'KE', 'THAILAND': 'TH'
        }
        
        if country_str in country_codes:
            return country_codes[country_str]
        
        if len(country_str) >= 2:
            return country_str[:2]
        
        return country_str
    
    df['Country_Code'] = df['country'].apply(extract_country_code)
    
    return df