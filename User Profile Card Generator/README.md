# User Profile Card Generator

A simple full-stack web application that allows users to create a profile by entering their name, bio, and profile image URL.

The application sends the profile information from the frontend to a FastAPI backend, stores it in a SQLite database, and displays the created profile as a profile card.

---

## Features

- Create a user profile
- Enter user name
- Enter user bio
- Add a profile image using an image URL
- Store profile information in SQLite
- Retrieve all profiles
- Retrieve a profile by ID
- Input validation using Pydantic
- REST API using FastAPI
- Responsive frontend
- Frontend and backend communication using JavaScript Fetch API
- Interactive API documentation using Swagger UI

---

## Technologies Used

### Frontend

- HTML5
- CSS3
- JavaScript
- Fetch API

### Backend

- Python 3
- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic

### Database

- SQLite

### Development Tools

- Visual Studio Code
- Git
- GitHub
- Live Server

---

## Project Structure

```text
user-profile-card-generator/
│
├── frontend/
│   ├── index.html
│   │
│   ├── css/
│   │   └── style.css
│   │
│   └── js/
│       └── script.js
│
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── requirements.txt
│   │
│   ├── routes/
│   │   └── profile_routes.py
│   │
│   └── profile.db
│
├── .gitignore
└── README.md
