from flask import (
    Flask,
    make_response,
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
    login_required,
    current_user
)


from models import db, User
from auth_decorators import role_required

from io import BytesIO
from reportlab.pdfgen import canvas


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
# Role-aware: each role lands on a different home template.


@app.route("/")

def home():

    if current_user.is_authenticated:

        if current_user.role == "insurance":
            return render_template("insurance_home.html")

        if current_user.role == "admin":
            return render_template("admin_dashboard.html")

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
# Restricted to "owner" role only.


@app.route(
    "/sale",
    methods=["GET","POST"]
)

@login_required
@role_required("owner")

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



        df = df.reindex(
        columns=sale_model.feature_names_in_,
        fill_value=0
        )

        prediction = sale_model.predict(df)[0]



        return render_template(
            "sale_result.html",
            price=f"{round(prediction):,}"
        )



    return render_template(
        "sale.html"
    )


@app.route("/download_sale_report")
@login_required
@role_required("owner")
def download_sale_report():

    price = request.args.get("price")


    buffer = BytesIO()

    pdf = canvas.Canvas(buffer)


    pdf.setFont(
        "Helvetica",
        16
    )

    pdf.drawString(
        100,
        750,
        "AI Property Valuation Report"
    )


    pdf.drawString(
        100,
        700,
        f"Estimated Sale Price: KES {price}"
    )


    pdf.drawString(
        100,
        650,
        "Generated by PropAI"
    )


    pdf.save()


    buffer.seek(0)


    response = make_response(
        buffer.getvalue()
    )


    response.headers["Content-Type"] = "application/pdf"

    response.headers["Content-Disposition"] = (
        "attachment; filename=sale_report.pdf"
    )


    return response


# RENTAL
# Restricted to "owner" role only.


@app.route(
    "/rental",
    methods=["GET","POST"]
)

@login_required
@role_required("owner")

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



        df = df.reindex(
        columns=rental_model.feature_names_in_,
        fill_value=0
        )

        prediction = rental_model.predict(df)[0]



        return render_template(
            "rental_result.html",
            price=f"{round(prediction):,}"
        )



    return render_template(
        "rental.html"
    )


@app.route("/download_rental_report")
@login_required
@role_required("owner")
def download_rental_report():

    price = request.args.get("price")


    buffer = BytesIO()

    pdf = canvas.Canvas(buffer)


    pdf.setFont(
        "Helvetica",
        16
    )


    pdf.drawString(
        100,
        750,
        "AI Property Valuation Report"
    )


    pdf.drawString(
        100,
        700,
        f"Estimated Monthly Rent: KES {price}"
    )


    pdf.drawString(
        100,
        650,
        "Generated by PropAI"
    )


    pdf.save()


    buffer.seek(0)


    response = make_response(
        buffer.getvalue()
    )


    response.headers["Content-Type"] = "application/pdf"

    response.headers["Content-Disposition"] = (
        "attachment; filename=rental_report.pdf"
    )


    return response


# INSURANCE ASSESSMENT
# Restricted to "insurance" role only.
# Reuses the sale model for valuation, then layers a rule-based
# risk score on top (see assess_risk below).


@app.route(
    "/insurance-assessment",
    methods=["GET", "POST"]
)

@login_required
@role_required("insurance")

def insurance_assessment():

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
                url_for("insurance_assessment")
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

        df = df.reindex(
            columns=sale_model.feature_names_in_,
            fill_value=0
        )

        prediction = sale_model.predict(df)[0]

        risk_tier, risk_factors, coverage_low, coverage_high = assess_risk(
            data, prediction
        )

        return render_template(
            "insurance_result.html",
            price=f"{round(prediction):,}",
            risk_tier=risk_tier,
            risk_factors=risk_factors,
            coverage_low=f"{coverage_low:,.0f}",
            coverage_high=f"{coverage_high:,.0f}",
        )

    return render_template("insurance_assessment.html")


