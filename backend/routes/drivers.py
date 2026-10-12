from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter(prefix="/api/drivers", tags=["Drivers"])

class DriverCreateSchema(BaseModel):
    name: str
    phone: str
    vehicle: Optional[str] = "سيارة مكيفة لنقل الورد"
    commission_per_order: float = 25.0
    notes: Optional[str] = None

class DriverStatusUpdateSchema(BaseModel):
    status: str # available, on_delivery, off_duty

@router.get("")
def get_drivers():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT d.*,
           (SELECT COUNT(*) FROM orders WHERE driver_id = d.id AND status NOT IN ('delivered', 'cancelled')) as current_active_orders
    FROM drivers d
    ORDER BY d.id ASC
    """)
    drivers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return drivers

@router.get("/{driver_id}")
def get_driver_detail(driver_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,))
    driver_row = cursor.fetchone()
    if not driver_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Driver not found")

    driver = dict(driver_row)

    # Assigned active orders
    cursor.execute("""
    SELECT * FROM orders 
    WHERE driver_id = ? AND status NOT IN ('delivered', 'cancelled')
    ORDER BY id DESC
    """, (driver_id,))
    driver["active_orders"] = [dict(r) for r in cursor.fetchall()]

    # Completed orders
    cursor.execute("""
    SELECT * FROM orders 
    WHERE driver_id = ? AND status = 'delivered'
    ORDER BY id DESC
    LIMIT 20
    """, (driver_id,))
    driver["delivered_orders"] = [dict(r) for r in cursor.fetchall()]

    driver["total_commission_earned"] = len(driver["delivered_orders"]) * driver["commission_per_order"]

    conn.close()
    return driver

@router.post("")
def create_driver(payload: DriverCreateSchema):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        INSERT INTO drivers (name, phone, vehicle, commission_per_order, notes)
        VALUES (?, ?, ?, ?, ?)
        """, (payload.name, payload.phone, payload.vehicle, payload.commission_per_order, payload.notes))
        driver_id = cursor.lastrowid
        conn.commit()
    except Exception:
        conn.close()
        raise HTTPException(status_code=400, detail="Driver with this phone already exists.")

    conn.close()
    return {"success": True, "id": driver_id}

@router.put("/{driver_id}/status")
def update_driver_status(driver_id: int, payload: DriverStatusUpdateSchema):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE drivers SET status = ? WHERE id = ?", (payload.status, driver_id))
    conn.commit()
    conn.close()
    return {"success": True, "status": payload.status}
