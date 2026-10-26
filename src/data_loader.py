"""
ONS Data Loader Utilities
=========================
Modules to load and clean UK Office for National Statistics (ONS) Quarterly
and Annual financial datasets from Excel spreadsheets.
"""

import pandas as pd
import numpy as np


def load_ons_quarterly_data_excel(filepath: str, sheet_name: str, table_index: int = 2) -> pd.DataFrame:
    """
    Load raw ONS quarterly spreadsheet data, strip headers, map quarterly time strings
    to standard calendar period ends (e.g., '1997 Q1' -> '1997-03-31'), and cast columns
    to numeric types.
    
    If a worksheet stacks multiple tables (e.g., Table 1 Not Seasonally Adjusted and
    Table 2 Seasonally Adjusted in ONS capital expenditure sheets), table_index selects
    the target table (default: 2 for Seasonally Adjusted).
    """
    df_raw_full = pd.read_excel(filepath, sheet_name=sheet_name, header=None)
    table_markers = df_raw_full[df_raw_full.iloc[:, 0].astype(str).str.contains(r'^Table \d+:', case=False, na=False)].index.tolist()
    
    if len(table_markers) > 1:
        if table_index == 2 and len(table_markers) >= 2:
            start_row = table_markers[1] + 1
            df_raw = df_raw_full.iloc[start_row + 1:].copy()
            df_raw.columns = df_raw_full.iloc[start_row].values
        else:
            end_row = table_markers[1]
            df_raw = df_raw_full.iloc[4:end_row].copy()
            df_raw.columns = df_raw_full.iloc[3].values
    else:
        df_raw = pd.read_excel(filepath, sheet_name=sheet_name, header=3)
        df_raw = df_raw.iloc[1:].copy()

    df_raw.rename(columns={df_raw.columns[0]: 'Time'}, inplace=True)
    df = df_raw.copy()

    def quarter_to_date(q_str):
        if not isinstance(q_str, str):
            return np.nan
        parts = q_str.strip().split(' ')
        if len(parts) == 2 and parts[1] in ['Q1', 'Q2', 'Q3', 'Q4']:
            year, q = parts
            q_map = {'Q1': '-03-31', 'Q2': '-06-30', 'Q3': '-09-30', 'Q4': '-12-31'}
            return f"{year}{q_map.get(q)}"
        return np.nan

    df['Date'] = pd.to_datetime(df['Time'].apply(quarter_to_date), errors='coerce')

    cols_to_convert = [c for c in df.columns if c not in ['Time', 'Date']]
    for col in cols_to_convert:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


def load_ons_annual_data_excel(filepath: str, sheet_name: str, sector_col_name: str) -> pd.DataFrame:
    """
    Load raw ONS annual national balance sheet estimates, extract Total Non-Financial Assets,
    Financial Liabilities, and Net Worth using official ONS CDID series codes:
      - Table 5 (Private Non-Financial / PNFC): NG2Y (Assets), NLBB (Liabilities), TMPN (B.90 Net Worth)
      - Table 3 (Non-Financial Total / NFC):     NG2I (Assets), NONT (Liabilities), CGRV (B.90 Net Worth)
      - Table 4 (Public Non-Financial):          NG2Q (Assets), NKIF (Liabilities), CGRW (B.90 Net Worth)
    """
    df_raw = pd.read_excel(filepath, sheet_name=sheet_name, header=None)

    cdid_row_idx = None
    for r in range(min(15, len(df_raw))):
        row_vals = [str(x).strip() for x in df_raw.iloc[r].dropna()]
        if any(code in row_vals for code in ['NG2Y', 'NG2I', 'NG2Q', 'NLBB', 'NONT', 'NKIF', 'TMPN', 'CGRV', 'CGRW']):
            cdid_row_idx = r
            break

    SECTOR_CDIDS = {
        'Table 5': {'assets': 'NG2Y', 'liabilities': 'NLBB', 'net_worth': 'TMPN'},
        'Table 3': {'assets': 'NG2I', 'liabilities': 'NONT', 'net_worth': 'CGRV'},
        'Table 4': {'assets': 'NG2Q', 'liabilities': 'NKIF', 'net_worth': 'CGRW'},
    }

    if cdid_row_idx is not None and sheet_name in SECTOR_CDIDS:
        cdid_row = df_raw.iloc[cdid_row_idx].astype(str).str.strip()
        target = SECTOR_CDIDS[sheet_name]

        col_assets = (cdid_row == target['assets']).idxmax() if (cdid_row == target['assets']).any() else None
        col_liab = (cdid_row == target['liabilities']).idxmax() if (cdid_row == target['liabilities']).any() else None
        col_nw = (cdid_row == target['net_worth']).idxmax() if (cdid_row == target['net_worth']).any() else None

        df_data = df_raw.iloc[cdid_row_idx + 1:].copy()
        df_data.rename(columns={0: 'Year', col_assets: 'TotalAssets', col_liab: 'TotalLiabilities', col_nw: 'Net worth'}, inplace=True)
        df_data['Year'] = pd.to_numeric(df_data['Year'], errors='coerce')
        df_clean = df_data[df_data['Year'].notna()].copy()
        df_clean['Year'] = df_clean['Year'].astype(int)

        for col in ['TotalAssets', 'TotalLiabilities', 'Net worth']:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

        df_clean['Sector'] = sector_col_name
        return df_clean[['Year', 'Sector', 'TotalAssets', 'TotalLiabilities', 'Net worth']].dropna(subset=['TotalAssets', 'TotalLiabilities'])

    # Fallback to general header parsing if CDIDs not detected
    df_raw = pd.read_excel(filepath, sheet_name=sheet_name, header=1)
    df_raw.rename(columns={df_raw.columns[0]: 'Year'}, inplace=True)
    df = df_raw[pd.to_numeric(df_raw['Year'], errors='coerce').notna()].copy()
    df['Year'] = df['Year'].astype(int)
    df['Sector'] = sector_col_name
    return df
