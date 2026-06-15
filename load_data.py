import pandas as pd

df = pd.read_csv("dataset/kenya_properties.csv")

print(df)
print(df.head())
print(df.shape)
print(df.columns)
print(df.head(10))
print(df.describe())
print(df.info())
print(df.isnull().sum())
