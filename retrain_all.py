"""
retrain_all.py

Retrains both the sale and rental Random Forest models using the enriched
dataset that now includes neighborhood-level factors:
  - distance_to_school_km
  - distance_to_hospital_km
  - crime_index
  - road_quality  (categorical → label encoded)

Run this once after replacing your dataset file with the enriched version.
The script saves new model and encoder pkl files, overwriting the old ones.

Usage:
    python retrain_all.py
"""

import pandas as pd
import numpy as np
import pickle
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ── Configuration ────────────────────────────────────────────────────────────

DATASET_PATH = "dataset/kenya_properties.csv"

COLUMNS_TO_DROP = [
    "property_id",
    "listing_type",      # used for splitting, not a model feature
    "land_size_acres",   # mostly NaN
]

TEXT_COLUMNS = [
    "property_type",
    "neighborhood",
    "town",
    "condition",
    "furnishing",
    "location_tier",
    "road_quality",      # new
]

TARGET = "price_ksh"


# ── Helper ───────────────────────────────────────────────────────────────────

def train_and_evaluate(df, label):
    df = df.copy().dropna(subset=[TARGET])

    drop_existing = [c for c in COLUMNS_TO_DROP if c in df.columns]
    df = df.drop(columns=drop_existing)

    encoders = {}
    for col in TEXT_COLUMNS:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le

    X = df.drop(columns=[TARGET])
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae  = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2   = r2_score(y_test, preds)

    print(f"\n── {label} model ──────────────────────────")
    print(f"  Training rows : {len(X_train)}")
    print(f"  Test rows     : {len(X_test)}")
    print(f"  MAE           : KES {mae:,.0f}")
    print(f"  RMSE          : KES {rmse:,.0f}")
    print(f"  R²            : {r2:.4f}")

    feat_imp = pd.DataFrame({
        "Feature": X.columns,
        "Importance": model.feature_importances_
    }).sort_values("Importance", ascending=False)
    print(f"\n  Top 10 features:")
    print(feat_imp.head(10).to_string(index=False))

    return model, encoders


# ── Main ─────────────────────────────────────────────────────────────────────

df = pd.read_csv(DATASET_PATH)

print(f"Loaded dataset: {df.shape[0]} rows, {df.shape[1]} columns")
print(f"New factor columns present: {[c for c in ['distance_to_school_km','distance_to_hospital_km','crime_index','road_quality'] if c in df.columns]}")

# Split by listing type
sale_df   = df[df["listing_type"] == "For Sale"].copy()
rental_df = df[df["listing_type"] == "For Rent"].copy()

print(f"\nSale rows  : {len(sale_df)}")
print(f"Rental rows: {len(rental_df)}")

# Train
sale_model,   sale_encoders   = train_and_evaluate(sale_df,   "Sale")
rental_model, rental_encoders = train_and_evaluate(rental_df, "Rental")

# Save
with open("models/sale_model.pkl",    "wb") as f: pickle.dump(sale_model,   f)
with open("models/sale_encoders.pkl", "wb") as f: pickle.dump(sale_encoders, f)
with open("models/rental_model.pkl",    "wb") as f: pickle.dump(rental_model,   f)
with open("models/rental_encoders.pkl", "wb") as f: pickle.dump(rental_encoders, f)

print("\n✓ All four pkl files saved to models/")
print("✓ Replace dataset/kenya_properties.csv with the enriched version")
print("✓ Restart Flask to load the new models")