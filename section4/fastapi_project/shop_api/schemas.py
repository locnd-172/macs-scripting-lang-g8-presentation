"""Request and response models."""

from pydantic import BaseModel, Field


class ProductOut(BaseModel):
    sku: str
    name: str
    price_cents: int
    stock: int


class ImportResult(BaseModel):
    imported: int


class OrderItem(BaseModel):
    sku: str = Field(min_length=1)
    quantity: int = Field(gt=0)


class OrderRequest(BaseModel):
    items: list[OrderItem] = Field(min_length=1)


class OrderResponse(BaseModel):
    order_id: int
    total_cents: int
