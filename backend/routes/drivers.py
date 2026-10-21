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
    WHERE d.status != 'deleted'
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

    cursor.execute("SELECT id, status FROM drivers WHERE phone = ?", (payload.phone,))
    existing = cursor.fetchone()
    if existing:
        if existing['status'] == 'deleted':
            cursor.execute("""
            UPDATE drivers
            SET name = ?, vehicle = ?, commission_per_order = ?, notes = ?, status = 'available'
            WHERE id = ?
            """, (payload.name, payload.vehicle, payload.commission_per_order, payload.notes, existing['id']))
            conn.commit()
            conn.close()
            return {"success": True, "id": existing['id'], "message": "تمت استعادة وتحديث بيانات المندوب بنجاح"}
        else:
            conn.close()
            raise HTTPException(status_code=400, detail="يوجد مندوب مسجل بهذا الهاتف مسبقاً في النظام.")

    try:
        cursor.execute("""
        INSERT INTO drivers (name, phone, vehicle, commission_per_order, notes, status)
        VALUES (?, ?, ?, ?, ?, 'available')
        """, (payload.name, payload.phone, payload.vehicle, payload.commission_per_order, payload.notes))
        driver_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"حدث خطأ أثناء حفظ بيانات المندوب: {e}")

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

@router.delete("/{driver_id}")
def delete_driver(driver_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM drivers WHERE id = ?", (driver_id,))
    driver = cursor.fetchone()
    if not driver:
        conn.close()
        raise HTTPException(status_code=404, detail="المندوب غير موجود")

    driver_dict = dict(driver)

    # Check if driver has active orders
    cursor.execute("""
    SELECT COUNT(*) FROM orders 
    WHERE driver_id = ? AND status NOT IN ('delivered', 'cancelled')
    """, (driver_id,))
    active_count = cursor.fetchone()[0]
    if active_count > 0:
        conn.close()
        raise HTTPException(
            status_code=400, 
            detail=f"لا يمكن حذف المندوب حالياً لوجود {active_count} طلبات جارية معه. يرجى إسناد الطلبات لمندوب آخر أولاً."
        )

    # Soft delete: mark driver as deleted without unlinking past completed orders
    cursor.execute("UPDATE drivers SET status = 'deleted' WHERE id = ?", (driver_id,))
    conn.commit()
    conn.close()

    return {"success": True, "message": f"تم حذف المندوب ({driver_dict['name']}) بنجاح مع الحفاظ على سجل طلباته السابقة"}

