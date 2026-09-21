from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import (
    initialize_database,
    get_all_users,
    update_user_availability
)

from models import User, AvailabilityUpdate


# Run database initialization when the application starts
@asynccontextmanager
async def lifespan(app: FastAPI):

    initialize_database()

    yield


# Create FastAPI application
app = FastAPI(
    title="Team Availability Tracker API",
    description="Backend API for the Team Availability Tracker",
    version="1.0.0",
    lifespan=lifespan
)


# =========================
# CORS Configuration
# =========================

app.add_middleware(
    CORSMiddleware,

    # Allow local frontend to communicate with FastAPI
    allow_origins=["*"],

    allow_credentials=False,

    allow_methods=["*"],

    allow_headers=["*"]
)


# =========================
# GET /users
# =========================

@app.get(
    "/users",
    response_model=list[User]
)
def get_users():

    try:

        users = get_all_users()

        return users

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve users."
        )


# =========================
# PATCH /users/{user_id}/availability
# =========================

@app.patch(
    "/users/{user_id}/availability",
    response_model=User
)
def update_availability(
    user_id: int,
    availability_data: AvailabilityUpdate
):

    try:

        updated_user = update_user_availability(
            user_id,
            availability_data.available
        )

        # User doesn't exist
        if updated_user is None:

            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        return updated_user

    except HTTPException:
        raise

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Unable to update user availability."
        )