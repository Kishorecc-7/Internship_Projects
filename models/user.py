"""Database model and password helpers for application users."""

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from models.note import db


class User(UserMixin, db.Model):
    """A registered user who owns notes."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    notes = db.relationship("Note", back_populates="user", lazy=True)

    def set_password(self, password):
        """Hash a password before it is saved."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check a submitted password against its saved hash."""
        return check_password_hash(self.password_hash, password)
