"""
Predictive Modeling Module
==========================
Random Forest regression pipeline to predict PNFC net profitability and extract
relative feature importances across macro and sectoral drivers.
"""

import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from typing import Tuple, Dict


def train_profitability_model(df_features: pd.DataFrame, target_col: str = 'NetRateReturn',
                              n_estimators: int = 100, random_state: int = 42) -> Tuple[RandomForestRegressor, pd.Series]:
    """
    Train a Random Forest Regressor to model PNFC profitability and determine
    feature importances.
    """
    feature_cols = [c for c in df_features.columns if c != target_col]
    X = df_features[feature_cols].dropna()
    y = df_features.loc[X.index, target_col]

    model = RandomForestRegressor(n_estimators=n_estimators, random_state=random_state)
    model.fit(X, y)

    importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=True)
    return model, importances


def plot_feature_importances(importances: pd.Series, output_path: str = None):
    """Plot horizontal bar chart of feature importances."""
    plt.figure(figsize=(8, 5))
    importances.plot(kind='barh', color='#0ea5e9')
    plt.title('Feature Importances – Drivers of PNFC Net Rate of Return', fontsize=13, fontweight='bold')
    plt.xlabel('Relative Importance (Random Forest)', fontsize=11)
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300)
    return plt.gca()
