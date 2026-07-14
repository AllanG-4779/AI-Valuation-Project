from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """
    User account model.

    UserMixin (from flask_login) gives this class the methods Flask-Login
    needs automatically: is_authenticated, is_active, is_anonymous, get_id().
    """

    id            = db.Column(db.Integer, primary_key=True)
    full_name     = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default="owner")
    # role values: "owner", "insurance", "admin"

    valuations            = db.relationship("Valuation", backref="user", lazy=True, cascade="all, delete-orphan")
    insurance_assessments = db.relationship("InsuranceAssessment", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self):
        return f"<User {self.email}>"


class Valuation(db.Model):
    """
    Saved property valuation result for an owner user.
    Stores all submitted property inputs plus the model's predicted price,
    so the user can view their history, re-run with edited inputs, and
    download a report for any past valuation.
    """

    id                   = db.Column(db.Integer, primary_key=True)
    user_id              = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # User-provided label / note
    label                = db.Column(db.String(120), nullable=True)

    # Valuation type
    valuation_type       = db.Column(db.String(10), nullable=False)  # "sale" or "rental"

    # Location
    town                 = db.Column(db.String(60), nullable=False)
    neighborhood         = db.Column(db.String(60), nullable=False)
    distance_to_cbd_km   = db.Column(db.Float, nullable=True)
    location_tier        = db.Column(db.String(20), nullable=True)

    # Property attributes
    property_type        = db.Column(db.String(40), nullable=False)
    bedrooms             = db.Column(db.Integer, nullable=True)
    bathrooms            = db.Column(db.Integer, nullable=True)
    floor_size_sqm       = db.Column(db.Integer, nullable=True)
    year_built           = db.Column(db.Integer, nullable=True)
    parking_spaces       = db.Column(db.Integer, nullable=True)
    floor_number         = db.Column(db.Integer, nullable=True)
    condition            = db.Column(db.String(20), nullable=True)
    furnishing           = db.Column(db.String(30), nullable=True)

    # Features (amenities)
    has_swimming_pool    = db.Column(db.Integer, default=0)
    has_gym              = db.Column(db.Integer, default=0)
    has_borehole         = db.Column(db.Integer, default=0)
    has_backup_generator = db.Column(db.Integer, default=0)
    has_security         = db.Column(db.Integer, default=0)
    has_garden           = db.Column(db.Integer, default=0)
    is_gated_community   = db.Column(db.Integer, default=0)

    # Neighborhood factors (auto-populated at prediction time)
    distance_to_school_km   = db.Column(db.Float, nullable=True)
    distance_to_hospital_km = db.Column(db.Float, nullable=True)
    crime_index             = db.Column(db.Integer, nullable=True)
    road_quality            = db.Column(db.String(20), nullable=True)

    # Predicted result
    predicted_price      = db.Column(db.BigInteger, nullable=False)

    created_at           = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at           = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Valuation {self.id} {self.valuation_type} {self.neighborhood}>"


class InsuranceAssessment(db.Model):
    """
    Saved insurance risk assessment result for an insurance officer user.
    Stores all submitted property inputs, the predicted value, risk tier,
    and coverage range so the officer can view and download past assessments.
    """

    id                   = db.Column(db.Integer, primary_key=True)
    user_id              = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    label                = db.Column(db.String(120), nullable=True)

    # Location
    town                 = db.Column(db.String(60), nullable=False)
    neighborhood         = db.Column(db.String(60), nullable=False)
    distance_to_cbd_km   = db.Column(db.Float, nullable=True)
    location_tier        = db.Column(db.String(20), nullable=True)

    # Property attributes
    property_type        = db.Column(db.String(40), nullable=False)
    bedrooms             = db.Column(db.Integer, nullable=True)
    bathrooms            = db.Column(db.Integer, nullable=True)
    floor_size_sqm       = db.Column(db.Integer, nullable=True)
    year_built           = db.Column(db.Integer, nullable=True)
    parking_spaces       = db.Column(db.Integer, nullable=True)
    floor_number         = db.Column(db.Integer, nullable=True)
    condition            = db.Column(db.String(20), nullable=True)
    furnishing           = db.Column(db.String(30), nullable=True)

    # Features
    has_swimming_pool    = db.Column(db.Integer, default=0)
    has_gym              = db.Column(db.Integer, default=0)
    has_borehole         = db.Column(db.Integer, default=0)
    has_backup_generator = db.Column(db.Integer, default=0)
    has_security         = db.Column(db.Integer, default=0)
    has_garden           = db.Column(db.Integer, default=0)
    is_gated_community   = db.Column(db.Integer, default=0)

    # Neighborhood factors
    distance_to_school_km   = db.Column(db.Float, nullable=True)
    distance_to_hospital_km = db.Column(db.Float, nullable=True)
    crime_index             = db.Column(db.Integer, nullable=True)
    road_quality            = db.Column(db.String(20), nullable=True)

    # Prediction + risk results
    predicted_value      = db.Column(db.BigInteger, nullable=False)
    risk_tier            = db.Column(db.String(10), nullable=False)
    coverage_low         = db.Column(db.BigInteger, nullable=True)
    coverage_high        = db.Column(db.BigInteger, nullable=True)

    created_at           = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at           = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<InsuranceAssessment {self.id} {self.risk_tier} {self.neighborhood}>"