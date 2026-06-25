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
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)


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
            return render_template("admin_home.html")

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



        # Snapshot the human-readable values BEFORE prepare_sale_input runs,
        # since it encodes text fields (neighborhood, condition, etc.) into
        # numbers in place. Without this, the result page would display
        # encoded integers instead of what the user actually typed.
        display_data = data.copy()



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
            price=f"{round(prediction):,}",
            data=display_data
        )



    return render_template(
        "sale.html"
    )


# SHARED PDF REPORT BUILDER
# Used by download_sale_report, download_rental_report, and
# download_insurance_report — one consistent, formal layout for all
# three report types via ReportLab Platypus (proper flowing document
# layout, not raw canvas coordinates).

BROWN_DARK = colors.HexColor("#1C140D")
BROWN_MID = colors.HexColor("#6B4A30")
GOLD = colors.HexColor("#C9A24B")
CREAM = colors.HexColor("#F5E9D8")

PROPERTY_LABELS = {
    "neighborhood": "Neighborhood",
    "town": "Town",
    "property_type": "Property Type",
    "bedrooms": "Bedrooms",
    "bathrooms": "Bathrooms",
    "floor_size_sqm": "Floor Size",
    "year_built": "Year Built",
    "condition": "Condition",
    "furnishing": "Furnishing",
    "distance_to_cbd_km": "Distance to CBD",
    "parking_spaces": "Parking Spaces",
    "floor_number": "Floor Number",
}


def build_pdf_report(report_title, subtitle, price_label, price_value, property_args, extra_sections=None):
    """
    Builds a formal, well-laid-out PDF report and returns it as bytes.

    report_title: main heading, e.g. "AI Property Valuation Report"
    subtitle: small label under the heading, e.g. "Sale Valuation"
    price_label: e.g. "Estimated Sale Price"
    price_value: e.g. "8,571,000" (already formatted, no "KES" prefix)
    property_args: a dict (typically request.args) containing raw property
        detail values, keyed by the same field names used elsewhere in
        the app (neighborhood, town, property_type, etc.) — human-readable
        text values, NOT label-encoded numbers.
    extra_sections: optional list of (heading, [(label, value), ...]) tuples
        for additional sections, e.g. insurance risk details.
    """

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=BROWN_DARK,
        alignment=TA_LEFT,
        spaceAfter=2,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=BROWN_MID,
        spaceAfter=16,
    )

    price_label_style = ParagraphStyle(
        "PriceLabel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.white,
        spaceAfter=4,
    )

    price_value_style = ParagraphStyle(
        "PriceValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        textColor=colors.white,
    )

    section_heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=BROWN_DARK,
        spaceBefore=16,
        spaceAfter=10,
    )

    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        textColor=BROWN_MID,
        leading=12,
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        textColor=BROWN_MID,
    )

    story = []

    story.append(Paragraph(report_title, title_style))
    story.append(Paragraph(subtitle, subtitle_style))

    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=16))

    # Price highlight box, built as a single-cell table so it gets a
    # solid background color (Platypus has no simple "colored box" Flowable).
    price_table = Table(
        [[Paragraph(price_label, price_label_style)],
         [Paragraph(f"KES {price_value}", price_value_style)]],
        colWidths=[doc.width],
    )

    price_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BROWN_DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, 0), 14),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
    ]))

    story.append(price_table)
    story.append(Spacer(1, 20))

    # Property details section
    story.append(Paragraph("Property Details", section_heading_style))

    detail_rows = []

    for field_key, label in PROPERTY_LABELS.items():
        if field_key not in property_args:
            continue

        value = property_args.get(field_key, "-")

        if field_key == "floor_size_sqm" and value not in ("-", None, ""):
            value = f"{value} sqm"
        elif field_key == "distance_to_cbd_km" and value not in ("-", None, ""):
            value = f"{value} km"

        detail_rows.append([label, str(value)])

    if detail_rows:

        detail_table = Table(detail_rows, colWidths=[doc.width * 0.4, doc.width * 0.6])

        detail_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10.5),
            ("TEXTCOLOR", (0, 0), (0, -1), BROWN_MID),
            ("TEXTCOLOR", (1, 0), (1, -1), BROWN_DARK),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#E7DDD0")),
        ]))

        story.append(detail_table)

    # Any extra sections (e.g. risk tier, coverage range for insurance reports)
    if extra_sections:

        for heading, rows in extra_sections:

            story.append(Paragraph(heading, section_heading_style))

            extra_table = Table(
                [[label, str(value)] for label, value in rows],
                colWidths=[doc.width * 0.4, doc.width * 0.6],
            )

            extra_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10.5),
                ("TEXTCOLOR", (0, 0), (0, -1), BROWN_MID),
                ("TEXTCOLOR", (1, 0), (1, -1), BROWN_DARK),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#E7DDD0")),
            ]))

            story.append(extra_table)

    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E7DDD0"), spaceAfter=12))

    story.append(Paragraph(
        "This figure was generated using a machine learning model trained on "
        "property features, location, and market data across Kenya. It is an "
        "estimate, not a formal appraisal.",
        disclaimer_style
    ))

    story.append(Spacer(1, 16))
    story.append(Paragraph("Generated by PropAI", footer_style))

    doc.build(story)

    buffer.seek(0)

    return buffer.getvalue()


