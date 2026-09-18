"""Database model for a note."""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


# This object connects Flask to SQLAlchemy. The app configures it in app.py.
db = SQLAlchemy()


class Note(db.Model):
    """A saved note in the database."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", back_populates="notes")

    def __repr__(self):
        return f"<Note {self.id}: {self.title}>"
