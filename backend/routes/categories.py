from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.category import CategoryResponse
from backend.services import category_service


router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)


@router.get(
    "",
    response_model=list[CategoryResponse],
    summary="List Nobel Prize categories"
)
def list_categories(db: Session = Depends(get_db)):
    return category_service.list_categories(db)


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get a Nobel Prize category",
    responses={404: {"description": "Category not found"}}
)
def get_category(
    category_id: int = Path(
        description="Nobel Explorer internal category database ID"
    ),
    db: Session = Depends(get_db)
):
    return category_service.get_category(db, category_id)
