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

def load_ons_quarterly_data_excel(filepath, sheet_name):
    df_raw = pd.read_excel(filepath, sheet_name=sheet_name, header=3)
    df_raw.rename(columns={df_raw.columns[0]: 'Time'}, inplace=True)
    df = df_raw.iloc[1:].copy()
    def quarter_to_date(q_str):
        if not isinstance(q_str, str): return np.nan
        parts = q_str.split(' ')
        if len(parts) == 2:
            year, q = parts
            q_map = {'Q1': '-03-31', 'Q2': '-06-30', 'Q3': '-09-30', 'Q4': '-12-31'}
            return f"{year}{q_map.get(q, '-01-01')}"
        return np.nan
    df['Date'] = df['Time'].apply(lambda x: pd.to_datetime(quarter_to_date(x), errors='coerce'))
    cols_to_convert = df.columns[1:-1]
    for col in cols_to_convert:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def load_ons_annual_data_excel(filepath, sheet_name, sector_col_name):
    df_raw = pd.read_excel(filepath, sheet_name=sheet_name, header=1)
    def clean_col_name(col):
        if col.strip() == 'Non-financial assets': return 'Total Assets'
        if col.strip() == 'Financial assets and liabilities': return 'Financial liabilities Total'
        if col.strip() == 'Total': return 'Net worth'
        if 'AN.11' in col: return 'AN.11 Fixed assets Total'
        if 'AN.21' in col: return 'AN.21 Natural resources Total'
        if 'Inventories' in col: return 'Inventories'
        return col.split('£million at end year)')[0].strip() if '£million at end year)' in col else col.strip()

    df_raw.columns = [clean_col_name(col) for col in df_raw.columns]
    df_raw.rename(columns={df_raw.columns[0]: 'Year'}, inplace=True)
    df = df_raw[pd.to_numeric(df_raw['Year'], errors='coerce').notna()].copy()
    df['Year'] = df['Year'].astype(int)
    expected_numeric_cols = ['Total Assets', 'Financial liabilities Total', 'Net worth']
    for col in expected_numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'Financial liabilities Total' in df.columns:
        df['TotalLiabilities'] = df['Financial liabilities Total']
    else:
        df['TotalLiabilities'] = np.nan

    if 'Total Assets' in df.columns:
        df['TotalAssets'] = df['Total Assets']
    else:
        df['TotalAssets'] = np.nan

    df['Sector'] = sector_col_name
    return df[['Year', 'Sector', 'TotalAssets', 'TotalLiabilities', 'Net worth']].dropna(subset=['TotalAssets', 'TotalLiabilities'])

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
df_nfc_assets = df_nfc[['Year', 'TotalAssets']].rename(columns={'TotalAssets': 'Non-Financial Corp Assets'})
df_pc_assets = df_pc[['Year', 'TotalAssets']].rename(columns={'TotalAssets': 'Public Corp Assets'})
df_assets_total = pd.merge(df_nfc_assets, df_pc_assets, on='Year', how='inner')
df_assets_total['Private Non-Financial Corp Assets'] = df_pnfc['TotalAssets']
df_pivot = df_assets_total[['Year', 'Private Non-Financial Corp Assets', 'Public Corp Assets']].set_index('Year').tail(15)

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

# 2. Chart 2
plt.figure(figsize=(9, 6))
plt.scatter(merged_c2['TotalAssets'], merged_c2['NetRateReturn'],
            s=merged_c2['TotalLiabilities']/merged_c2['TotalAssets'] * 1200,
            alpha=0.7, edgecolors='navy', linewidth=1, c='#3b82f6')
for i, sector in enumerate(merged_c2['Sector_PR']):
    plt.annotate(sector, (merged_c2['TotalAssets'].iat[i], merged_c2['NetRateReturn'].iat[i]),
                 textcoords="offset points", xytext=(8, -4), ha='left', fontweight='semibold')
plt.xscale('log')
plt.title(f'Assets vs Rate of Return by PNFC Sector (Latest Annual Avg – {latest_year})', fontsize=13, fontweight='bold')
plt.xlabel('Total Non-Financial Assets (£ million, log scale)', fontsize=11)
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
fig, ax = plt.subplots(figsize=(11, 5))
df_pivot.plot(kind='area', stacked=True, ax=ax, colormap='viridis', alpha=0.85)
plt.title('Non-Financial Corporations Total Assets by Sector (2010-2023)', fontsize=13, fontweight='bold')
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

# 8. Chart 8
df_model = df_corr.dropna().copy()
df_pnfc_sector_annual = df_profit_annual[df_profit_annual['Sector'] != 'All Private Non-Financial Corporations'].copy()
df_pnfc_sector_annual = df_pnfc_sector_annual.pivot(index='Year', columns='Sector', values='NetRateReturn')
df_pnfc_sector_annual = df_pnfc_sector_annual.apply(lambda x: x.fillna(x.mean()), axis=0)
df_model = df_model.merge(df_pnfc_sector_annual, on='Year', how='inner')
df_model.rename(columns={
    'Manufacturing Private Non-Financial Corporations': 'NetReturn_Manufacturing',
    'Service Private Non-Financial Corporations': 'NetReturn_Service',
    'UK Continental Shelf': 'NetReturn_UKCS',
    'UK Non-Continental Shelf Private Non-Financial Corporations': 'NetReturn_NonUKCS'
}, inplace=True)

y = df_model['NetRateReturn']
features = ['AssetGrowthRate', 'LiabilityRatio', 'InvestmentAmount', 'NetReturn_Manufacturing', 'NetReturn_Service']
X = df_model[[c for c in features if c in df_model.columns]].dropna()
y = y.loc[X.index]

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
