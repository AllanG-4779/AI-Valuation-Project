import pickle
import pandas as pd
import numpy as np

# Load the trained model (SALE)
with open("models/sale_model.pkl", "rb") as file:
    model = pickle.load(file)

# Load encoders
with open("models/sale_encoders.pkl", "rb") as file:
    encoders = pickle.load(file)

# Load feature names
try:
    with open("models/sale_features.pkl", "rb") as file:
        feature_names = pickle.load(file)
except FileNotFoundError:
    feature_names = model.feature_names_in_

# Sample property data for prediction (SALE)
sample = {
    "property_type": "Apartment",
    "neighborhood": "Westlands",
    "town": "Nairobi",
    "bedrooms": 3,
    "bathrooms": 2,
    "parking_spaces": 2,
    "floor_size_sqm": 150,
    "year_built": 2020,
    "floor_number": 5,
    "condition": "Excellent",
    "furnishing": "Furnished",
    "has_swimming_pool": 1,
    "has_gym": 1,
    "has_borehole": 1,
    "has_backup_generator": 1,
    "has_security": 1,
    "has_garden": 0,
    "is_gated_community": 1,
    "distance_to_cbd_km": 5.0,
    "location_tier": "premium",
    # NEW FEATURES
    "distance_to_school_km": 0.3,
    "distance_to_hospital_km": 0.6,
    "crime_index": 2.8,
    "road_quality": 5
}

def safe_transform(encoder, value):
    try:
        return encoder.transform([value])[0]
    except ValueError:
        print(f"Warning: Category '{value}' not seen in training. Using default encoding.")
        return 0

# Encode the sample
sample["property_type"] = safe_transform(encoders["property_type"], sample["property_type"])
sample["neighborhood"] = safe_transform(encoders["neighborhood"], sample["neighborhood"])
sample["town"] = safe_transform(encoders["town"], sample["town"])
sample["condition"] = safe_transform(encoders["condition"], sample["condition"])
sample["furnishing"] = safe_transform(encoders["furnishing"], sample["furnishing"])
sample["location_tier"] = safe_transform(encoders["location_tier"], sample["location_tier"])

# Create DataFrame
sample_df = pd.DataFrame([sample])

# Ensure all features
for feature in feature_names:
    if feature not in sample_df.columns:
        sample_df[feature] = 0

sample_df = sample_df[feature_names].fillna(0)

# Predict
prediction = model.predict(sample_df)

print("\n" + "="*50)
print("PROPERTY SALE PRICE PREDICTION")
print("="*50)
print(f"Property Type: {list(encoders['property_type'].classes_)[sample['property_type']]}")
print(f"Neighborhood: {list(encoders['neighborhood'].classes_)[sample['neighborhood']]}")
print(f"Bedrooms: {sample['bedrooms']}")
print(f"Floor Size: {sample['floor_size_sqm']} sqm")
print("-"*50)
print(f"Predicted Sale Price:")
print(f"KES {prediction[0]:,.0f}")
print(f"≈ USD {prediction[0]/150:,.0f} (approx)")
print("="*50)