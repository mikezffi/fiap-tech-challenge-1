from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import datetime

class BookOut(BaseModel):
    """Represents a book in the system"""
    id: int = Field(..., description="Unique identifier of the book")
    title: str = Field(..., description="Title of the book")
    price: float = Field(..., description="Price in local currency")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    availability: str = Field(..., description="Stock availability status")
    category: str = Field(..., description="Book category/genre")
    image_url: Optional[str] = Field(None, description="URL to book cover image")
    book_url: Optional[str] = Field(None, description="URL to book details page")

    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "title": "A Light in the Attic",
                "price": 51.77,
                "rating": 3,
                "availability": "In stock",
                "category": "Poetry",
                "image_url": "https://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg",
                "book_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
            }
        }

class CategoryOut(BaseModel):
    name: str
    count: int

class CategoryStats(BaseModel):
    category: str
    count: int
    average_price: float
    min_price: float
    max_price: float

class HealthOut(BaseModel):
    status: str
    total_books: int
    data_file_exists: bool
    timestamp: datetime

class StatsOverview(BaseModel):
    total_books: int
    average_price: float
    rating_distribution: Dict[int, int]