def assess_risk(data, estimated_value):
    """
    Rule-based risk scoring layer (not a separate trained model).

    Note: data here comes from request.form.to_dict(), so every value
    is a STRING (checkbox values like "1" included), unlike the sale/
    rental routes which cast types explicitly. Comparisons below account
    for that.
    """

    score = 0
    factors = []

    # Age of the building
    try:
        year_built = int(data.get("year_built", 2020))
    except ValueError:
        year_built = 2020

    building_age = 2026 - year_built

    if building_age > 30:
        score += 3
        factors.append("Building is over 30 years old, increasing structural risk.")
    elif building_age > 15:
        score += 1
        factors.append("Building is moderately aged (15-30 years).")
    else:
        factors.append("Building is relatively new, reducing structural risk.")

    # Condition
    condition = data.get("condition", "")

    if condition in ("Excellent", "New"):
        score -= 1
        factors.append("Property condition is excellent, lowering risk.")
    elif condition == "Fair":
        score += 2
        factors.append("Property condition is only fair, raising risk.")

    # Security features (checkbox values arrive as "1" string, or are
    # absent entirely from the dict if unchecked)
    has_security = data.get("has_security") == "1"
    is_gated = data.get("is_gated_community") == "1"
    has_generator = data.get("has_backup_generator") == "1"
    has_borehole = data.get("has_borehole") == "1"

    if has_security:
        score -= 1
        factors.append("On-site security reduces risk of loss.")

    if is_gated:
        score -= 1
        factors.append("Gated community access reduces risk exposure.")

    if not has_security and not is_gated:
        score += 2
        factors.append("No security or gated access in place, raising risk.")

    if has_generator:
        score -= 1
        factors.append("Backup generator reduces risk from power-related damage.")

    if has_borehole:
        score -= 1
        factors.append("Borehole reduces dependency-related risk.")

    # Location tier
    # Real values in the dataset are: "affordable", "mid", "upper_mid", "premium"
    location_tier = str(data.get("location_tier", "mid")).strip().lower()

    if location_tier == "premium":
        score -= 1
        factors.append("Premium location tier reduces overall risk.")
    elif location_tier == "affordable":
        score += 2
        factors.append("Lower-tier (affordable) location raises overall risk.")

    # Determine tier from final score
    if score <= 0:
        risk_tier = "Low"
        coverage_low = estimated_value * 0.85
        coverage_high = estimated_value * 1.0
    elif score <= 3:
        risk_tier = "Medium"
        coverage_low = estimated_value * 0.70
        coverage_high = estimated_value * 0.85
    else:
        risk_tier = "High"
        coverage_low = estimated_value * 0.50
        coverage_high = estimated_value * 0.70

    return risk_tier, factors, coverage_low, coverage_high


@app.route("/download_insurance_report")
@login_required
@role_required("insurance")
def download_insurance_report():

    price = request.args.get("price")
    risk_tier = request.args.get("risk_tier")
    coverage_low = request.args.get("coverage_low")
    coverage_high = request.args.get("coverage_high")

    buffer = BytesIO()

    pdf = canvas.Canvas(buffer)

    pdf.setFont("Helvetica", 16)

    pdf.drawString(100, 750, "PropAI Insurance Risk Assessment Report")

    pdf.setFont("Helvetica", 12)

    pdf.drawString(100, 710, f"Estimated Property Value: KES {price}")

    pdf.drawString(100, 685, f"Risk Tier: {risk_tier}")

    pdf.drawString(
        100, 660,
        f"Suggested Coverage Range: KES {coverage_low} - KES {coverage_high}"
    )

    pdf.drawString(100, 620, "Generated by PropAI")

    pdf.save()

    buffer.seek(0)

    response = make_response(buffer.getvalue())

    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        "attachment; filename=insurance_risk_assessment.pdf"
    )

    return response


# ADMIN
# Restricted to "admin" role only.


@app.route("/admin")
@login_required
@role_required("admin")
def admin_dashboard():

    return render_template("admin_dashboard.html")


# --- ADMIN: USER MANAGEMENT ---

@app.route("/admin/users")
@login_required
@role_required("admin")
def user_management():

    users = User.query.order_by(User.id).all()

    return render_template("user_management.html", users=users)


@app.route("/admin/users/<int:user_id>/role", methods=["POST"])
@login_required
@role_required("admin")
def update_user_role(user_id):

    user = User.query.get(user_id)

    if user is None:
        flash("User not found.")
        return redirect(url_for("user_management"))

    if user.id == current_user.id:
        flash("You cannot change your own role.")
        return redirect(url_for("user_management"))

    new_role = request.form.get("role")

    if new_role not in ("owner", "insurance", "admin"):
        flash("Invalid role.")
        return redirect(url_for("user_management"))

    user.role = new_role
    db.session.commit()

    flash(f"Updated {user.email} to role '{new_role}'.")

    return redirect(url_for("user_management"))


# --- ADMIN: PERFORMANCE MONITORING ---

