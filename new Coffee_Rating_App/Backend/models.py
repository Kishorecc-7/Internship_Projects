from pydantic import BaseModel


class Coffee(BaseModel):
    """
    Represents a coffee returned by the API.
    """

    id: int
    name: str
    votes: int