@app.route("/download_sale_report")
@login_required
@role_required("owner")
def download_sale_report():

    price = request.args.get("price")

    pdf_bytes = build_pdf_report(
        report_title="AI Property Valuation Report",
        subtitle="Sale Valuation",
        price_label="Estimated Sale Price",
        price_value=price,
        property_args=request.args,
    )

    response = make_response(pdf_bytes)

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



        display_data = data.copy()



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
            price=f"{round(prediction):,}",
            data=display_data
        )



    return render_template(
        "rental.html"
    )


@app.route("/download_rental_report")
@login_required
@role_required("owner")
def download_rental_report():

    price = request.args.get("price")

    pdf_bytes = build_pdf_report(
        report_title="AI Property Valuation Report",
        subtitle="Rental Valuation",
        price_label="Estimated Monthly Rent",
        price_value=price,
        property_args=request.args,
    )

    response = make_response(pdf_bytes)

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

        # Snapshot BEFORE prepare_sale_input encodes text fields into
        # integers in place. assess_risk() needs the original strings
        # (e.g. "Excellent", "mid") to compare against — without this,
        # it was silently comparing encoded numbers to string literals
        # and always falling through to default risk factors.
        display_data = data.copy()

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
            display_data, prediction
        )

        return render_template(
            "insurance_result.html",
            price=f"{round(prediction):,}",
            risk_tier=risk_tier,
            risk_factors=risk_factors,
            coverage_low=f"{coverage_low:,.0f}",
            coverage_high=f"{coverage_high:,.0f}",
            data=display_data,
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

    risk_section = [
        ("Risk Assessment", [
            ("Risk Tier", risk_tier or "-"),
            ("Suggested Coverage Range", f"KES {coverage_low} - KES {coverage_high}"),
        ])
    ]

    pdf_bytes = build_pdf_report(
        report_title="PropAI Insurance Risk Assessment Report",
        subtitle="Insurance Risk Assessment",
        price_label="Estimated Property Value",
        price_value=price,
        property_args=request.args,
        extra_sections=risk_section,
    )

    response = make_response(pdf_bytes)

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

    # Kept for backward compatibility with existing links/bookmarks —
    # the actual dashboard now lives at /admin/dashboard, reached via
    # the admin landing page's "Get started" button.

    return redirect(url_for("admin_dashboard_grid"))


@app.route("/admin/dashboard")
@login_required
@role_required("admin")
def admin_dashboard_grid():

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
    search_query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    if page < 1:
        page = 1

    df = sale_location_df if dataset_type == "sale" else rental_location_df

    if search_query:
        mask = (
            df["neighborhood"].astype(str).str.contains(search_query, case=False, na=False)
            | df["town"].astype(str).str.contains(search_query, case=False, na=False)
        )
        filtered_df = df[mask]
    else:
        filtered_df = df

    total_rows = len(filtered_df)

    per_page = 50
    total_pages = max(1, (total_rows + per_page - 1) // per_page)

    if page > total_pages:
        page = total_pages

    start_index = (page - 1) * per_page
    end_index = start_index + per_page

    page_rows = filtered_df.iloc[start_index:end_index].to_dict(orient="records")
    columns = list(df.columns)

    return render_template(
        "dataset_management.html",
        dataset_type=dataset_type,
        rows=page_rows,
        columns=columns,
        total_rows=total_rows,
        search_query=search_query,
        page=page,
        total_pages=total_pages,
        start_row=start_index + 1 if total_rows > 0 else 0,
        end_row=min(end_index, total_rows),
    )


# Returns full location details (not just names) for each neighborhood in
# a given town, so the dataset-management "add listing" form can auto-fill
# distance/tier instead of letting an admin type them and risk inconsistency.

@app.route("/get_neighborhood_details/<property_type>/<town>")
@login_required
@role_required("admin")
def get_neighborhood_details(property_type, town):

    lookup = sale_location_lookup if property_type == "sale" else rental_location_lookup

    matches = lookup[lookup["neighborhood"].notna()]

    matches = matches[
        matches["neighborhood"].isin(
            (sale_location_df if property_type == "sale" else rental_location_df)[
                (sale_location_df if property_type == "sale" else rental_location_df)["town"] == town
            ]["neighborhood"].unique()
        )
    ]

    results = [
        {
            "neighborhood": row["neighborhood"],
            "distance_to_cbd_km": row["distance_to_cbd_km"],
            "location_tier": row["location_tier"],
        }
        for _, row in matches.iterrows()
    ]

    return {"neighborhoods": results}


# Adds a brand new neighborhood's location facts (town, distance, tier) as
# its own row context. In practice this is captured the first time a
# listing for that neighborhood is added — this route exists so the facts
# can be registered once, deliberately, rather than re-typed per listing.

@app.route("/admin/dataset/add_neighborhood", methods=["POST"])
@login_required
@role_required("admin")
def add_neighborhood():

    dataset_type = request.form.get("dataset_type", "sale")

    town = request.form.get("town")
    neighborhood = request.form.get("neighborhood", "").strip()
    distance_to_cbd_km = request.form.get("distance_to_cbd_km")
    location_tier = request.form.get("location_tier")

    csv_path = (
        "dataset/sale_properties.csv"
        if dataset_type == "sale"
        else "dataset/rental_properties.csv"
    )

    try:
        existing_df = pd.read_csv(csv_path)

        already_exists = (
            (existing_df["town"] == town)
            & (existing_df["neighborhood"].str.lower() == neighborhood.lower())
        ).any()

        if already_exists:
            flash(
                f"'{neighborhood}' already exists in {town}. "
                f"Use the listing form below instead — it will appear in the dropdown."
            )
            return redirect(url_for("dataset_management", dataset=dataset_type))

        flash(
            f"Noted. To actually add '{neighborhood}' in {town}, scroll to "
            f"'Add a property listing' below, select {town}, check "
            f"'This neighborhood isn't listed', and enter the same distance "
            f"({distance_to_cbd_km}km) and tier ({location_tier}) when adding "
            f"the listing — that's what creates the neighborhood."
        )

    except Exception as e:
        flash(f"Could not check existing neighborhoods: {e}")

    return redirect(url_for("dataset_management", dataset=dataset_type))


@app.route("/admin/dataset/add", methods=["POST"])
@login_required
@role_required("admin")
def add_property_row():

    dataset_type = request.form.get("dataset_type", "sale")

    csv_path = (
        "dataset/sale_properties.csv"
        if dataset_type == "sale"
        else "dataset/rental_properties.csv"
    )

    town = request.form.get("town")
    neighborhood = request.form.get("neighborhood")
    distance_to_cbd_km = request.form.get("distance_to_cbd_km")
    location_tier = request.form.get("location_tier")

    if not distance_to_cbd_km or not location_tier:
        flash(
            "Couldn't add the listing: no location details were found for that "
            "neighborhood. Pick a neighborhood from the dropdown after selecting "
            "a town, or use 'Add a new neighborhood' above first."
        )
        return redirect(url_for("dataset_management", dataset=dataset_type))

    new_row = {
        "town": town,
        "neighborhood": neighborhood,
        "distance_to_cbd_km": distance_to_cbd_km,
        "location_tier": location_tier,
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
        "price_ksh": request.form.get("target_price"),
        "listing_type": "For Sale" if dataset_type == "sale" else "For Rent",
    }

    try:
        existing_df = pd.read_csv(csv_path)

        # property_id: generate the next sequential ID rather than leaving
        # it blank/NaN, since it exists as a real column in the CSV and
        # earlier rows show it's a simple incrementing number.
        if "property_id" in existing_df.columns:
            existing_ids = pd.to_numeric(existing_df["property_id"], errors="coerce")
            next_id = int(existing_ids.max() + 1) if existing_ids.notna().any() else 1
            new_row["property_id"] = next_id

        # Diagnostic check: make sure the price field actually arrived.
        if not new_row["price_ksh"]:
            flash(
                "Warning: no sale/rent price was submitted with this listing — "
                "the row was NOT added. Check that the price field has a value "
                "before submitting."
            )
            return redirect(url_for("dataset_management", dataset=dataset_type))

        new_row_filtered = {
            k: v for k, v in new_row.items() if k in existing_df.columns
        }

        # Warn (don't silently drop) if the real CSV has columns this form
        # never fills in, so a future mismatch like this gets caught here
        # instead of showing up as a silent NaN three screens later.
        missing_columns = [
            c for c in existing_df.columns if c not in new_row_filtered
        ]

        updated_df = pd.concat(
            [existing_df, pd.DataFrame([new_row_filtered])],
            ignore_index=True
        )

        updated_df.to_csv(csv_path, index=False)

        success_message = (
            f"Added new listing in {neighborhood}, {town} to the {dataset_type} "
            f"dataset. Retrain the model from the Model Retraining page to include "
            f"it in future predictions."
        )

        
        #if missing_columns:
            #success_message += (
                #f" Note: this CSV has columns this form doesn't set "
                #f"({', '.join(missing_columns)}) — they were left blank for this row."
            #)

        flash(success_message)

    except Exception as e:

        flash(f"Failed to add listing: {e}")

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