from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter(prefix="/api/products", tags=["Products"])

class ProductCreateSchema(BaseModel):
    name: str
    category: str
    price: float
    cost: float = 0.0
    stock: int = 100
    image_url: Optional[str] = "https://images.unsplash.com/photo-1561181286-d3fee7d55364?w=500"
    description: Optional[str] = None

class ProductUpdateStockSchema(BaseModel):
    stock: int

@router.get("")
def get_products(category: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM products WHERE is_active = 1"
    params = []
    if category and category != "all":
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY id ASC"
    cursor.execute(query, params)
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return products

@router.post("")
def create_product(payload: ProductCreateSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO products (name, category, price, cost, stock, image_url, description)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (payload.name, payload.category, payload.price, payload.cost, payload.stock, payload.image_url, payload.description))
    p_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "id": p_id}

@router.put("/{product_id}/stock")
def update_stock(product_id: int, payload: ProductUpdateStockSchema):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (payload.stock, product_id))
    conn.commit()
    conn.close()
    return {"success": True, "stock": payload.stock}
