from fastapi import HTTPException, status

from backend.app.repositories.category_repository import CategoryRepository
from backend.app.repositories.product_repository import ProductRepository
from backend.app.schemas.category import CategoryRead
from backend.app.schemas.product import (
    ProductCreate,
    ProductRead,
    ProductStatus,
    ProductUpdate,
)
from backend.app.schemas.user import UserCredentials


class ProductService:
    def __init__(
        self,
        repository: ProductRepository,
        category_repository: CategoryRepository,
    ) -> None:
        self.repository = repository
        self.category_repository = category_repository

    async def create(
        self,
        data: ProductCreate,
        seller: UserCredentials,
    ) -> ProductRead:
        category = await self._get_category(data.category, str(seller.id))
        canonical_data = data.model_copy(update={"category": category.name})
        product = await self.repository.create(canonical_data, str(seller.id))
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="The selected category does not exist.",
            )
        return product

    async def get(
        self,
        product_id: str,
        user: UserCredentials | None = None,
    ) -> ProductRead:
        product = await self.repository.get(product_id)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )
        if product.status is not ProductStatus.ACTIVE and (
            user is None or product.seller_id != user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )
        return product

    async def list(
        self,
        *,
        search: str | None,
        category: str | None,
        seller_id: str | None,
        seller_filter_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[ProductRead], int]:
        return await self.repository.list(
            search=search,
            category=category,
            seller_id=seller_id,
            seller_filter_id=seller_filter_id,
            limit=limit,
            offset=offset,
        )

    async def update(
        self,
        product_id: str,
        data: ProductUpdate,
        seller: UserCredentials,
    ) -> ProductRead:
        existing = await self.repository.get(product_id)
        if existing is None or existing.seller_id != seller.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )
        category = await self._get_category(data.category, str(seller.id))
        canonical_data = data.model_copy(update={"category": category.name})
        product = await self.repository.update(
            product_id,
            canonical_data,
            str(seller.id),
        )
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="The selected category does not exist.",
            )
        return product

    async def delete(self, product_id: str, seller: UserCredentials) -> None:
        result = await self.repository.delete(product_id, str(seller.id))
        if result == -2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )
        if result == -1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product cannot be deleted while a confirmed order uses it.",
            )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )

    async def _get_category(
        self,
        name: str,
        seller_id: str,
    ) -> CategoryRead:
        category = await self.category_repository.get_by_name(name)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Category '{name}' does not exist.",
            )
        if category.seller_id is not None and str(category.seller_id) != seller_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )
        return category
