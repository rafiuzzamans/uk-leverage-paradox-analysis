"""
Pipeline Extraction Test Suite
==============================
Verifies that ONS datasets load without error and conform to expected schemas.
"""

import sys
import os

# Add root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_loader import load_ons_quarterly_data_excel, load_ons_annual_data_excel

def test_pipeline():
    print("[1/3] Testing Profitability Table 2 loading...")
    df_profit = load_ons_quarterly_data_excel('2024q2referencetables.xlsx', sheet_name='Table 2')
    assert not df_profit.empty, "df_profit should not be empty"
    assert 'Date' in df_profit.columns, "Date column must be created"
    print(f"      Passed. Rows: {len(df_profit)}, Columns: {len(df_profit.columns)}")

    print("[2/3] Testing Balance Sheet Table 5 (PNFC) loading...")
    df_pnfc = load_ons_annual_data_excel('nbsreferencetables2024.xlsx', sheet_name='Table 5', sector_col_name='Private Non-Financial')
    assert not df_pnfc.empty, "df_pnfc should not be empty"
    assert 'TotalAssets' in df_pnfc.columns, "TotalAssets column must exist"
    print(f"      Passed. Rows: {len(df_pnfc)}")

    print("[3/3] Testing GFCF Investment loading...")
    df_invest = load_ons_quarterly_data_excel('ukea2023q2table2corpssectorv2.xlsx', sheet_name='3.1.7_B')
    assert not df_invest.empty, "df_invest should not be empty"
    print(f"      Passed. Rows: {len(df_invest)}")

    print("\nAll pipeline verification tests passed successfully!")

if __name__ == '__main__':
    test_pipeline()
