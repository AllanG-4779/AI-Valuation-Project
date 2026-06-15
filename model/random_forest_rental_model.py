import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor

# Load rental dataset
df = pd.read_csv("dataset/rental_properties.csv")

# Remove unnecessary columns
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
    df[column] = encoder.fit_transform(df[column])

    encoders[column] = encoder

# Features (inputs)
X = df.drop("price_ksh", axis=1)

# Target (output)
y = df["price_ksh"]


from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

model = RandomForestRegressor(n_estimators=200, random_state=42)

model.fit(X_train, y_train)

print("Model trained successfully!")

predictions = model.predict(X_test)

print("\nFirst 5 Predictions:")
print(predictions[:5])

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

import numpy as np

mae = mean_absolute_error(y_test, predictions)

rmse = np.sqrt(
    mean_squared_error(y_test, predictions)
)

r2 = r2_score(y_test, predictions)

print("\nModel Evaluation")
print("MAE:", mae)
print("RMSE:", rmse)
print("R²:", r2)

feature_importance = pd.DataFrame({
    "Feature": X.columns,
    "Importance": model.feature_importances_
})

feature_importance = feature_importance.sort_values(
    by="Importance",
    ascending=False
)

print(feature_importance)

import pickle

with open("models/rental_model.pkl", "wb") as file:
    pickle.dump(model, file)

print("Rental model saved successfully!")

with open("models/rental_encoders.pkl", "wb") as file:
    pickle.dump(encoders, file)

print("Encoders saved successfully!")