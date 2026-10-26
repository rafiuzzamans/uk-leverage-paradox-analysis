import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

os.makedirs('figures', exist_ok=True)

FILE_PROFITABILITY_EXCEL = '2024q2referencetables.xlsx'
FILE_INVESTMENT_EXCEL = 'ukea2023q2table2corpssectorv2.xlsx'
FILE_BALANCE_EXCEL = 'nbsreferencetables2024.xlsx'

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data_loader import load_ons_quarterly_data_excel, load_ons_annual_data_excel

print("Processing ONS Data...")
df_profit = load_ons_quarterly_data_excel(FILE_PROFITABILITY_EXCEL, sheet_name='Table 2')
id_vars = ['Time', 'Date']
value_vars_net = [
    'UK Continental Shelf companies % [note 2] Net [note 4] [note 5]',
    'UK Non-Continental Shelf Private Non-Financial Corporations % - Net [note 4] [note 5]',
    'Manufacturing sector Private Non-Financial Corporations % - Net [note 4] [note 5]',
    'Service sector Private Non-Financial Corporations % - Net [note 4] [note 5]'
]
df_profit_long = df_profit.melt(id_vars=id_vars, value_vars=value_vars_net, var_name='SectorFull', value_name='NetRateReturn')
df_profit_long['Sector'] = df_profit_long['SectorFull'].str.split('%').str[0].str.split(' - ').str[-1].str.replace(' sector', '').str.replace(' companies', '').str.strip()
df_profit_long = df_profit_long.dropna(subset=['NetRateReturn']).sort_values('Date')

df_pnfc = load_ons_annual_data_excel(FILE_BALANCE_EXCEL, sheet_name='Table 5', sector_col_name='Private Non-Financial')
df_nfc = load_ons_annual_data_excel(FILE_BALANCE_EXCEL, sheet_name='Table 3', sector_col_name='Non-Financial')
df_invest_raw = load_ons_quarterly_data_excel(FILE_INVESTMENT_EXCEL, sheet_name='3.1.7_B')
df_invest = df_invest_raw[['Date', 'Gross fixed capital formation']].copy()
df_invest.rename(columns={'Gross fixed capital formation': 'InvestmentAmount'}, inplace=True)
df_invest = df_invest.dropna(subset=['InvestmentAmount'])

latest_year = df_pnfc['Year'].max()
df_profit_annual = df_profit_long.groupby(['Sector', df_profit_long['Date'].dt.year])['NetRateReturn'].mean().reset_index()
df_profit_annual.rename(columns={'Date': 'Year'}, inplace=True)

merged_c2 = pd.merge(df_pnfc[df_pnfc['Year'] == latest_year],
                     df_profit_annual[df_profit_annual['Year'] == latest_year],
                     on='Year', how='inner', suffixes=('_BS', '_PR'))

df_econ_profit = df_profit_long[['Date', 'Sector', 'NetRateReturn']].copy()
df_econ_profit['NextQuarterReturn'] = df_econ_profit.groupby('Sector')['NetRateReturn'].shift(-1)
df_merge_c7 = pd.merge(df_econ_profit, df_invest[['Date', 'InvestmentAmount']], on='Date', how='left')
df_merge_c7 = df_merge_c7.dropna(subset=['NextQuarterReturn', 'InvestmentAmount'])

df_corr_base = df_nfc.copy()
df_corr_base.rename(columns={'TotalAssets': 'TotalAssets_NFC', 'TotalLiabilities': 'TotalLiabilities_NFC'}, inplace=True)
df_corr_base = df_corr_base.set_index('Year')
df_corr_base['AssetGrowthRate'] = df_corr_base['TotalAssets_NFC'].pct_change() * 100
df_corr_base['LiabilityRatio'] = df_corr_base['TotalLiabilities_NFC'] / df_corr_base['TotalAssets_NFC'] * 100

df_invest_annual = df_invest.groupby(df_invest['Date'].dt.year)['InvestmentAmount'].sum().reset_index()
df_invest_annual.rename(columns={'Date': 'Year'}, inplace=True)
df_invest_annual = df_invest_annual.set_index('Year')

df_nfc_annual_profit = load_ons_quarterly_data_excel(FILE_PROFITABILITY_EXCEL, sheet_name='Table 2')
df_nfc_annual_profit = df_nfc_annual_profit[['Date', 'All Private Non-Financial Corporations % [note 1]: Net [note 4] [note 5]']].copy()
df_nfc_annual_profit['Year'] = df_nfc_annual_profit['Date'].dt.year
df_nfc_annual_profit.rename(columns={'All Private Non-Financial Corporations % [note 1]: Net [note 4] [note 5]': 'NetRateReturn'}, inplace=True)
df_nfc_annual_profit = df_nfc_annual_profit.groupby('Year')['NetRateReturn'].mean().reset_index().set_index('Year').dropna()

df_corr = pd.concat([df_corr_base, df_invest_annual, df_nfc_annual_profit], axis=1).dropna()
vars_for_corr = ['AssetGrowthRate', 'LiabilityRatio', 'InvestmentAmount', 'NetRateReturn']

df_pc = load_ons_annual_data_excel(FILE_BALANCE_EXCEL, sheet_name='Table 4', sector_col_name='Public Non-Financial')

df_lw_pnfc = df_pnfc[(df_pnfc['Year'] >= 2010)].copy()

plt.style.use('seaborn-v0_8-whitegrid')

