from pydantic import BaseModel


# Response model for a user
class User(BaseModel):
    id: int
    name: str
    department: str
    available: bool


# Request model for updating availability
class AvailabilityUpdate(BaseModel):
    available: bool