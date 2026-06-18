from flask import Flask, render_template, request
import pickle
import pandas as pd
from utils.prediction import prepare_sale_input


app = Flask(__name__)

# Load location information
location_df = pd.read_csv(
    "dataset/sale_properties.csv"
)


location_lookup = (
    location_df[
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


        location = location_lookup[
            location_lookup["neighborhood"] == selected_location
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
            "result.html",
            price=f"{prediction:,.0f}"
        )



    return render_template("sale.html")





if __name__ == "__main__":

    app.run(debug=True)