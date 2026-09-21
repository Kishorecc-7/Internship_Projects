from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import (
    initialize_database,
    save_quote,
    get_all_quotes
)

from models import Quote

from quote_api import fetch_random_quote


# ---------------------------------------
# Application startup
# ---------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the database and quotes table
    # when the application starts.
    initialize_database()

    yield


# ---------------------------------------
# Create FastAPI application
# ---------------------------------------

app = FastAPI(
    title="Quote Generator API",
    description="Backend for the Quote Generator with History application",
    version="1.0.0",
    lifespan=lifespan
)


# ---------------------------------------
# CORS Configuration
# ---------------------------------------

app.add_middleware(
    CORSMiddleware,

    # Allow the frontend to communicate
    # with the backend during development.
    allow_origins=["*"],

    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ---------------------------------------
# GET /quote
# ---------------------------------------

@app.get("/quote", response_model=Quote)
def generate_quote():

    # Get a random quote from the external API
    quote_data = fetch_random_quote()

    if quote_data is None:
        raise HTTPException(
            status_code=503,
            detail="Unable to fetch quote from external API."
        )

    try:
        # Save the quote in SQLite
        saved_quote = save_quote(
            quote_data["quote"],
            quote_data["author"]
        )

        return saved_quote

    except Exception:
        # Do not expose database details
        # to the frontend.
        raise HTTPException(
            status_code=500,
            detail="Unable to save quote."
        )


# ---------------------------------------
# GET /quotes
# ---------------------------------------

@app.get("/quotes", response_model=list[Quote])
def get_quotes():

    try:
        # Retrieve quote history from SQLite
        quotes = get_all_quotes()

        return quotes

    except Exception:
        # Do not expose internal database
        # details to the frontend.
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve quote history."
        )