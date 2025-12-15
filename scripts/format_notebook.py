import json

cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# The UK's Leverage Paradox\n",
            "## Unmasking Sectoral Fragility to Inform Private Non-Financial Corporation Strategy\n",
            "\n",
            "**Author**: Rafi Uz Zaman Siddiqui  \n",
            "\n",
            "---\n",
            "\n",
            "### Overview & Research Goal\n",
            "Private Non-Financial Corporations (PNFCs) are the economic engine of the UK. This project investigates over a decade of official **Office for National Statistics (ONS)** data to uncover the structural divergence between sectors, examine corporate leverage vs net worth, and test the relationship between capital investment and profitability."
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 1. Library Imports & Configuration"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import pandas as pd\n",
            "import matplotlib.pyplot as plt\n",
            "import seaborn as sns\n",
            "import numpy as np\n",
            "from sklearn.ensemble import RandomForestRegressor\n",
            "from sklearn.preprocessing import LabelEncoder\n",
            "import warnings\n",
            "warnings.filterwarnings('ignore')\n",
            "\n",
            "plt.style.use('seaborn-v0_8-whitegrid')\n",
            "plt.rcParams['font.size'] = 10\n",
            "plt.rcParams['axes.titlesize'] = 13\n",
            "plt.rcParams['axes.titleweight'] = 'bold'"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 2. ONS Data Ingestion & Preprocessing Utilities\n",
            "Functions to parse quarterly and annual ONS reference tables from Excel spreadsheets."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "FILE_PROFITABILITY_EXCEL = '2024q2referencetables.xlsx'  # Sheet: Table 2\n",
            "FILE_INVESTMENT_EXCEL = 'ukea2023q2table2corpssectorv2.xlsx'  # Sheet: 3.1.7_B\n",
            "FILE_BALANCE_EXCEL = 'nbsreferencetables2024.xlsx'  # Sheets: Table 3, Table 5, Table 4\n",
            "\n",
            "def load_ons_quarterly_data_excel(filepath, sheet_name):\n",
            "    df_raw = pd.read_excel(filepath, sheet_name=sheet_name, header=3)\n",
            "    df_raw.rename(columns={df_raw.columns[0]: 'Time'}, inplace=True)\n",
            "    df = df_raw.iloc[1:].copy()\n",
            "\n",
            "    def quarter_to_date(q_str):\n",
            "        if not isinstance(q_str, str):\n",
            "            return np.nan\n",
            "        parts = q_str.split(' ')\n",
            "        if len(parts) == 2:\n",
            "            year, q = parts\n",
            "            q_map = {'Q1': '-03-31', 'Q2': '-06-30', 'Q3': '-09-30', 'Q4': '-12-31'}\n",
            "            return f\"{year}{q_map.get(q, '-01-01')}\"\n",
            "        return np.nan\n",
            "\n",
            "    df['Date'] = df['Time'].apply(lambda x: pd.to_datetime(quarter_to_date(x), errors='coerce'))\n",
            "    for col in df.columns[1:-1]:\n",
            "        df[col] = pd.to_numeric(df[col], errors='coerce')\n",
            "    return df\n",
            "\n",
            "def load_ons_annual_data_excel(filepath, sheet_name, sector_col_name):\n",
            "    df_raw = pd.read_excel(filepath, sheet_name=sheet_name, header=1)\n",
            "    def clean_col_name(col):\n",
            "        c = col.strip()\n",
            "        if c == 'Non-financial assets': return 'Total Assets'\n",
            "        if c == 'Financial assets and liabilities': return 'Financial liabilities Total'\n",
            "        if c == 'Total': return 'Net worth'\n",
            "        if 'AN.11' in col: return 'AN.11 Fixed assets Total'\n",
            "        if 'AN.21' in col: return 'AN.21 Natural resources Total'\n",
            "        if 'Inventories' in col: return 'Inventories'\n",
            "        return col.split('£million at end year)')[0].strip() if '£million at end year)' in col else c\n",
            "\n",
            "    df_raw.columns = [clean_col_name(col) for col in df_raw.columns]\n",
            "    df_raw.rename(columns={df_raw.columns[0]: 'Year'}, inplace=True)\n",
            "    df = df_raw[pd.to_numeric(df_raw['Year'], errors='coerce').notna()].copy()\n",
            "    df['Year'] = df['Year'].astype(int)\n",
            "\n",
            "    for col in ['Total Assets', 'Financial liabilities Total', 'Net worth']:\n",
            "        if col in df.columns:\n",
            "            df[col] = pd.to_numeric(df[col], errors='coerce')\n",
            "\n",
            "    df['TotalLiabilities'] = df['Financial liabilities Total'] if 'Financial liabilities Total' in df.columns else np.nan\n",
            "    df['TotalAssets'] = df['Total Assets'] if 'Total Assets' in df.columns else np.nan\n",
            "    df['Sector'] = sector_col_name\n",
            "    return df[['Year', 'Sector', 'TotalAssets', 'TotalLiabilities', 'Net worth']].dropna(subset=['TotalAssets', 'TotalLiabilities'])"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 3. Load Datasets & Reshape for Analysis"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Load Profitability Data\n",
            "df_profit = load_ons_quarterly_data_excel(FILE_PROFITABILITY_EXCEL, sheet_name='Table 2')\n",
            "id_vars = ['Time', 'Date']\n",
            "value_vars_net = [\n",
            "    'UK Continental Shelf companies % [note 2] Net [note 4] [note 5]',\n",
            "    'UK Non-Continental Shelf Private Non-Financial Corporations % - Net [note 4] [note 5]',\n",
            "    'Manufacturing sector Private Non-Financial Corporations % - Net [note 4] [note 5]',\n",
            "    'Service sector Private Non-Financial Corporations % - Net [note 4] [note 5]'\n",
            "]\n",
            "df_profit_long = df_profit.melt(id_vars=id_vars, value_vars=value_vars_net, var_name='SectorFull', value_name='NetRateReturn')\n",
            "df_profit_long['Sector'] = df_profit_long['SectorFull'].str.split('%').str[0].str.split(' - ').str[-1].str.replace(' sector', '').str.replace(' companies', '').str.strip()\n",
            "df_profit_long = df_profit_long.dropna(subset=['NetRateReturn']).sort_values('Date')\n",
            "\n",
            "# Load Balance Sheet Data\n",
            "df_pnfc = load_ons_annual_data_excel(FILE_BALANCE_EXCEL, sheet_name='Table 5', sector_col_name='Private Non-Financial')\n",
            "df_nfc = load_ons_annual_data_excel(FILE_BALANCE_EXCEL, sheet_name='Table 3', sector_col_name='Non-Financial')\n",
            "df_pc = load_ons_annual_data_excel(FILE_BALANCE_EXCEL, sheet_name='Table 4', sector_col_name='Public Non-Financial')\n",
            "\n",
            "# Load Gross Fixed Capital Formation (GFCF / Investment)\n",
            "df_invest_raw = load_ons_quarterly_data_excel(FILE_INVESTMENT_EXCEL, sheet_name='3.1.7_B')\n",
            "df_invest = df_invest_raw[['Date', 'Gross fixed capital formation']].copy()\n",
            "df_invest.rename(columns={'Gross fixed capital formation': 'InvestmentAmount'}, inplace=True)\n",
            "df_invest = df_invest.dropna(subset=['InvestmentAmount'])\n",
            "\n",
            "print('Data Ingestion complete.')"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 4. Chart 1: Profitability Trend by Sector (2010–2024)\n",
            "Longitudinal comparison showing the divergence between the stable Service sector and the volatile UK Continental Shelf."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "plt.figure(figsize=(12, 6))\n",
            "df_c1 = df_profit_long[df_profit_long['Date'].dt.year >= 2010]\n",
            "sns.lineplot(data=df_c1, x='Date', y='NetRateReturn', hue='Sector', linewidth=2)\n",
            "plt.title('Net Rate of Return by Sector (Quarterly, 2010-2024)', fontsize=14)\n",
            "plt.xlabel('Date', fontsize=12)\n",
            "plt.ylabel('Net Rate of Return (%)', fontsize=12)\n",
            "plt.legend(title='Sector', loc='upper left')\n",
            "plt.grid(True, linestyle='--', alpha=0.7)\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 5. Chart 2: Asset Base vs Profitability (Latest Year)\n",
            "Scatter bubble chart of Total Non-Financial Assets (£m) vs Net Rate of Return (%), with bubble size reflecting the debt/asset liability ratio."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "latest_year = df_pnfc['Year'].max()\n",
            "df_profit_annual = df_profit_long.groupby(['Sector', df_profit_long['Date'].dt.year])['NetRateReturn'].mean().reset_index()\n",
            "df_profit_annual.rename(columns={'Date': 'Year'}, inplace=True)\n",
            "\n",
            "merged_c2 = pd.merge(df_pnfc[df_pnfc['Year'] == latest_year],\n",
            "                     df_profit_annual[df_profit_annual['Year'] == latest_year],\n",
            "                     on='Year', how='inner', suffixes=('_BS', '_PR'))\n",
            "\n",
            "plt.figure(figsize=(10, 7))\n",
            "plt.scatter(merged_c2['TotalAssets'], merged_c2['NetRateReturn'],\n",
            "            s=merged_c2['TotalLiabilities']/merged_c2['TotalAssets'] * 1200,\n",
            "            alpha=0.7, edgecolors='navy', linewidth=1, c='#3b82f6')\n",
            "\n",
            "for i, sector in enumerate(merged_c2['Sector_PR']):\n",
            "    plt.annotate(sector, (merged_c2['TotalAssets'].iat[i], merged_c2['NetRateReturn'].iat[i]),\n",
            "                 textcoords=\"offset points\", xytext=(8,-4), ha='left', fontweight='semibold')\n",
            "\n",
            "plt.xscale('log')\n",
            "plt.title(f'Assets vs Rate of Return by PNFC Sector (Annual Avg – {latest_year})', fontsize=14)\n",
            "plt.xlabel('Total Non-Financial Assets (£ million, log scale)', fontsize=12)\n",
            "plt.ylabel('Net Rate of Return (Annual Avg, %)', fontsize=12)\n",
            "plt.grid(True, linestyle='--', alpha=0.7)\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 6. Chart 3: Correlation Matrix – Key NFC Variables vs Profitability"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "df_corr_base = df_nfc.copy()\n",
            "df_corr_base.rename(columns={'TotalAssets': 'TotalAssets_NFC', 'TotalLiabilities': 'TotalLiabilities_NFC'}, inplace=True)\n",
            "df_corr_base = df_corr_base.set_index('Year')\n",
            "df_corr_base['AssetGrowthRate'] = df_corr_base['TotalAssets_NFC'].pct_change() * 100\n",
            "df_corr_base['LiabilityRatio'] = df_corr_base['TotalLiabilities_NFC'] / df_corr_base['TotalAssets_NFC'] * 100\n",
            "\n",
            "df_invest_annual = df_invest.groupby(df_invest['Date'].dt.year)['InvestmentAmount'].sum().reset_index()\n",
            "df_invest_annual.rename(columns={'Date': 'Year'}, inplace=True)\n",
            "df_invest_annual = df_invest_annual.set_index('Year')\n",
            "\n",
            "df_nfc_annual_profit = load_ons_quarterly_data_excel(FILE_PROFITABILITY_EXCEL, sheet_name='Table 2')\n",
            "df_nfc_annual_profit = df_nfc_annual_profit[['Date', 'All Private Non-Financial Corporations % [note 1]: Net [note 4] [note 5]']].copy()\n",
            "df_nfc_annual_profit['Year'] = df_nfc_annual_profit['Date'].dt.year\n",
            "df_nfc_annual_profit.rename(columns={'All Private Non-Financial Corporations % [note 1]: Net [note 4] [note 5]': 'NetRateReturn'}, inplace=True)\n",
            "df_nfc_annual_profit = df_nfc_annual_profit.groupby('Year')['NetRateReturn'].mean().reset_index().set_index('Year').dropna()\n",
            "\n",
            "df_corr = pd.concat([df_corr_base, df_invest_annual, df_nfc_annual_profit], axis=1).dropna()\n",
            "vars_for_corr = ['AssetGrowthRate', 'LiabilityRatio', 'InvestmentAmount', 'NetRateReturn']\n",
            "corr = df_corr[vars_for_corr].corr()\n",
            "\n",
            "plt.figure(figsize=(7, 5))\n",
            "sns.heatmap(corr, annot=True, fmt=\".2f\", cmap='coolwarm', vmin=-1, vmax=1, cbar_kws={'label': 'Correlation Coefficient'})\n",
            "plt.title('Correlation Matrix – Key NFC Variables vs Profitability', fontsize=14)\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 7. Chart 4: Sector Contribution to Total Assets Over Time (2010–2023)\n",
            "Stacked area chart confirming private corporations are the primary driver of capital expansion."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "df_nfc_assets = df_nfc[['Year', 'TotalAssets']].rename(columns={'TotalAssets': 'Non-Financial Corp Assets'})\n",
            "df_pc_assets = df_pc[['Year', 'TotalAssets']].rename(columns={'TotalAssets': 'Public Corp Assets'})\n",
            "df_assets_total = pd.merge(df_nfc_assets, df_pc_assets, on='Year', how='inner')\n",
            "df_assets_total['Private Non-Financial Corp Assets'] = df_pnfc['TotalAssets']\n",
            "df_pivot = df_assets_total[['Year', 'Private Non-Financial Corp Assets', 'Public Corp Assets']].set_index('Year').tail(15)\n",
            "\n",
            "fig, ax = plt.subplots(figsize=(11, 5))\n",
            "df_pivot.plot(kind='area', stacked=True, ax=ax, colormap='viridis', alpha=0.85)\n",
            "plt.title('Non-Financial Corporations Total Assets by Sector (2010-2023)', fontsize=14)\n",
            "plt.xlabel('Year', fontsize=12)\n",
            "plt.ylabel('Assets (£ million)', fontsize=12)\n",
            "plt.legend(loc='upper left', title='Sector')\n",
            "plt.grid(axis='y', linestyle='--', alpha=0.7)\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 8. Chart 5: Distribution of Rate of Return by Sector (Variance & Risk)\n",
            "Boxplot illustrating quarterly spread and predictability across sub-sectors."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "plt.figure(figsize=(10, 5))\n",
            "df_c5 = df_profit_long[df_profit_long['Date'].dt.year == latest_year]\n",
            "sns.boxplot(data=df_c5, x='Sector', y='NetRateReturn', palette='Set2')\n",
            "plt.title(f'Distribution of Net Rate of Return by PNFC Sector (Quarterly – {latest_year})', fontsize=14)\n",
            "plt.xlabel('PNFC Sub-Sector', fontsize=12)\n",
            "plt.ylabel('Net Rate of Return (%)', fontsize=12)\n",
            "plt.xticks(rotation=15, ha='right')\n",
            "plt.grid(axis='y', linestyle='--', alpha=0.7)\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 9. Chart 6: Liabilities vs Net Worth Trend (The Leverage Paradox)\n",
            "Persistent divergence showing rising liabilities alongside negative aggregate net worth."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "df_lw_nfc = df_nfc[(df_nfc['Year'] >= 2010)].copy()\n",
            "\n",
            "plt.figure(figsize=(11, 5))\n",
            "plt.plot(df_lw_nfc['Year'], df_lw_nfc['TotalLiabilities'], label='Total Financial Liabilities', marker='o', linewidth=2, color='#ef4444')\n",
            "plt.plot(df_lw_nfc['Year'], df_lw_nfc['Net worth'], label='Net Worth', marker='s', linewidth=2, color='#3b82f6')\n",
            "plt.title('Financial Liabilities vs Net Worth – The Leverage Paradox (2010-2023)', fontsize=14)\n",
            "plt.xlabel('Year', fontsize=12)\n",
            "plt.ylabel('Value (£ million)', fontsize=12)\n",
            "plt.legend(loc='upper left')\n",
            "plt.grid(True, linestyle='--', alpha=0.7)\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 10. Chart 7: Investment (GFCF) vs Next-Quarter Profitability (The Investment Fallacy)\n",
            "Testing whether higher capital expenditure produces immediate returns."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "df_econ_profit = df_profit_long[['Date', 'Sector', 'NetRateReturn']].copy()\n",
            "df_econ_profit['NextQuarterReturn'] = df_econ_profit.groupby('Sector')['NetRateReturn'].shift(-1)\n",
            "df_merge_c7 = pd.merge(df_econ_profit, df_invest[['Date', 'InvestmentAmount']], on='Date', how='left')\n",
            "df_merge_c7 = df_merge_c7.dropna(subset=['NextQuarterReturn', 'InvestmentAmount'])\n",
            "\n",
            "plt.figure(figsize=(9, 6))\n",
            "sns.scatterplot(data=df_merge_c7, x='InvestmentAmount', y='NextQuarterReturn', hue='Sector', alpha=0.75, s=60)\n",
            "plt.xscale('log')\n",
            "plt.title('Investment (GFCF) vs Next-Quarter Rate of Return – The Investment Fallacy', fontsize=14)\n",
            "plt.xlabel('Non-Financial Corp GFCF (£ million, log scale)', fontsize=12)\n",
            "plt.ylabel('Next Quarter Net Rate of Return (%)', fontsize=12)\n",
            "plt.grid(True, linestyle='--', alpha=0.7)\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 11. Chart 8: Machine Learning – Drivers of PNFC Profitability (Random Forest)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "df_model = df_corr.dropna().copy()\n",
            "df_pnfc_sector_annual = df_profit_annual[df_profit_annual['Sector'] != 'All Private Non-Financial Corporations'].copy()\n",
            "df_pnfc_sector_annual = df_pnfc_sector_annual.pivot(index='Year', columns='Sector', values='NetRateReturn')\n",
            "df_pnfc_sector_annual = df_pnfc_sector_annual.apply(lambda x: x.fillna(x.mean()), axis=0)\n",
            "df_model = df_model.merge(df_pnfc_sector_annual, on='Year', how='inner')\n",
            "df_model.rename(columns={\n",
            "    'Manufacturing Private Non-Financial Corporations': 'NetReturn_Manufacturing',\n",
            "    'Service Private Non-Financial Corporations': 'NetReturn_Service',\n",
            "    'UK Continental Shelf': 'NetReturn_UKCS',\n",
            "    'UK Non-Continental Shelf Private Non-Financial Corporations': 'NetReturn_NonUKCS'\n",
            "}, inplace=True)\n",
            "\n",
            "y = df_model['NetRateReturn']\n",
            "features = ['AssetGrowthRate', 'LiabilityRatio', 'InvestmentAmount', 'NetReturn_Manufacturing', 'NetReturn_Service']\n",
            "X = df_model[[c for c in features if c in df_model.columns]].dropna()\n",
            "y = y.loc[X.index]\n",
            "\n",
            "if len(X) >= 5:\n",
            "    model = RandomForestRegressor(n_estimators=100, random_state=42)\n",
            "    model.fit(X, y)\n",
            "    importances = pd.Series(model.feature_importances_, index=X.columns)\n",
            "\n",
            "    plt.figure(figsize=(8, 5))\n",
            "    importances.sort_values().plot(kind='barh', color='#0ea5e9')\n",
            "    plt.title('Feature Importances – Drivers of PNFC Net Rate of Return', fontsize=14)\n",
            "    plt.xlabel('Relative Importance (Random Forest)', fontsize=12)\n",
            "    plt.grid(axis='x', linestyle='--', alpha=0.7)\n",
            "    plt.tight_layout()\n",
            "    plt.show()\n",
            "else:\n",
            "    print('Insufficient data points for Random Forest fitting.')"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 12. Conclusion & Summary\n",
            "- **The UK PNFC sector operates under a 'High Leverage, High Service Dependence' model**.\n",
            "- **Service stability** cushions macro-economic shocks.\n",
            "- **Continental Shelf volatility** demands risk hedging.\n",
            "- **Capital spending alone is insufficient**; monitoring debt ratios and operational agility is essential for corporate survival."
        ]
    }
]

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbformat": 4,
            "nbformat_minor": 2
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}

with open('Financial_Analysis_Charts.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=2)

print('Formatted Financial_Analysis_Charts.ipynb created successfully!')
