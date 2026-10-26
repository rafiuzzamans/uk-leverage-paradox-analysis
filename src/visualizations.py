"""
Visualizations Module
=====================
Plotting routines for economic and financial indicators using Seaborn and Matplotlib.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd


def plot_profitability_trend(df_profit_long: pd.DataFrame, output_path: str = None):
    """Chart 1: Net Rate of Return by Sector (Quarterly, 2010-2024)."""
    plt.figure(figsize=(11, 5))
    df_filtered = df_profit_long[df_profit_long['Date'].dt.year >= 2010]
    sns.lineplot(data=df_filtered, x='Date', y='NetRateReturn', hue='Sector', linewidth=2)
    plt.title('Net Rate of Return by Sector (Quarterly, 2010-2024)', fontsize=13, fontweight='bold')
    plt.xlabel('Date', fontsize=11)
    plt.ylabel('Net Rate of Return (%)', fontsize=11)
    plt.legend(title='Sector', loc='upper left')
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300)
    return plt.gca()


def plot_asset_vs_profitability(df_corr: pd.DataFrame, output_path: str = None):
    """Chart 2: Liabilities Relative to Non-Financial Assets vs Rate of Return (Annual, 1997-2023)."""
    plt.figure(figsize=(9, 6))
    sns.regplot(data=df_corr, x='LiabilityRatio', y='NetRateReturn',
                scatter_kws={'alpha': 0.75, 'color': '#3b82f6', 's': 60},
                line_kws={'color': '#ef4444', 'linewidth': 2})
    plt.title('Liabilities Relative to Non-Financial Assets vs Rate of Return (1997-2023)', fontsize=13, fontweight='bold')
    plt.xlabel('Financial Liabilities ÷ Non-Financial Assets (%)', fontsize=11)
    plt.ylabel('Net Rate of Return (Annual Avg, %)', fontsize=11)
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300)
    return plt.gca()


def plot_correlation_matrix(corr_matrix: pd.DataFrame, output_path: str = None):
    """Chart 3: Correlation Matrix – Key NFC Variables vs Profitability."""
    plt.figure(figsize=(7, 5))
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap='coolwarm', vmin=-1, vmax=1,
                cbar_kws={'label': 'Correlation Coefficient'})
    plt.title('Correlation Matrix – Key NFC Variables vs Profitability', fontsize=13, fontweight='bold')
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300)
    return plt.gca()


def plot_sector_assets_stacked(df_pivot: pd.DataFrame, output_path: str = None):
    """Chart 4: Sector Contribution to Total Assets Over Time (2010-2023)."""
    fig, ax = plt.subplots(figsize=(11, 5))
    df_pivot.plot(kind='area', stacked=True, ax=ax, colormap='viridis', alpha=0.85)
    plt.title('Non-Financial Corporations Total Assets by Sector (2010-2023)', fontsize=13, fontweight='bold')
    plt.xlabel('Year', fontsize=11)
    plt.ylabel('Assets (£ million)', fontsize=11)
    plt.legend(loc='upper left', title='Sector')
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300)
    return ax


def plot_return_distribution_boxplot(df_profit_long: pd.DataFrame, year: int, output_path: str = None):
    """Chart 5: Distribution of Rate of Return by Sector."""
    plt.figure(figsize=(9, 5))
    df_c5 = df_profit_long[df_profit_long['Date'].dt.year == year]
    sns.boxplot(data=df_c5, x='Sector', y='NetRateReturn', palette='Set2')
    plt.title(f'Distribution of Net Rate of Return by PNFC Sector ({year})', fontsize=13, fontweight='bold')
    plt.xlabel('PNFC Sub-Sector', fontsize=11)
    plt.ylabel('Net Rate of Return (%)', fontsize=11)
    plt.xticks(rotation=15, ha='right')
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300)
    return plt.gca()


def plot_leverage_paradox(df_lw_nfc: pd.DataFrame, output_path: str = None):
    """Chart 6: Liabilities vs Net Worth Trend – The Leverage Paradox."""
    plt.figure(figsize=(11, 5))
    plt.plot(df_lw_nfc['Year'], df_lw_nfc['TotalLiabilities'], label='Total Financial Liabilities',
             marker='o', linewidth=2, color='#ef4444')
    plt.plot(df_lw_nfc['Year'], df_lw_nfc['Net worth'], label='Net Worth',
             marker='s', linewidth=2, color='#3b82f6')
    plt.title('Financial Liabilities vs Net Worth – The Leverage Paradox (2010-2023)', fontsize=13, fontweight='bold')
    plt.xlabel('Year', fontsize=11)
    plt.ylabel('Value (£ million)', fontsize=11)
    plt.legend(loc='upper left')
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300)
    return plt.gca()


def plot_investment_fallacy(df_merge_c7: pd.DataFrame, output_path: str = None):
    """Chart 7: Investment (GFCF) vs Next-Quarter Profitability."""
    plt.figure(figsize=(9, 6))
    sns.scatterplot(data=df_merge_c7, x='InvestmentAmount', y='NextQuarterReturn', hue='Sector', alpha=0.75, s=60)
    plt.xscale('log')
    plt.title('Investment (GFCF) vs Next-Quarter Rate of Return – The Investment Fallacy', fontsize=13, fontweight='bold')
    plt.xlabel('Non-Financial Corp GFCF (£ million, log scale)', fontsize=11)
    plt.ylabel('Next Quarter Net Rate of Return (%)', fontsize=11)
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300)
    return plt.gca()