@app.route("/admin/performance")
@login_required
@role_required("admin")
def performance_monitoring():

    import numpy as np
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.ensemble import RandomForestRegressor

    target_col = "price_ksh"

    columns_to_drop = ["property_id", "listing_type", "land_size_acres"]

    text_columns = [
        "property_type",
        "neighborhood",
        "town",
        "condition",
        "furnishing",
        "location_tier",
    ]

    def compute_metrics(csv_path):
        """
        Re-runs the exact same train/test split used in the original
        training script (test_size=0.2, random_state=42) and reports
        metrics on the held-out 20% — this matches how the model was
        originally evaluated, rather than testing in-sample.

        Note: this trains a temporary model purely for evaluation
        purposes — it does NOT touch the live .pkl files in models/.
        """

        try:
            df = pd.read_csv(csv_path)

            existing_drops = [c for c in columns_to_drop if c in df.columns]
            df = df.drop(columns=existing_drops)

            df = df.dropna(subset=[target_col]).copy()

            for column in text_columns:
                if column in df.columns:
                    encoder = LabelEncoder()
                    df[column] = encoder.fit_transform(df[column].astype(str))

            X = df.drop(columns=[target_col])
            y = df[target_col]

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            temp_model = RandomForestRegressor(n_estimators=200, random_state=42)
            temp_model.fit(X_train, y_train)

            predictions = temp_model.predict(X_test)

            mae = mean_absolute_error(y_test, predictions)
            rmse = np.sqrt(mean_squared_error(y_test, predictions))
            r2 = r2_score(y_test, predictions)

            return {
                "mae": f"{mae:,.0f}",
                "rmse": f"{rmse:,.0f}",
                "r2": f"{r2:.3f}",
                "n_rows": len(X_test),
            }

        except Exception as e:
            return {"mae": "N/A", "rmse": "N/A", "r2": "N/A", "n_rows": 0}

    sale_metrics = compute_metrics("dataset/sale_properties.csv")
    rental_metrics = compute_metrics("dataset/rental_properties.csv")

    usage = {
        "total_users": User.query.count(),
        "owner_count": User.query.filter_by(role="owner").count(),
        "insurance_count": User.query.filter_by(role="insurance").count(),
        "admin_count": User.query.filter_by(role="admin").count(),
    }

    return render_template(
        "performance_monitoring.html",
        sale_metrics=sale_metrics,
        rental_metrics=rental_metrics,
        usage=usage,
    )


# --- ADMIN: DATASET MANAGEMENT ---

@app.route("/admin/dataset")
@login_required
@role_required("admin")
def dataset_management():

    dataset_type = request.args.get("dataset", "sale")

    df = sale_location_df if dataset_type == "sale" else rental_location_df

    preview_rows = df.head(50).to_dict(orient="records")
    columns = list(df.columns)

    return render_template(
        "dataset_management.html",
        dataset_type=dataset_type,
        rows=preview_rows,
        columns=columns,
        total_rows=len(df),
    )


@app.route("/admin/dataset/add", methods=["POST"])
@login_required
@role_required("admin")
def add_property_row():

    dataset_type = request.form.get("dataset_type", "sale")

    target_col = "sale_price" if dataset_type == "sale" else "rent_price"

    csv_path = (
        "dataset/sale_properties.csv"
        if dataset_type == "sale"
        else "dataset/rental_properties.csv"
    )

    new_row = {
        "town": request.form.get("town"),
        "neighborhood": request.form.get("neighborhood"),
        "distance_to_cbd_km": request.form.get("distance_to_cbd_km"),
        "location_tier": request.form.get("location_tier"),
        "property_type": request.form.get("property_type"),
        "bedrooms": request.form.get("bedrooms"),
        "bathrooms": request.form.get("bathrooms"),
        "floor_size_sqm": request.form.get("floor_size_sqm"),
        "year_built": request.form.get("year_built"),
        "parking_spaces": request.form.get("parking_spaces"),
        "floor_number": request.form.get("floor_number"),
        "condition": request.form.get("condition"),
        "furnishing": request.form.get("furnishing"),
        "has_swimming_pool": int(request.form.get("has_swimming_pool", 0) or 0),
        "has_gym": int(request.form.get("has_gym", 0) or 0),
        "has_borehole": int(request.form.get("has_borehole", 0) or 0),
        "has_backup_generator": int(request.form.get("has_backup_generator", 0) or 0),
        "has_security": int(request.form.get("has_security", 0) or 0),
        "has_garden": int(request.form.get("has_garden", 0) or 0),
        "is_gated_community": int(request.form.get("is_gated_community", 0) or 0),
        target_col: request.form.get("target_price"),
    }

    try:
        existing_df = pd.read_csv(csv_path)

        # Only keep keys that exist as columns in the real CSV, in case
        # your actual dataset has slightly different column names than
        # assumed above (common columns will still be added correctly).
        new_row_filtered = {
            k: v for k, v in new_row.items() if k in existing_df.columns
        }

        updated_df = pd.concat(
            [existing_df, pd.DataFrame([new_row_filtered])],
            ignore_index=True
        )

        updated_df.to_csv(csv_path, index=False)

        flash(
            f"Added new record to the {dataset_type} dataset. "
            f"Restart the app or retrain the model to use it in predictions."
        )

    except Exception as e:

        flash(f"Failed to add record: {e}")

    return redirect(url_for("dataset_management", dataset=dataset_type))


