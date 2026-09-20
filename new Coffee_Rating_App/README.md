# ☕ Coffee Rating Application

A beginner-friendly full-stack web application that allows users to view different coffee categories and vote for their favorite coffee.

Each time a user clicks the **Vote** button, the selected coffee's vote count is increased by 1 and permanently stored in a SQLite database.

---

## 📌 Project Overview

The Coffee Rating Application is designed to demonstrate the basic concepts of frontend and backend development.

Users can:

- View available coffee categories
- See the current vote count for each coffee
- Vote for their favorite coffee
- See the updated vote count without refreshing the page

The application uses a simple REST API built with FastAPI and stores data using SQLite.

---

## 🛠️ Technologies Used

### Frontend

- HTML
- CSS
- JavaScript
- Fetch API

### Backend

- Python
- FastAPI
- Uvicorn

### Database

- SQLite

---

## 📂 Project Structure

```text
Coffee_Rating_App/
│
├── .gitignore
├── README.md
│
├── Backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   └── requirements.txt
│
├── Database/
│   └── coffee.db
│
└── Frontend/
    ├── index.html
    │
    ├── css/
    │   └── style.css
    │
    └── js/
        └── script.js
