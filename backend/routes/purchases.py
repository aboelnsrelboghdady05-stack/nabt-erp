from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db
from datetime import datetime, date

router = APIRouter(prefix="/api/purchases", tags=["Purchase Requests"])

class PurchaseCreateSchema(BaseModel):
    item_name: str
    category: Optional[str] = "مشتريات عامة"
    quantity: Optional[str] = "-"
    estimated_amount: Optional[float] = 0.0
    urgency: str = "عاجل جداً اليوم"  # عاجل جداً اليوم, عادي غداً
    reason: Optional[str] = None
    requested_by_name: str
    requested_by_role: str
    requested_by_id: Optional[int] = None

class PurchaseEndorseSchema(BaseModel):
    endorsed_by_name: str
    endorsed_by_role: str
    endorsed_by_id: Optional[int] = None
    endorsement_notes: Optional[str] = None

class PurchaseApproveSchema(BaseModel):
    approved_by_name: str
    approved_by_id: Optional[int] = None
    gm_notes: Optional[str] = None
    record_expense: bool = True
    payment_method: str = "cash"

class PurchaseRejectSchema(BaseModel):
    rejected_by_name: str
    rejection_reason: str

@router.get("")
def get_purchases(status: Optional[str] = None, user_role: Optional[str] = None, user_name: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM purchase_requests WHERE 1=1"
    params = []

    if status and status != "all":
        query += " AND status = ?"
        params.append(status)

    # If the user is a florist, show all requests but prioritize or filter if requested
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    # Global stats
    cursor.execute("SELECT COUNT(*) FROM purchase_requests")
    total_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM purchase_requests WHERE status = 'pending_review'")
    pending_endorsement = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM purchase_requests WHERE status = 'endorsed'")
    pending_gm = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*), COALESCE(SUM(estimated_amount), 0) FROM purchase_requests WHERE status = 'approved'")
    approved_row = cursor.fetchone()
    approved_count = approved_row[0]
    approved_total_amount = approved_row[1]

    cursor.execute("SELECT COUNT(*) FROM purchase_requests WHERE status = 'rejected'")
    rejected_count = cursor.fetchone()[0]

    conn.close()

    return {
        "requests": rows,
        "stats": {
            "total_count": total_count,
            "pending_endorsement": pending_endorsement,
            "pending_gm": pending_gm,
            "approved_count": approved_count,
            "approved_total_amount": round(approved_total_amount, 2),
            "rejected_count": rejected_count
        }
    }

@router.post("")
def create_purchase_request(payload: PurchaseCreateSchema):
    conn = get_db()
    cursor = conn.cursor()

    # Generate sequential request number PR-XXXX
    cursor.execute("SELECT MAX(id) FROM purchase_requests")
    max_id = cursor.fetchone()[0] or 0
    request_number = f"PR-{1000 + max_id + 1}"

    cat = payload.category or "مشتريات عامة"
    qty = payload.quantity.strip() if payload.quantity and payload.quantity.strip() else "-"
    amt = payload.estimated_amount or 0.0

    cursor.execute("""
    INSERT INTO purchase_requests (
        request_number, item_name, category, quantity, estimated_amount,
        urgency, reason, requested_by_id, requested_by_name, requested_by_role,
        status, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_review', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (
        request_number, payload.item_name.strip(), cat, qty,
        amt, payload.urgency, payload.reason, payload.requested_by_id,
        payload.requested_by_name, payload.requested_by_role
    ))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "id": new_id,
        "request_number": request_number,
        "message": f"تم إنشاء طلب الشراء رقم {request_number} بنجاح وبانتظار التعميد"
    }

@router.put("/{request_id}/endorse")
def endorse_purchase_request(request_id: int, payload: PurchaseEndorseSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM purchase_requests WHERE id = ?", (request_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="طلب الشراء غير موجود")

    req = dict(row)
    if req["status"] not in ("pending_review", "rejected"):
        conn.close()
        raise HTTPException(status_code=400, detail="الطلب تم تعميده أو اعتماده مسبقاً")

    cursor.execute("""
    UPDATE purchase_requests
    SET status = 'endorsed',
        endorsed_by_id = ?,
        endorsed_by_name = ?,
        endorsed_by_role = ?,
        endorsed_at = CURRENT_TIMESTAMP,
        endorsement_notes = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (
        payload.endorsed_by_id, payload.endorsed_by_name, payload.endorsed_by_role,
        payload.endorsement_notes, request_id
    ))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"تم تعميد طلب الشراء {req['request_number']} بنجاح وتم تحويله للمدير العام (ياسر) للموافقة النهائية"
    }

@router.put("/{request_id}/approve")
def approve_purchase_request(request_id: int, payload: PurchaseApproveSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM purchase_requests WHERE id = ?", (request_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="طلب الشراء غير موجود")

    req = dict(row)
    if req["status"] == "approved":
        conn.close()
        raise HTTPException(status_code=400, detail="الطلب معتمد مسبقاً")

    expense_id = None
    if payload.record_expense:
        # Automatically insert into expenses table
        exp_date = date.today().strftime("%Y-%m-%d")
        exp_title = f"شراء: {req['item_name']} ({req['request_number']})"
        exp_notes = f"طلب شراء معتمد بواسطة {payload.approved_by_name}. الكمية: {req['quantity']}."
        if payload.gm_notes:
            exp_notes += f" ملاحظات: {payload.gm_notes}"

        cursor.execute("""
        INSERT INTO expenses (title, category, amount, payment_method, expense_date, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            exp_title, req["category"], req["estimated_amount"], payload.payment_method,
            exp_date, exp_notes
        ))
        expense_id = cursor.lastrowid

    cursor.execute("""
    UPDATE purchase_requests
    SET status = 'approved',
        approved_by_id = ?,
        approved_by_name = ?,
        approved_at = CURRENT_TIMESTAMP,
        gm_notes = ?,
        expense_id = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (
        payload.approved_by_id, payload.approved_by_name, payload.gm_notes,
        expense_id, request_id
    ))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "expense_id": expense_id,
        "message": f"تمت موافقة المدير العام واعتماد طلب الشراء {req['request_number']} نهائياً للصرف ✅"
    }

@router.put("/{request_id}/reject")
def reject_purchase_request(request_id: int, payload: PurchaseRejectSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM purchase_requests WHERE id = ?", (request_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="طلب الشراء غير موجود")

    req = dict(row)
    cursor.execute("""
    UPDATE purchase_requests
    SET status = 'rejected',
        rejected_by_name = ?,
        rejected_at = CURRENT_TIMESTAMP,
        rejection_reason = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (payload.rejected_by_name, payload.rejection_reason, request_id))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"تم رفض طلب الشراء {req['request_number']}"
    }
