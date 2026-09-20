from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from models import Profile
from schemas import ProfileCreate
from schemas import ProfileResponse


router = APIRouter(
    prefix="/profiles",
    tags=["Profiles"]
)


@router.post(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED
)
def create_profile(
    profile_data: ProfileCreate,
    db: Session = Depends(get_db)
):

    try:

        new_profile = Profile(
            name=profile_data.name,
            bio=profile_data.bio,
            image_url=str(profile_data.image_url)
        )

        db.add(new_profile)

        db.commit()

        db.refresh(new_profile)

        return new_profile

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create the profile."
        )


@router.get(
    "",
    response_model=list[ProfileResponse]
)
def get_profiles(
    db: Session = Depends(get_db)
):

    try:

        profiles = (
            db.query(Profile)
            .order_by(Profile.id.desc())
            .all()
        )

        return profiles

    except SQLAlchemyError:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve profiles."
        )


@router.get(
    "/{profile_id}",
    response_model=ProfileResponse
)
def get_profile(
    profile_id: int,
    db: Session = Depends(get_db)
):

    try:

        profile = (
            db.query(Profile)
            .filter(Profile.id == profile_id)
            .first()
        )

        if profile is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with ID {profile_id} not found."
            )

        return profile

    except HTTPException:
        raise

    except SQLAlchemyError:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve the profile."
        )