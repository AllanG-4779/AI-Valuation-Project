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


    # Add missing amenity features
    amenity_columns = [

        "has_backup_generator",
        "has_borehole",
        "has_garden",
        "has_gym",
        "has_security"

    ]


    for column in amenity_columns:

        if column not in data:

            data[column] = 0


        else:

            data[column] = int(data[column] == "on")


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


    amenity_columns = [

        "has_backup_generator",
        "has_borehole",
        "has_garden",
        "has_gym",
        "has_security"

    ]


    for column in amenity_columns:

        if column not in data:

            data[column] = 0


        else:

            data[column] = int(data[column] == "on")


    return pd.DataFrame([data])