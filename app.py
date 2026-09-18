from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from config import Config
from models.note import Note, db
from models.user import User


# Flask uses this file's location to find the "templates" and "static" folders.
app = Flask(__name__)
app.config.from_object(Config)

# Store the SQLite file in the instance folder, which is meant for local data.
Path(app.instance_path).mkdir(parents=True, exist_ok=True)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Create the tables described by SQLAlchemy models if they do not already exist.
with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    """Reload the logged-in user from the session's stored ID."""
    return db.session.get(User, int(user_id))


def validate_note_input(title, content):
    """Return validation messages for submitted note fields."""
    errors = []

    if not title:
        errors.append("Title is required and cannot be empty.")
    elif len(title) < 3:
        errors.append("Title must be at least 3 characters long.")
    elif len(title) > 100:
        errors.append("Title must be 100 characters or fewer.")

    if not content:
        errors.append("Content is required and cannot be empty.")
    elif len(content) < 5:
        errors.append("Content must be at least 5 characters long.")

    return errors


def get_user_note_or_404(note_id):
    """Return one of the current user's notes, or hide it with a 404."""
    note = db.session.scalar(
        db.select(Note).where(Note.id == note_id, Note.user_id == current_user.id)
    )
    if note is None:
        abort(404)
    return note


@app.route("/")
def home():
    """Display the Notes App home page."""
    return render_template("index.html")


@app.route("/notes")
@login_required
def list_notes():
    """Display every saved note, newest first."""
    notes = db.session.scalars(
        db.select(Note)
        .where(Note.user_id == current_user.id)
        .order_by(Note.created_at.desc())
    ).all()
    return render_template("notes.html", notes=notes)


@app.route("/notes/<int:note_id>")
@login_required
def view_note(note_id):
    """Display one note selected by its database ID."""
    note = get_user_note_or_404(note_id)
    return render_template("view_note.html", note=note)


@app.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def edit_note(note_id):
    """Display an existing note's form or save its changes."""
    note = get_user_note_or_404(note_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        errors = validate_note_input(title, content)

        if errors:
            return render_template(
                "edit_note.html",
                note=note,
                errors=errors,
                title=title,
                content=content,
            )

        note.title = title
        note.content = content
        db.session.commit()
        return redirect(url_for("view_note", note_id=note.id))

    return render_template(
        "edit_note.html",
        note=note,
        errors=[],
        title=note.title,
        content=note.content,
    )


@app.route("/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(note_id):
    """Delete one note and return to the notes list."""
    note = get_user_note_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    return redirect(url_for("list_notes"))


@app.route("/notes/create", methods=["GET", "POST"])
@login_required
def create_note():
    """Display the note form or save a submitted note."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        errors = validate_note_input(title, content)

        if errors:
            return render_template(
                "create_note.html", errors=errors, title=title, content=content
            )

        note = Note(title=title, content=content, user_id=current_user.id)
        db.session.add(note)
        db.session.commit()
        return redirect(url_for("list_notes"))

    return render_template("create_note.html", errors=[], title="", content="")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user with a securely hashed password."""
    if current_user.is_authenticated:
        return redirect(url_for("list_notes"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        errors = []

        if len(username) < 3:
            errors.append("Username must be at least 3 characters long.")
        if not email or "@" not in email:
            errors.append("Enter a valid email address.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        if db.session.scalar(db.select(User).where(User.username == username)):
            errors.append("That username is already in use.")
        if db.session.scalar(db.select(User).where(User.email == email)):
            errors.append("That email address is already registered.")

        if errors:
            return render_template("register.html", errors=errors, username=username, email=email)

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Registration complete. Welcome to My Notes!", "success")
        return redirect(url_for("list_notes"))

    return render_template("register.html", errors=[], username="", email="")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate an existing user."""
    if current_user.is_authenticated:
        return redirect(url_for("list_notes"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.session.scalar(db.select(User).where(User.email == email))

        if user is None or not user.check_password(password):
            return render_template(
                "login.html",
                errors=["Invalid email or password."],
                email=email,
            )

        login_user(user)
        return redirect(url_for("list_notes"))

    return render_template("login.html", errors=[], email="")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    """End the current user's authenticated session."""
    logout_user()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
