# Team Availability Tracker

A simple beginner-friendly full-stack web application that allows a company to view and manage the availability of its team members.

Users can see which team members are currently available or away and update their availability using a toggle switch.

The application uses a Vanilla JavaScript frontend, a FastAPI backend, and SQLite for data storage.

---

## 📌 Project Overview

The Team Availability Tracker provides a simple company dashboard where users can:

- View all team members
- View each member's department
- See whether a team member is available or away
- Change a team member's availability
- View total team members
- View the number of available members
- View the number of away members

When availability is changed, the frontend sends the updated value to the FastAPI backend.

The backend updates the SQLite database and returns the updated user to the frontend.

---

## 🛠️ Technologies Used

### Frontend

- HTML5
- CSS3
- Vanilla JavaScript
- Fetch API

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic

### Database

- SQLite

---

## 📂 Project Structure

```text
team-availability-tracker/
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
│   └── requirements.txt
│
├── database/
│   └── team.db
│
├── .gitignore
│
└── README.md