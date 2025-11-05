#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
from datetime import datetime
import pandas as pd
import os

from .models import (
    BookOut, 
    CategoryOut, 
    CategoryStats, 
    HealthOut, 
    StatsOverview
)

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "extracted_data.csv")

app = FastAPI(
    title="Books API",
    description="""
    API for managing and querying book information from an online bookstore.
    
    ## Features
    * Browse and search books
    * Get detailed book information
    * View categories
    * Access statistics and health information
    
    ## Notes
    All endpoints are prefixed with `/api/v1/`
    """,
    version="1.0.0",
    openapi_prefix="",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
)

def load_books_df() -> pd.DataFrame:
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=list(BookOut.model_fields.keys()))
    df = pd.read_csv(DATA_FILE)
    if 'id' in df.columns:
        df['id'] = df['id'].astype(int)
    if 'price' in df.columns:
        df['price'] = df['price'].astype(float)
    if 'rating' in df.columns:
        df['rating'] = df['rating'].astype(int)
    return df

@app.get("/api/v1/health", response_model=HealthOut, tags=["health"])
def health():
    exists = os.path.exists(DATA_FILE)
    df = load_books_df()
    return HealthOut(
        status="healthy" if exists else "degraded",
        total_books=len(df),
        data_file_exists=exists,
        timestamp=datetime.utcnow()
    )

@app.get(
    "/api/v1/books",
    response_model=List[BookOut],
    tags=["books"],
    summary="List all books",
    description="Retrieve a paginated list of all books in the database.",
    response_description="List of books with their details"
)
def list_books(
    skip: int = Query(0, ge=0, description="Number of books to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of books to return")
):
    """
    Retrieves a list of books with pagination support.

    - **skip**: Number of books to skip (for pagination)
    - **limit**: Maximum number of books to return (max 1000)
    """
    df = load_books_df()
    df = df.sort_values("id").iloc[skip: skip + limit]
    return [BookOut(**row) for row in df.to_dict(orient="records")]

@app.get(
    "/api/v1/books/search",
    response_model=List[BookOut],
    tags=["books"],
    summary="Search books",
    description="Search for books by title and/or category"
)
def search_books(
    title: Optional[str] = Query(None, description="Partial or full book title to search for"),
    category: Optional[str] = Query(None, description="Category name to filter by"),
    skip: int = Query(0, ge=0, description="Number of books to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of books to return")
):
    """
    Search for books using various criteria.

    - **title**: Optional partial book title (case-insensitive)
    - **category**: Optional category name to filter by
    - **skip**: Number of books to skip (for pagination)
    - **limit**: Maximum number of books to return (max 1000)
    """
    df = load_books_df()
    if title:
        df = df[df['title'].str.contains(title, case=False, na=False)]
    if category:
        df = df[df['category'].str.lower() == category.lower()]
    df = df.sort_values("id").iloc[skip: skip + limit]
    return [BookOut(**row) for row in df.to_dict(orient="records")]

@app.get(
    "/api/v1/books/top-rated",
    response_model=List[BookOut],
    tags=["books"],
    summary="Get top rated books",
    description="Retrieve a list of books with the highest rating"
)
def top_rated(
    limit: int = Query(20, ge=1, le=100, description="Number of top rated books to return")
):
    """
    Returns the top rated books, sorted by rating (descending) and then price (descending).

    - **limit**: Number of books to return (default 20, max 100)
    """
    df = load_books_df()
    if df.empty or 'rating' not in df.columns:
        return []
    max_rating = int(df['rating'].max())
    top = df[df['rating'] == max_rating].sort_values(['rating','price'], ascending=[False, False]).head(limit)
    return [BookOut(**row) for row in top.to_dict(orient="records")]

@app.get(
    "/api/v1/books/price-range",
    response_model=List[BookOut],
    tags=["books"],
    summary="Get books by price range",
    description="Retrieve books within a specific price range"
)
def price_range(
    min: float = Query(..., ge=0.0, alias="min"),
    max: float = Query(..., ge=0.0, alias="max"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1)
):
    """
    Retrieves books within the specified price range.

    - **min**: Minimum price (inclusive)
    - **max**: Maximum price (inclusive)
    - **skip**: Number of books to skip (for pagination)
    - **limit**: Maximum number of books to return (max 1000)
    """
    if min > max:
        raise HTTPException(status_code=400, detail="min must be <= max")
    df = load_books_df()
    if df.empty or 'price' not in df.columns:
        return []
    filtered = df[(df['price'] >= min) & (df['price'] <= max)].sort_values("price").iloc[skip: skip + limit]
    return [BookOut(**row) for row in filtered.to_dict(orient="records")]

@app.get("/api/v1/books/{book_id}", response_model=BookOut, tags=["books"])
def get_book(book_id: int):
    df = load_books_df()
    row = df[df['id'] == book_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Book not found")
    return BookOut(**row.iloc[0].to_dict())

@app.get("/api/v1/categories", response_model=List[CategoryOut], tags=["categories"])
def categories():
    df = load_books_df()
    if df.empty or 'category' not in df.columns:
        return []
    counts = df['category'].value_counts().to_dict()
    return [CategoryOut(name=k, count=int(v)) for k, v in counts.items()]

@app.get("/api/v1/stats/overview", response_model=StatsOverview, tags=["stats"])
def stats_overview():
    df = load_books_df()
    total = len(df)
    average_price = float(df['price'].mean()) if total and 'price' in df.columns else 0.0
    if 'rating' in df.columns and not df['rating'].empty:
        dist = df['rating'].value_counts().to_dict()
        rating_distribution = {i: int(dist.get(i, 0)) for i in range(1, 6)}
    else:
        rating_distribution = {i: 0 for i in range(1, 6)}
    return StatsOverview(
        total_books=total,
        average_price=average_price,
        rating_distribution=rating_distribution
    )

@app.get("/api/v1/stats/categories", response_model=List[CategoryStats], tags=["stats"])
def stats_categories():
    df = load_books_df()
    if df.empty or 'category' not in df.columns or 'price' not in df.columns:
        return []
    grouped = df.groupby('category')['price'].agg(['count','mean','min','max']).reset_index()
    return [
        CategoryStats(
            category=row['category'],
            count=int(row['count']),
            average_price=float(row['mean']),
            min_price=float(row['min']),
            max_price=float(row['max'])
        )
        for row in grouped.to_dict(orient='records')
    ]