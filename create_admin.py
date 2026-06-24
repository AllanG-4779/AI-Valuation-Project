"""
create_admin.py

Run this once to create an admin account, since "admin" is intentionally
NOT an option on the public registration form (you don't want random users
able to self-register as system administrators).

Usage:
    python create_admin.py

Edit the values below before running, then you can delete or keep this
file — running it again with the same email will just show an error
since emails must be unique.
"""

from app import app
from models import db, User

ADMIN_NAME = "Admin"
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin"

with app.app_context():

    existing = User.query.filter_by(email=ADMIN_EMAIL).first()

    if existing:
        print(f"A user with email {ADMIN_EMAIL} already exists. Nothing created.")
    else:
        admin_user = User(
            full_name=ADMIN_NAME,
            email=ADMIN_EMAIL,
            role="admin"
        )
        admin_user.set_password(ADMIN_PASSWORD)

        db.session.add(admin_user)
        db.session.commit()

        print(f"Admin account created: {ADMIN_EMAIL}")