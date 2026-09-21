from pydantic import BaseModel


class Quote(BaseModel):
    """
    Represents a quote returned by the API.
    """

    id: int
    quote: str
    author: str
    created_at: str
