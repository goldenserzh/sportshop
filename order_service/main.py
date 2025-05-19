from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import httpx

app = FastAPI(title="Order Service")

# Mock database
orders_db = []
PRODUCT_SERVICE_URL = "http://product-service:8000"  

class OrderItem(BaseModel):
    product_id: int
    quantity: int

class OrderCreate(BaseModel):
    items: List[OrderItem]
    customer_name: str
    customer_email: str

class Order(BaseModel):
    id: int
    items: List[OrderItem]
    customer_name: str
    customer_email: str
    status: str = "created"

@app.post("/orders", response_model=Order)
async def create_order(order_data: OrderCreate):
    # Проверяем наличие товаров и их количество
    async with httpx.AsyncClient() as client:
        for item in order_data.items:
            try:
                response = await client.get(f"{PRODUCT_SERVICE_URL}/products/check_stock/{item.product_id}")
                stock = response.json()["quantity"]
                if stock < item.quantity:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Недостаточно товара {item.product_id} на складе"
                    )
            except httpx.HTTPStatusError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Товар {item.product_id} не найден"
                )

    # Резервируем товары
    async with httpx.AsyncClient() as client:
        for item in order_data.items:
            try:
                await client.put(
                    f"{PRODUCT_SERVICE_URL}/products/update_quantity/{item.product_id}",
                    json={"quantity_change": -item.quantity}
                )
            except httpx.HTTPStatusError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ошибка при резервировании товара {item.product_id}"
                )

    # Создаем заказ
    new_id = max(o["id"] for o in orders_db) + 1 if orders_db else 1
    new_order = {
        "id": new_id,
        "items": [item.dict() for item in order_data.items],
        "customer_name": order_data.customer_name,
        "customer_email": order_data.customer_email,
        "status": "created"
    }
    orders_db.append(new_order)
    return new_order

@app.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: int):
    order = next((o for o in orders_db if o["id"] == order_id), None)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/orders", response_model=List[Order])
async def get_orders():
    return orders_db

@app.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: int):
    order = next((o for o in orders_db if o["id"] == order_id), None)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Order already cancelled")
    
    # Возвращаем товары 
    async with httpx.AsyncClient() as client:
        for item in order["items"]:
            try:
                await client.put(
                    f"{PRODUCT_SERVICE_URL}/products/update_quantity/{item['product_id']}",
                    json={"quantity_change": item['quantity']}
                )
            except httpx.HTTPStatusError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ошибка при возврате товара {item['product_id']} на склад"
                )
    
    order["status"] = "cancelled"
    return {"message": "Order cancelled"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)