from flask import Flask, render_template, request
import pickle
import pandas as pd
from utils.prediction import (
    prepare_sale_input,
    prepare_rental_input
)


app = Flask(__name__)

# Load location information
sale_location_df = pd.read_csv(
    "dataset/sale_properties.csv"
)

rental_location_df = pd.read_csv(
    "dataset/rental_properties.csv"
)


sale_location_lookup = (
    sale_location_df[
        [
            "neighborhood",
            "distance_to_cbd_km",
            "location_tier"
        ]
    ]
    .drop_duplicates()
)

rental_location_lookup = (
    rental_location_df[
        [
            "neighborhood",
            "distance_to_cbd_km",
            "location_tier"
        ]
    ]
    .drop_duplicates()
)

# Load sale model
with open("models/sale_model.pkl", "rb") as file:
    sale_model = pickle.load(file)


# Load sale encoders
with open("models/sale_encoders.pkl", "rb") as file:
    sale_encoders = pickle.load(file)


# Load rental model
with open("models/rental_model.pkl", "rb") as file:
    rental_model = pickle.load(file)


# Load rental encoders
with open("models/rental_encoders.pkl", "rb") as file:
    rental_encoders = pickle.load(file)



@app.route("/")
def home():

    return render_template("index.html")




@app.route("/sale", methods=["GET", "POST"])
def sale():


    if request.method == "POST":


        data = {

            "property_type": request.form["property_type"],
            "neighborhood": request.form["neighborhood"],
            "town": request.form["town"],

            "bedrooms": int(request.form["bedrooms"]),

            "bathrooms": int(request.form["bathrooms"]),

            "parking_spaces": int(request.form["parking_spaces"]),

            "floor_size_sqm": int(request.form["floor_size_sqm"]),

            "year_built": int(request.form["year_built"]),

            "floor_number": int(request.form["floor_number"]),


            "condition": request.form["condition"],

            "furnishing": request.form["furnishing"],


            "has_swimming_pool": int(request.form.get("has_swimming_pool", 0)),
 
            "has_gym": int(request.form.get("has_gym", 0)),

            "has_borehole": int(request.form.get("has_borehole", 0)),

            "has_backup_generator": int(request.form.get("has_backup_generator", 0)),

            "has_security": int(request.form.get("has_security", 0)),

            "has_garden": int(request.form.get("has_garden", 0)),

            "is_gated_community": int(request.form.get("is_gated_community", 0)),

        }

        # Get location details automatically

        selected_location = data["neighborhood"]


        location = sale_location_lookup[
            sale_location_lookup["neighborhood"] == selected_location
        ]


        data["distance_to_cbd_km"] = location[
            "distance_to_cbd_km"
        ].values[0]


        data["location_tier"] = location[
            "location_tier"
        ].values[0]

        # Encode text values

        df = prepare_sale_input(data, sale_encoders)


        prediction = sale_model.predict(df)[0]


        prediction = round(prediction)



        return render_template(
            "sale_result.html",
            price=f"{prediction:,.0f}"
        )



    return render_template("sale.html")

@app.route("/rental", methods=["GET", "POST"])
def rental():


    if request.method == "POST":


        data = {


            "property_type": request.form["property_type"],
            "neighborhood": request.form["neighborhood"],
            "town": request.form["town"],

            "bedrooms": int(request.form["bedrooms"]),

            "bathrooms": int(request.form["bathrooms"]),

            "parking_spaces": int(request.form["parking_spaces"]),

            "floor_size_sqm": int(request.form["floor_size_sqm"]),

            "year_built": int(request.form["year_built"]),

            "floor_number": int(request.form["floor_number"]),


            "condition": request.form["condition"],

            "furnishing": request.form["furnishing"],


            "has_swimming_pool": int(request.form.get("has_swimming_pool", 0)),
 
            "has_gym": int(request.form.get("has_gym", 0)),

            "has_borehole": int(request.form.get("has_borehole", 0)),

            "has_backup_generator": int(request.form.get("has_backup_generator", 0)),

            "has_security": int(request.form.get("has_security", 0)),

            "has_garden": int(request.form.get("has_garden", 0)),

            "is_gated_community": int(request.form.get("is_gated_community", 0)),

        }

        # Get location details automatically

        selected_location = data["neighborhood"]


        location = rental_location_lookup[
            rental_location_lookup["neighborhood"] == selected_location
        ]


        data["distance_to_cbd_km"] = location[
            "distance_to_cbd_km"
        ].values[0]


        data["location_tier"] = location[
            "location_tier"
        ].values[0]



        df = prepare_rental_input(
            data,
            rental_encoders
        )


        prediction = rental_model.predict(df)[0]


        prediction = round(prediction)



        return render_template(

            "rental_result.html",

            price=f"{prediction:,.0f}"

        )




    return render_template("rental.html")

@app.route("/get_neighborhoods/<property_type>/<town>")
def get_neighborhoods(property_type, town):


    if property_type == "sale":

        df = sale_location_df


    elif property_type == "rental":

        df = rental_location_df


    else:

        return {
            "neighborhoods": []
        }


    locations = df[
        df["town"] == town
    ]["neighborhood"].dropna().unique()



    return {
        "neighborhoods": list(locations)
    }



if __name__ == "__main__":

    app.run(debug=True)