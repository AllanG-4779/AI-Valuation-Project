import pandas as pd


def prepare_sale_input(data, encoders):

    for column in [

        "property_type",
        "neighborhood",
        "town",
        "condition",
        "furnishing",
        "location_tier"

    ]:

        data[column] = encoders[column].transform(
            [data[column]]
        )[0]

    return pd.DataFrame([data])


def prepare_rental_input(data, encoders):

    for column in [

        "property_type",
        "neighborhood",
        "town",
        "condition",
        "furnishing",
        "location_tier"

    ]:

        data[column] = encoders[column].transform(
            [data[column]]
        )[0]

    return pd.DataFrame([data])