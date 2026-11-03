from fastapi import HTTPException, status

from backend.app.repositories.category_repository import CategoryRepository
from backend.app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from backend.app.schemas.user import UserCredentials, UserRole


class CategoryService:
    def __init__(self, repository: CategoryRepository) -> None:
        self.repository = repository

    async def create(
        self,
        data: CategoryCreate,
        seller: UserCredentials,
    ) -> CategoryRead:
        category = await self.repository.create(data, str(seller.id))
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A category with this name already exists.",
            )
        return category

    async def get(self, category_id: str) -> CategoryRead:
        category = await self.repository.get(category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )
        return category

    async def list(
        self,
        user: UserCredentials | None = None,
    ) -> list[CategoryRead]:
        categories = await self.repository.list()
        if user is None or user.role is not UserRole.SELLER:
            return categories
        return [
            category
            for category in categories
            if category.seller_id is None or category.seller_id == user.id
        ]

    async def update(
        self,
        category_id: str,
        data: CategoryUpdate,
        seller: UserCredentials,
    ) -> CategoryRead:
        result = await self.repository.update(
            category_id,
            data,
            str(seller.id),
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )
        if result == "duplicate":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A category with this name already exists.",
            )
        if result == "forbidden":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )
        if result == "foreign_products":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category cannot be renamed while it contains products owned by another seller.",
            )
        return await self.get(category_id)

    async def delete(self, category_id: str, seller: UserCredentials) -> None:
        result = await self.repository.delete(category_id, str(seller.id))
        if result == "missing":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )
        if result == "in_use":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category cannot be deleted while products use it.",
            )
        if result == "forbidden":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )
