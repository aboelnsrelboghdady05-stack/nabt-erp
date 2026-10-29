from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db
from datetime import datetime, date
from routes.whatsapp import dispatch_via_gateway_if_configured

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

    # Look up General Manager (Yasser) dynamically
    cursor.execute("SELECT name, phone FROM employees WHERE role = 'general_manager' OR name LIKE '%ياسر%' LIMIT 1")
    gm_emp = cursor.fetchone()
    yasser_name = gm_emp['name'] if gm_emp else 'ياسر (المدير العام)'
    yasser_phone = gm_emp['phone'] if gm_emp else '0544338827'

    urgency_text = payload.urgency
    if urgency_text in ("urgent", "عاجل جداً اليوم"):
        urgency_text = "عاجل جداً اليوم ⚡"
    elif urgency_text in ("normal", "عادي غداً"):
        urgency_text = "عادي غداً ⏳"

    amt_str = f"{amt:,.2f} ريال" if amt > 0 else "غير محدد"

    # WhatsApp message to Yasser asking for approval/endorsement
    yasser_purchase_msg = (
        f"👑 إشعار طلب مشتريات جديد يحتاج تعميدك يا {yasser_name}!\n"
        f"تم رفع طلب مشتريات جديد بالنظام وبانتظار تعميدك واعتمادك:\n"
        f"• رقم الطلب: #{request_number}\n"
        f"• الصنف / المادة: {payload.item_name.strip()}\n"
        f"• التصنيف: {cat}\n"
        f"• الكمية: {qty}\n"
        f"• التكلفة التقديرية: {amt_str}\n"
        f"• درجة الأهمية: {urgency_text}\n"
        f"• مقدّم الطلب: {payload.requested_by_name} ({payload.requested_by_role})\n"
        f"• سبب الشراء: {payload.reason or 'لا توجد ملاحظات إضافية'}\n\n"
        f"يرجى الدخول على السيستم لمراجعة الطلب وتعميده والموافقة عليه 📝✨"
    )

    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status)
    VALUES (?, ?, 'outbound', 'purchase_alert', ?, 'delivered')
    """, (yasser_phone, yasser_name, yasser_purchase_msg))

    conn.commit()
    conn.close()

    # Dispatch WhatsApp to Yasser
    dispatch_via_gateway_if_configured(yasser_phone, yasser_purchase_msg)

    return {
        "success": True,
        "id": new_id,
        "request_number": request_number,
        "message": f"تم إنشاء طلب الشراء رقم {request_number} بنجاح، وتم إرسال إشعار تعميد للمدير العام (ياسر) بالواتساب 👑"
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

    # Notify General Manager (Yasser) of branch manager endorsement
    cursor.execute("SELECT name, phone FROM employees WHERE role = 'general_manager' OR name LIKE '%ياسر%' LIMIT 1")
    gm_emp = cursor.fetchone()
    yasser_name = gm_emp['name'] if gm_emp else 'ياسر (المدير العام)'
    yasser_phone = gm_emp['phone'] if gm_emp else '0544338827'

    amt_val = float(req.get('estimated_amount') or 0.0)
    amt_disp = f"{amt_val:,.2f} ريال" if amt_val > 0 else "غير محدد"

    yasser_endorsed_msg = (
        f"👑 إشعار تعميد طلب مشتريات يا {yasser_name}!\n"
        f"تم تعميد طلب الشراء #{req['request_number']} بواسطة ({payload.endorsed_by_name}) وبانتظار موافقتك النهائية وصرف المبلغ:\n"
        f"• الصنف: {req['item_name']}\n"
        f"• التكلفة التقديرية: {amt_disp}\n"
        f"• ملاحظات التعميد: {payload.endorsement_notes or 'تم التعميد والموافقة المبدئية بنجاح'}\n\n"
        f"الطلب متاح الآن في السيستم للاعتماد النهائي والصرف ✍️"
    )

    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status)
    VALUES (?, ?, 'outbound', 'purchase_alert', ?, 'delivered')
    """, (yasser_phone, yasser_name, yasser_endorsed_msg))

    conn.commit()
    conn.close()

    dispatch_via_gateway_if_configured(yasser_phone, yasser_endorsed_msg)

    return {
        "success": True,
        "message": f"تم تعميد طلب الشراء {req['request_number']} بنجاح وتم إشعار المدير العام (ياسر) بالواتساب للموافقة النهائية"
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

@router.delete("/{request_id}")
def delete_purchase_request(request_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM purchase_requests WHERE id = ?", (request_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="طلب الشراء غير موجود")

    req = dict(row)
    req_num = req.get("request_number") or f"#{request_id}"

    if req.get("expense_id"):
        try:
            cursor.execute("DELETE FROM expenses WHERE id = ?", (req["expense_id"],))
        except Exception:
            pass

    cursor.execute("DELETE FROM purchase_requests WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"تم حذف طلب الشراء {req_num} بنجاح"
    }
