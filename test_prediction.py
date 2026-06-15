import pickle
import pandas as pd

# Load the trained model
with open("models/rental_model.pkl", "rb") as file:
    model = pickle.load(file)

# Load encoders
with open("models/rental_encoders.pkl", "rb") as file:
    encoders = pickle.load(file)

# Sample property data for prediction
sample = {
    "property_type": "Apartment",
    "neighborhood": "Donholm",
    "town": "Nairobi",
    "bedrooms": 3,
    "bathrooms": 2,
    "parking_spaces": 1,
    "floor_size_sqm": 120,
    "year_built": 2018,
    "floor_number": 4,
    "condition": "Excellent",
    "furnishing": "Furnished",
    "has_swimming_pool": 1,
    "has_gym": 1,
    "has_borehole": 1,
    "has_backup_generator": 1,
    "has_security": 1,
    "has_garden": 0,
    "is_gated_community": 1,
    "distance_to_cbd_km": 8.0,
    "location_tier": "premium"
}

# Encode the sample using the same encoders
sample["property_type"] = encoders["property_type"].transform(
    [sample["property_type"]]
)[0]

sample["neighborhood"] = encoders["neighborhood"].transform(
    [sample["neighborhood"]]
)[0]

sample["town"] = encoders["town"].transform(
    [sample["town"]]
)[0]

sample["condition"] = encoders["condition"].transform(
    [sample["condition"]]
)[0]

sample["furnishing"] = encoders["furnishing"].transform(
    [sample["furnishing"]]
)[0]

sample["location_tier"] = encoders["location_tier"].transform(
    [sample["location_tier"]]
)[0]

#predicting the price
sample_df = pd.DataFrame([sample])

prediction = model.predict(sample_df)

print("\nPredicted Property Price:")
print(f"KES {prediction[0]:,.0f}")