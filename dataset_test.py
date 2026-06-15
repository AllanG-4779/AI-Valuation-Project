import pandas as pd

data = {
    "Location": ["Nairobi", "Nakuru", "Mombasa"],
    "Bedrooms": [3, 4, 2],
    "Price": [8500000, 6500000, 7200000]
}

df = pd.DataFrame(data)

print(df)