# --- ADMIN: MODEL RETRAINING ---

@app.route("/admin/retrain")
@login_required
@role_required("admin")
def model_retraining():

    return render_template(
        "model_retraining.html",
        sale_row_count=len(sale_location_df),
        rental_row_count=len(rental_location_df),
    )


@app.route("/admin/retrain/<model_type>", methods=["POST"])
@login_required
@role_required("admin")
def retrain_model(model_type):

    import shutil
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    import numpy as np

    if model_type not in ("sale", "rental"):
        flash("Invalid model type.")
        return redirect(url_for("model_retraining"))

    csv_path = (
        "dataset/sale_properties.csv"
        if model_type == "sale"
        else "dataset/rental_properties.csv"
    )

    model_path = f"models/{model_type}_model.pkl"
    encoders_path = f"models/{model_type}_encoders.pkl"

    target_col = "price_ksh"

    # Columns dropped before training in the original training script —
    # must match exactly or the retrained model's feature set won't line
    # up with what prepare_sale_input / prepare_rental_input expect.
    columns_to_drop = ["property_id", "listing_type", "land_size_acres"]

    text_columns = [
        "property_type",
        "neighborhood",
        "town",
        "condition",
        "furnishing",
        "location_tier",
    ]

    try:
        df = pd.read_csv(csv_path)

        if target_col not in df.columns:
            flash(
                f"Could not find target column '{target_col}' in {csv_path}. "
                f"Retraining aborted — no changes were made."
            )
            return redirect(url_for("model_retraining"))

        existing_drops = [c for c in columns_to_drop if c in df.columns]
        df = df.drop(columns=existing_drops)

        df = df.dropna(subset=[target_col]).copy()

        encoders = {}

        for column in text_columns:
            if column in df.columns:
                encoder = LabelEncoder()
                df[column] = encoder.fit_transform(df[column].astype(str))
                encoders[column] = encoder

        X = df.drop(columns=[target_col])
        y = df[target_col]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        new_model = RandomForestRegressor(n_estimators=200, random_state=42)
        new_model.fit(X_train, y_train)

        predictions = new_model.predict(X_test)

        mae = mean_absolute_error(y_test, predictions)
        rmse = np.sqrt(mean_squared_error(y_test, predictions))
        r2 = r2_score(y_test, predictions)

        # Backup the existing model/encoders before overwriting, so a bad
        # retrain doesn't destroy the only working version.
        if os.path.exists(model_path):
            shutil.copy(model_path, model_path.replace(".pkl", "_backup.pkl"))

        if os.path.exists(encoders_path):
            shutil.copy(encoders_path, encoders_path.replace(".pkl", "_backup.pkl"))

        with open(model_path, "wb") as f:
            pickle.dump(new_model, f)

        with open(encoders_path, "wb") as f:
            pickle.dump(encoders, f)

        flash(
            f"The {model_type} model was retrained successfully on {len(X_train)} "
            f"training rows (tested on {len(X_test)} held-out rows). "
            f"MAE: KES {mae:,.0f}, RMSE: KES {rmse:,.0f}, R²: {r2:.3f}. "
            f"Restart the app to load the new model into memory."
        )

    except Exception as e:

        flash(f"Retraining failed: {e}. No changes were made to the live model.")

    return redirect(url_for("model_retraining"))


# ROLE ACCESS DENIED


@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


if __name__ == "__main__":


    app.run(
        debug=True
    )