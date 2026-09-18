# Notes App

A beginner-friendly Flask application for creating and organizing notes.

## Run locally

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install the dependency:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Start the application:

   ```powershell
   python app.py
   ```

4. Open `http://127.0.0.1:5000/` in your browser.

The application uses SQLite through Flask-SQLAlchemy. Create, update, and delete
note features have intentionally not been added yet.
