
import pandas as pd

class Transformations:
    def __init__(self):
        self.pd = pd
        
    def drop_empty_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        df.dropna(inplace=True)
        return df
    
    def assign_column_names(
        self,column_names: list, df: pd.DataFrame) -> pd.DataFrame:

        if len(df.columns) != len(column_names):
            raise ValueError("Not valid column names in file")
        
        df.columns = column_names
        return df
    