from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
import json

router = APIRouter(prefix="/api/customers", tags=["Customers"])

class OccasionSchema(BaseModel):
    type: str # ذكرى زواج، عيد ميلاد، تخرج، يوم الأم، أخرى
    date: str # MM-DD or YYYY-MM-DD
    notes: Optional[str] = ""

class CustomerCreateSchema(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    special_occasions: Optional[List[OccasionSchema]] = []

@router.get("")
def get_customers(search: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM customers WHERE 1=1"
    params = []
    if search:
        query += " AND (name LIKE ? OR phone LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term])

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    customers = [dict(row) for row in cursor.fetchall()]

    for c in customers:
        try:
            c["special_occasions"] = json.loads(c["special_occasions"] or "[]")
        except Exception:
            c["special_occasions"] = []

    conn.close()
    return customers

@router.get("/{customer_id}")
def get_customer_detail(customer_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Customer not found")

    customer = dict(row)
    try:
        customer["special_occasions"] = json.loads(customer["special_occasions"] or "[]")
    except Exception:
        customer["special_occasions"] = []

    # Get customer orders
    cursor.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC", (customer_id,))
    customer["orders"] = [dict(r) for r in cursor.fetchall()]

    # Get customer unpaid invoices
    cursor.execute("SELECT * FROM invoices WHERE customer_id = ? AND status != 'paid' ORDER BY id DESC", (customer_id,))
    customer["unpaid_invoices"] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return customer

@router.post("")
def create_customer(payload: CustomerCreateSchema):
    conn = get_db()
    cursor = conn.cursor()

    occasions_json = json.dumps([occ.model_dump() for occ in payload.special_occasions], ensure_ascii=False)

    try:
        cursor.execute("""
        INSERT INTO customers (name, phone, email, address, notes, special_occasions)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (payload.name, payload.phone, payload.email, payload.address, payload.notes, occasions_json))
        cust_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail="Customer with this phone number might already exist.")

    conn.close()
    return {"success": True, "id": cust_id}

@router.post("/{customer_id}/occasions")
def add_customer_occasion(customer_id: int, payload: OccasionSchema):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT special_occasions FROM customers WHERE id = ?", (customer_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Customer not found")

    try:
        occasions = json.loads(row[0] or "[]")
    except Exception:
        occasions = []

    occasions.append(payload.model_dump())
    cursor.execute("UPDATE customers SET special_occasions = ? WHERE id = ?", (json.dumps(occasions, ensure_ascii=False), customer_id))
    conn.commit()
    conn.close()
    return {"success": True, "occasions": occasions}

@router.delete("/{customer_id}")
def delete_customer(customer_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM customers WHERE id = ?", (customer_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="العميل غير موجود")

    cust_name = row["name"]

    # Detach customer from any existing orders so orders are NEVER deleted
    cursor.execute("UPDATE orders SET customer_id = NULL WHERE customer_id = ?", (customer_id,))
    # Detach customer from invoices
    cursor.execute("UPDATE invoices SET customer_id = NULL WHERE customer_id = ?", (customer_id,))

    # Delete customer record
    cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    conn.commit()
    conn.close()

    return {"success": True, "message": f"تم حذف العميل {cust_name} بنجاح"}