# 1. Chart 1
plt.figure(figsize=(11, 5))
df_c1 = df_profit_long[df_profit_long['Date'].dt.year >= 2010]
sns.lineplot(data=df_c1, x='Date', y='NetRateReturn', hue='Sector', linewidth=2)
plt.title('Net Rate of Return by Sector (Quarterly, 2010-2024)', fontsize=13, fontweight='bold')
plt.xlabel('Date', fontsize=11)
plt.ylabel('Net Rate of Return (%)', fontsize=11)
plt.legend(title='Sector', loc='upper left')
plt.tight_layout()
plt.savefig('figures/chart1_profitability_trend.png', dpi=300)
plt.close()

# 2. Chart 2: Annual Liabilities relative to Assets vs Rate of Return (1997-2023)
plt.figure(figsize=(9, 6))
sns.regplot(data=df_corr, x='LiabilityRatio', y='NetRateReturn',
            scatter_kws={'alpha': 0.75, 'color': '#3b82f6', 's': 60},
            line_kws={'color': '#ef4444', 'linewidth': 2})
plt.title('Liabilities Relative to Non-Financial Assets vs Rate of Return (1997-2023)', fontsize=13, fontweight='bold')
plt.xlabel('Financial Liabilities ÷ Non-Financial Assets (%)', fontsize=11)
plt.ylabel('Net Rate of Return (Annual Avg, %)', fontsize=11)
plt.tight_layout()
plt.savefig('figures/chart2_asset_vs_return.png', dpi=300)
plt.close()

# 3. Chart 3
corr = df_corr[vars_for_corr].corr()
plt.figure(figsize=(7, 5))
sns.heatmap(corr, annot=True, fmt=".2f", cmap='coolwarm', vmin=-1, vmax=1, cbar_kws={'label': 'Correlation Coefficient'})
plt.title('Correlation Matrix – Key NFC Variables vs Profitability', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig('figures/chart3_correlation_matrix.png', dpi=300)
plt.close()

# 4. Chart 4
df_pnfc_assets = df_pnfc[['Year', 'TotalAssets']].rename(columns={'TotalAssets': 'Private Non-Financial Corp Assets'})
df_pc_assets = df_pc[['Year', 'TotalAssets']].rename(columns={'TotalAssets': 'Public Corp Assets'})
df_pivot = pd.merge(df_pnfc_assets, df_pc_assets, on='Year', how='inner').set_index('Year').tail(15)

fig, ax = plt.subplots(figsize=(11, 5))
df_pivot.plot(kind='area', stacked=True, ax=ax, colormap='viridis', alpha=0.85)
plt.title('Non-Financial Corporations Total Assets by Sector (2009-2023)', fontsize=13, fontweight='bold')
plt.xlabel('Year', fontsize=11)
plt.ylabel('Assets (£ million)', fontsize=11)
plt.legend(loc='upper left', title='Sector')
plt.tight_layout()
plt.savefig('figures/chart4_sector_assets_stacked.png', dpi=300)
plt.close()

# 5. Chart 5
plt.figure(figsize=(9, 5))
df_c5 = df_profit_long[df_profit_long['Date'].dt.year == latest_year]
sns.boxplot(data=df_c5, x='Sector', y='NetRateReturn', palette='Set2')
plt.title(f'Distribution of Net Rate of Return by PNFC Sector ({latest_year})', fontsize=13, fontweight='bold')
plt.xlabel('PNFC Sub-Sector', fontsize=11)
plt.ylabel('Net Rate of Return (%)', fontsize=11)
plt.xticks(rotation=15, ha='right')
plt.tight_layout()
plt.savefig('figures/chart5_return_distribution_boxplot.png', dpi=300)
plt.close()

# 6. Chart 6
plt.figure(figsize=(11, 5))
plt.plot(df_lw_pnfc['Year'], df_lw_pnfc['TotalLiabilities'], label='Total Financial Liabilities', marker='o', linewidth=2, color='#ef4444')
plt.plot(df_lw_pnfc['Year'], df_lw_pnfc['Net worth'], label='Net Worth', marker='s', linewidth=2, color='#3b82f6')
plt.title('PNFC Financial Liabilities vs Net Worth (2010-2023)', fontsize=13, fontweight='bold')
plt.xlabel('Year', fontsize=11)
plt.ylabel('Value (£ million)', fontsize=11)
plt.legend(loc='upper left')
plt.tight_layout()
plt.savefig('figures/chart6_liabilities_vs_networth_paradox.png', dpi=300)
plt.close()

# 7. Chart 7
plt.figure(figsize=(9, 6))
sns.scatterplot(data=df_merge_c7, x='InvestmentAmount', y='NextQuarterReturn', hue='Sector', alpha=0.75, s=60)
plt.xscale('log')
plt.title('Non-Financial Corp GFCF vs Next-Quarter Rate of Return by Sector', fontsize=13, fontweight='bold')
plt.xlabel('Non-Financial Corp GFCF (£ million, log scale)', fontsize=11)
plt.ylabel('Next Quarter Net Rate of Return (%)', fontsize=11)
plt.tight_layout()
plt.savefig('figures/chart7_investment_vs_future_return.png', dpi=300)
plt.close()

# 8. Chart 8 (Non-circular exploratory regression)
df_model = df_corr.dropna().copy()
X = df_model[['AssetGrowthRate', 'LiabilityRatio', 'InvestmentAmount']]
y = df_model['NetRateReturn']

if len(X) >= 5:
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    importances = pd.Series(model.feature_importances_, index=X.columns)
    plt.figure(figsize=(8, 5))
    importances.sort_values().plot(kind='barh', color='#0ea5e9')
    plt.title('Exploratory Feature Importances – PNFC Net Rate of Return', fontsize=13, fontweight='bold')
    plt.xlabel('Relative Importance (Random Forest)', fontsize=11)
    plt.tight_layout()
    plt.savefig('figures/chart8_rf_feature_importance.png', dpi=300)
    plt.close()

print("All charts successfully generated in figures/ directory!")
