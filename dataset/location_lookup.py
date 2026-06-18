import pandas as pd


df = pd.read_csv(
    "dataset/sale_properties.csv"
)


location_lookup = (
    df[
        [
            "neighborhood",
            "distance_to_cbd_km",
            "location_tier"
        ]
    ]
    .drop_duplicates()
)


print(location_lookup)