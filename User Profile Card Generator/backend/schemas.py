from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import HttpUrl
from pydantic import field_validator


class ProfileCreate(BaseModel):

    name: str
    bio: str
    image_url: HttpUrl

    @field_validator("name", "bio")
    @classmethod
    def validate_text_fields(cls, value: str) -> str:

        value = value.strip()

        if not value:
            raise ValueError(
                "This field cannot be empty."
            )

        return value


class ProfileResponse(BaseModel):

    id: int
    name: str
    bio: str
    image_url: HttpUrl
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )