from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import (
    initialize_database,
    get_all_coffees,
    get_coffee_by_id,
    increment_coffee_vote
)


# ---------------------------------------
# Application startup
# ---------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the database and initialize
    # the default coffee categories.
    initialize_database()

    yield


# ---------------------------------------
# Create FastAPI application
# ---------------------------------------

app = FastAPI(
    title="Coffee Rating API",
    description="Backend API for the Coffee Rating Application",
    version="1.0.0",
    lifespan=lifespan
)


# ---------------------------------------
# CORS Configuration
# ---------------------------------------

app.add_middleware(
    CORSMiddleware,

    # Allow the frontend during local development.
    # "*" allows requests from any origin.
    allow_origins=["*"],

    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ---------------------------------------
# GET /coffees
# ---------------------------------------

@app.get("/coffees")
def get_coffees():
    """
    Return all coffee categories and their vote counts.
    """

    coffees = get_all_coffees()

    return coffees


# ---------------------------------------
# POST /coffees/{coffee_id}/vote
# ---------------------------------------

@app.post("/coffees/{coffee_id}/vote")
def vote_for_coffee(coffee_id: int):
    """
    Increase the selected coffee's vote count by 1.
    """

    # Check whether the coffee exists
    coffee = get_coffee_by_id(coffee_id)

    if coffee is None:
        raise HTTPException(
            status_code=404,
            detail="Coffee not found"
        )

    # Increase the vote count
    updated_coffee = increment_coffee_vote(coffee_id)

    return updated_coffee