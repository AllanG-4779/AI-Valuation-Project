import pandas as pd

df = pd.read_csv("dataset/rental_properties.csv")

print(df["price_ksh"].describe())

print("\nAffordable Properties")
print(
    df[df["location_tier"] == "affordable"]["price_ksh"].describe()
)

print("\nMid Properties")
print(
    df[df["location_tier"] == "mid"]["price_ksh"].describe()
)

print("\nPremium Properties")
print(
    df[df["location_tier"] == "premium"]["price_ksh"].describe()
)