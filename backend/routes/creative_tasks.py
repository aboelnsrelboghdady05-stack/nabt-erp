from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from datetime import datetime, date

router = APIRouter(prefix="/api/creative-tasks", tags=["Creative Projects Tasks"])

class CreativeTaskCreateSchema(BaseModel):
    details: str
    due_date: str
    due_time: Optional[str] = None
    assigned_to_id: int
    created_by_name: Optional[str] = "عضو الفريق"
    created_by_id: Optional[int] = None
    notes: Optional[str] = None

class CreativeTaskStatusSchema(BaseModel):
    status: str # pending, in_progress, completed, cancelled
    notes: Optional[str] = None

@router.get("")
def get_creative_tasks(status: Optional[str] = None, assigned_to_id: Optional[int] = None):
    conn = get_db()
    cursor = conn.cursor()

    query = """
    SELECT ct.*,
           e.phone as assignee_phone,
           e.role as assignee_role,
           e.specialty as assignee_specialty
    FROM creative_tasks ct
    LEFT JOIN employees e ON ct.assigned_to_id = e.id
    WHERE 1=1
    """
    params = []
    if status and status != "all":
        query += " AND ct.status = ?"
        params.append(status)
    if assigned_to_id:
        query += " AND ct.assigned_to_id = ?"
        params.append(assigned_to_id)

    query += " ORDER BY ct.id DESC"
    cursor.execute(query, params)
    tasks = [dict(row) for row in cursor.fetchall()]

    # Stats
    cursor.execute("SELECT status, COUNT(*) FROM creative_tasks GROUP BY status")
    counts = dict(cursor.fetchall())
    stats = {
        "total": sum(counts.values()),
        "pending": counts.get("pending", 0),
        "in_progress": counts.get("in_progress", 0),
        "completed": counts.get("completed", 0),
        "cancelled": counts.get("cancelled", 0)
    }

    conn.close()
    return {
        "tasks": tasks,
        "stats": stats
    }

@router.post("")
def create_creative_task(payload: CreativeTaskCreateSchema):
    if not payload.details or not payload.details.strip():
        raise HTTPException(status_code=400, detail="يرجى كتابة تفاصيل الطلب الإبداعي.")
    if not payload.due_date or not payload.due_date.strip():
        raise HTTPException(status_code=400, detail="يرجى تحديد موعد التسليم.")

    conn = get_db()
    cursor = conn.cursor()

    # Get assignee details
    cursor.execute("SELECT id, name, phone, role FROM employees WHERE id = ?", (payload.assigned_to_id,))
    emp = cursor.fetchone()
    if not emp:
        conn.close()
        raise HTTPException(status_code=404, detail="الموظف المختار غير موجود في السيستم.")

    assignee_name = emp["name"]
    assignee_phone = emp["phone"] or ""

    # Generate task number CRT-0001
    cursor.execute("SELECT COALESCE(MAX(id), 0) FROM creative_tasks")
    next_id = cursor.fetchone()[0] + 1
    task_number = f"CRT-{next_id:04d}"

    due_time_str = payload.due_time.strip() if payload.due_time else ""
    created_by_name = (payload.created_by_name or "عضو الفريق").strip()

    cursor.execute("""
    INSERT INTO creative_tasks (
        task_number, details, due_date, due_time,
        assigned_to_id, assigned_to_name, assigned_to_phone,
        created_by_id, created_by_name, status, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (
        task_number, payload.details.strip(), payload.due_date.strip(), due_time_str,
        payload.assigned_to_id, assignee_name, assignee_phone,
        payload.created_by_id, created_by_name, payload.notes
    ))
    task_id = cursor.lastrowid
    conn.commit()

    # Build WhatsApp notification message
    time_part = f" (الساعة: {due_time_str})" if due_time_str else ""
    wa_message = (
        f"🎨 مهمة جديدة ضمن مشاريع نبت الإبداعية\n"
        f"مرحباً {assignee_name} ✨\n"
        f"تم إسناد مهمة إبداعية جديدة إليك من ({created_by_name}):\n"
        f"• رقم المهمة: #{task_number}\n"
        f"• تفاصيل الطلب: {payload.details.strip()}\n"
        f"• موعد التسليم: {payload.due_date.strip()}{time_part}\n"
        f"نثق بلمساتك وذوقك الإبداعي! 🌸✨"
    )

    clean_phone = assignee_phone.replace("+", "").replace(" ", "").strip()
    if clean_phone.startswith("05"):
        clean_phone = "966" + clean_phone[1:]
    encoded_msg = wa_message.replace(" ", "%20").replace("\n", "%0A")
    wa_url = f"https://wa.me/{clean_phone}?text={encoded_msg}" if clean_phone else ""

    conn.close()

    return {
        "success": True,
        "task_id": task_id,
        "task_number": task_number,
        "assignee_name": assignee_name,
        "assignee_phone": assignee_phone,
        "wa_message": wa_message,
        "wa_url": wa_url,
        "message": f"تم إرسال المهمة الإبداعية رقم #{task_number} إلى ({assignee_name}) بنجاح!"
    }

@router.put("/{task_id}/status")
def update_creative_task_status(task_id: int, payload: CreativeTaskStatusSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, task_number, assigned_to_name FROM creative_tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        conn.close()
        raise HTTPException(status_code=404, detail="المهمة غير موجودة")

    completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if payload.status == "completed" else None

    if completed_at:
        cursor.execute("""
        UPDATE creative_tasks 
        SET status = ?, completed_at = ?, notes = COALESCE(?, notes), updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (payload.status, completed_at, payload.notes, task_id))
    else:
        cursor.execute("""
        UPDATE creative_tasks 
        SET status = ?, completed_at = NULL, notes = COALESCE(?, notes), updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (payload.status, payload.notes, task_id))

    conn.commit()
    conn.close()

    status_labels = {
        "pending": "قيد الانتظار ⏳",
        "in_progress": "قيد التنفيذ 🎨",
        "completed": "مكتملة بنجاح ✅",
        "cancelled": "ملغية ❌"
    }

    return {
        "success": True,
        "status": payload.status,
        "status_label": status_labels.get(payload.status, payload.status),
        "message": f"تم تحديث حالة المهمة #{task['task_number']} إلى ({status_labels.get(payload.status, payload.status)})"
    }

@router.delete("/{task_id}")
def delete_creative_task(task_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM creative_tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    return {"success": True, "message": "تم حذف المهمة الإبداعية بنجاح"}
