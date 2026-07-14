import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np
import pickle

# Load rental dataset
df = pd.read_csv("dataset/rental_properties.csv")

# Remove unnecessary columns (keep new features)
df = df.drop(columns=[
    "property_id",
    "listing_type",
    "land_size_acres"
])

# Create encoder
encoders = {}

# Encode text columns
text_columns = [
    "property_type",
    "neighborhood",
    "town",
    "condition",
    "furnishing",
    "location_tier"
]

for column in text_columns:
    encoder = LabelEncoder()
    df[column] = encoder.fit_transform(df[column].astype(str))
    encoders[column] = encoder

# Ensure all numeric columns are float/int
numeric_columns = [
    "bedrooms", "bathrooms", "parking_spaces", "floor_size_sqm",
    "year_built", "floor_number", "distance_to_cbd_km",
    "has_swimming_pool", "has_gym", "has_borehole", "has_backup_generator",
    "has_security", "has_garden", "is_gated_community",
    "distance_to_school_km", "distance_to_hospital_km", "crime_index", "road_quality"
]

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Features (inputs)
X = df.drop("price_ksh", axis=1)

# Target (output)
y = df["price_ksh"]

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train model
model = RandomForestRegressor(
    n_estimators=200,
    max_depth=20,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

print("Model trained successfully!")

# Predictions
predictions = model.predict(X_test)

print("\nFirst 5 Predictions:")
print(predictions[:5])

# Evaluation
mae = mean_absolute_error(y_test, predictions)
rmse = np.sqrt(mean_squared_error(y_test, predictions))
r2 = r2_score(y_test, predictions)

print("\nModel Evaluation")
print(f"MAE: {mae:,.2f} KSh")
print(f"RMSE: {rmse:,.2f} KSh")
print(f"R²: {r2:.4f}")

# Feature importance
feature_importance = pd.DataFrame({
    "Feature": X.columns,
    "Importance": model.feature_importances_
}).sort_values(by="Importance", ascending=False)

print("\nTop 10 Feature Importances:")
print(feature_importance.head(10))

# Save model and encoders
with open("models/rental_model.pkl", "wb") as file:
    pickle.dump(model, file)

print("\nRental model saved successfully!")

with open("models/rental_encoders.pkl", "wb") as file:
    pickle.dump(encoders, file)

print("Rental encoders saved successfully!")

# Save feature names for inference
with open("models/rental_features.pkl", "wb") as file:
    pickle.dump(list(X.columns), file)

print("Feature names saved successfully!")