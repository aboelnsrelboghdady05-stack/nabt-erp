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

    raw_phone = "".join(payload.phone.split())
    if raw_phone.startswith("+966"):
        clean_phone = "0" + raw_phone[4:]
    elif raw_phone.startswith("966"):
        clean_phone = "0" + raw_phone[3:]
    else:
        clean_phone = raw_phone

    clean_name = payload.name.strip()
    clean_vehicle = (payload.vehicle or "سيارة مكيفة لنقل الورد").strip()

    cursor.execute("SELECT id, status FROM drivers WHERE phone = ? OR phone = ?", (clean_phone, payload.phone))
    existing = cursor.fetchone()
    if existing:
        if existing['status'] == 'deleted':
            cursor.execute("""
            UPDATE drivers
            SET name = ?, phone = ?, vehicle = ?, commission_per_order = ?, notes = ?, status = 'available'
            WHERE id = ?
            """, (clean_name, clean_phone, clean_vehicle, payload.commission_per_order, payload.notes, existing['id']))
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
        """, (clean_name, clean_phone, clean_vehicle, payload.commission_per_order, payload.notes))
        driver_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"حدث خطأ أثناء حفظ بيانات المندوب: {e}")

    conn.close()
    return {"success": True, "id": driver_id, "message": "تمت إضافة المندوب بنجاح"}

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

    driver_name = driver['name']

    # Unlink any orders that were assigned to this driver so orders remain safe
    cursor.execute("UPDATE orders SET driver_id = NULL WHERE driver_id = ?", (driver_id,))

    # Complete clean deletion from drivers table
    cursor.execute("DELETE FROM drivers WHERE id = ?", (driver_id,))
    conn.commit()
    conn.close()

    return {"success": True, "message": f"تم حذف المندوب ({driver_name}) نهائياً من السيستم بنجاح ✅"}

