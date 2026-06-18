import pandas as pd


def prepare_sale_input(data, encoders):


    text_columns = [

        "property_type",
        "neighborhood",
        "town",
        "condition",
        "furnishing",
        "location_tier"

    ]



    for column in text_columns:


        data[column] = encoders[column].transform(
            [data[column]]
        )[0]



    df = pd.DataFrame([data])


    return df