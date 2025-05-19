from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import httpx

app = FastAPI(title="Product Service")

# Mock database
products_db = [
    {"id": 1, "name": "Футбольный мяч", "price": 1500, "quantity": 10, "category": "Футбол"},
    {"id": 2, "name": "Баскетбольный мяч", "price": 2000, "quantity": 8, "category": "Баскетбол"},
    {"id": 3, "name": "Теннисная ракетка", "price": 3500, "quantity": 5, "category": "Теннис"},
    {"id": 4, "name": "Велосипед", "price": 25000, "quantity": 3, "category": "Велоспорт"},
]

class Product(BaseModel):
    name: str
    price: float
    quantity: int
    category: str

@app.get("/products", response_model=List[dict])
async def get_products():
    return products_db

@app.get("/products/{product_id}", response_model=dict)
async def get_product(product_id: int):
    product = next((p for p in products_db if p["id"] == product_id), None)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/products", response_model=dict)
async def create_product(product: Product):
    new_id = max(p["id"] for p in products_db) + 1 if products_db else 1
    new_product = {"id": new_id, **product.dict()}
    products_db.append(new_product)
    return new_product

@app.put("/products/{product_id}", response_model=dict)
async def update_product(product_id: int, product: Product):
    index = next((i for i, p in enumerate(products_db) if p["id"] == product_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Product not found")
    products_db[index] = {"id": product_id, **product.dict()}
    return products_db[index]

@app.delete("/products/{product_id}")
async def delete_product(product_id: int):
    global products_db
    products_db = [p for p in products_db if p["id"] != product_id]
    return {"message": "Product deleted"}

@app.get("/products/check_stock/{product_id}")
async def check_stock(product_id: int):
    product = next((p for p in products_db if p["id"] == product_id), None)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"quantity": product["quantity"]}

async def update_product_quantity(product_id: int, quantity_change: int):
    product = next((p for p in products_db if p["id"] == product_id), None)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if product["quantity"] + quantity_change < 0:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    product["quantity"] += quantity_change
    return product

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)