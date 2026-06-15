import pandas as pd

df = pd.read_csv("dataset/kenya_properties.csv")

print("Original Shape:")
print(df.shape)

# Keep only sale properties
sale_df = df[df["listing_type"] == "For Sale"]

print("\nAfter Keeping Sale Properties:")
print(sale_df.shape)

sale_df.to_csv("dataset/sale_properties.csv", index=False)

print("\nSale dataset saved!")

rent_df = df[df["listing_type"] == "For Rent"]

rent_df.to_csv("dataset/rental_properties.csv", index=False)

print("Rental dataset saved!")