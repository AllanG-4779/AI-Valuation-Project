from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

import pickle
import pandas as pd
import os


from dotenv import load_dotenv


from utils.prediction import (
    prepare_sale_input,
    prepare_rental_input
)


from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required
)


from models import db, User



# -----------------------------
# LOAD ENVIRONMENT VARIABLES
# -----------------------------

load_dotenv()



app = Flask(__name__)


app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY"
)


app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL"
)


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False



db.init_app(app)



with app.app_context():

    db.create_all()


# LOGIN CONFIGURATION


login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"



@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))


# LOAD DATASETS


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

# LOAD MODELS


with open(
    "models/sale_model.pkl",
    "rb"
) as file:

    sale_model = pickle.load(file)





with open(
    "models/sale_encoders.pkl",
    "rb"
) as file:

    sale_encoders = pickle.load(file)





with open(
    "models/rental_model.pkl",
    "rb"
) as file:

    rental_model = pickle.load(file)





with open(
    "models/rental_encoders.pkl",
    "rb"
) as file:

    rental_encoders = pickle.load(file)


# HOME


@app.route("/")

def home():

    return render_template(
        "index.html"
    )


# REGISTER


@app.route(
    "/register",
    methods=["GET","POST"]
)

def register():


    if request.method == "POST":


        full_name = request.form["full_name"]

        email = request.form["email"]

        password = request.form["password"]

        role = request.form.get(
            "role",
            "owner"
        )



        existing = User.query.filter_by(
            email=email
        ).first()



        if existing:

            flash(
                "Email already exists"
            )

            return redirect(
                url_for("register")
            )



        user = User(
            full_name=full_name,
            email=email,
            role=role
        )


        user.set_password(
            password
        )


        db.session.add(user)

        db.session.commit()



        login_user(user)



        return redirect(
            url_for("home")
        )



    return render_template(
        "register.html"
    )



# LOGIN


@app.route(
    "/login",
    methods=["GET","POST"]
)

def login():


    if request.method == "POST":


        email = request.form["email"]

        password = request.form["password"]



        user = User.query.filter_by(
            email=email
        ).first()



        if user and user.check_password(password):


            login_user(user)


            return redirect(
                url_for("home")
            )



        flash(
            "Invalid credentials"
        )



    return render_template(
        "login.html"
    )








@app.route("/logout")

@login_required

def logout():


    logout_user()


    return redirect(
        url_for("home")
    )


# LOCATION API


@app.route(
    "/get_neighborhoods/<property_type>/<town>"
)


def get_neighborhoods(
    property_type,
    town
):


    if property_type == "sale":

        df = sale_location_df


    elif property_type == "rental":

        df = rental_location_df


    else:

        return {
            "neighborhoods":[]
        }



    locations = df[
        df["town"] == town
    ]["neighborhood"]\
    .dropna()\
    .unique()



    return {

        "neighborhoods":
        list(locations)

    }


# SALE


@app.route(
    "/sale",
    methods=["GET","POST"]
)

@login_required

def sale():


    if request.method == "POST":



        data = request.form.to_dict()



        selected = data["neighborhood"]



        location = sale_location_lookup[
            sale_location_lookup["neighborhood"]
            ==
            selected
        ]



        if location.empty:


            flash(
                "Invalid location selected"
            )


            return redirect(
                url_for("sale")
            )



        data["distance_to_cbd_km"] = (
            location.iloc[0]
            ["distance_to_cbd_km"]
        )



        data["location_tier"] = (
            location.iloc[0]
            ["location_tier"]
        )



        df = prepare_sale_input(
            data,
            sale_encoders
        )



        prediction = sale_model.predict(df)[0]



        return render_template(
            "sale_result.html",
            price=f"{round(prediction):,}"
        )



    return render_template(
        "sale.html"
    )


# RENTAL


@app.route(
    "/rental",
    methods=["GET","POST"]
)

@login_required

def rental():


    if request.method == "POST":


        data = request.form.to_dict()



        selected = data["neighborhood"]



        location = rental_location_lookup[
            rental_location_lookup["neighborhood"]
            ==
            selected
        ]



        if location.empty:


            flash(
                "Invalid location selected"
            )


            return redirect(
                url_for("rental")
            )




        data["distance_to_cbd_km"] = (
            location.iloc[0]
            ["distance_to_cbd_km"]
        )



        data["location_tier"] = (
            location.iloc[0]
            ["location_tier"]
        )



        df = prepare_rental_input(
            data,
            rental_encoders
        )



        prediction = rental_model.predict(df)[0]



        return render_template(
            "rental_result.html",
            price=f"{round(prediction):,}"
        )



    return render_template(
        "rental.html"
    )








if __name__ == "__main__":


    app.run(
        debug=True
    )