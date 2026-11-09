from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from datetime import datetime

router = APIRouter(prefix="/api/monthly-targets", tags=["Employee Monthly Tasks & Goals"])

class TargetCreateSchema(BaseModel):
    employee_id: int
    target_month: str  # Format: YYYY-MM e.g. '2026-11'
    target_title: str
    description: Optional[str] = ""  # النص الكامل للمهام والأهداف المكتوبة
    special_instructions: Optional[str] = None
    set_by_name: Optional[str] = "الإدارة (فيصل / ياسر)"
    set_by_role: Optional[str] = "operations_manager"
    set_by_id: Optional[int] = None
    priority: Optional[str] = "normal"  # normal, urgent, mandatory

class TargetUpdateSchema(BaseModel):
    target_title: Optional[str] = None
    description: Optional[str] = None
    special_instructions: Optional[str] = None
    status: Optional[str] = None  # in_progress, completed, reviewed
    manager_feedback: Optional[str] = None
    rating: Optional[int] = None
    priority: Optional[str] = None

class TargetStatusSchema(BaseModel):
    status: str  # in_progress, completed
    notes: Optional[str] = None

@router.get("")
def get_monthly_targets(
    month: Optional[str] = None,
    employee_id: Optional[int] = None,
    status: Optional[str] = None
):
    conn = get_db()
    cursor = conn.cursor()

    current_month = month or datetime.now().strftime("%Y-%m")

    query = """
    SELECT t.*,
           e.phone as employee_phone,
           e.specialty as employee_specialty
    FROM employee_monthly_targets t
    LEFT JOIN employees e ON t.employee_id = e.id
    WHERE 1=1
    """
    params = []

    if month and month != "all":
        query += " AND t.target_month = ?"
        params.append(month)
    if employee_id:
        query += " AND t.employee_id = ?"
        params.append(employee_id)
    if status and status != "all":
        query += " AND t.status = ?"
        params.append(status)

    query += " ORDER BY t.id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()

    targets = []
    in_progress_count = 0
    completed_count = 0
    reviewed_count = 0

    for row in rows:
        item = dict(row)
        st = item.get("status") or "in_progress"
        if st in ("completed", "achieved", "exceeded"):
            completed_count += 1
        elif st == "reviewed":
            reviewed_count += 1
        else:
            in_progress_count += 1

        targets.append(item)

    stats = {
        "total_tasks": len(targets),
        "in_progress": in_progress_count,
        "completed": completed_count,
        "reviewed": reviewed_count,
        "active_month": current_month
    }

    conn.close()
    return {
        "targets": targets,
        "stats": stats
    }

@router.get("/employees")
def get_target_employees():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, role, phone, specialty
        FROM employees
        WHERE status = 'active' OR status IS NULL
        ORDER BY role DESC, name ASC
    """)
    emps = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"employees": emps}

@router.post("")
def create_monthly_target(payload: TargetCreateSchema):
    if not payload.target_title or not payload.target_title.strip():
        raise HTTPException(status_code=400, detail="يرجى كتابة عنوان الهدف / المهمة.")
    if not payload.target_month or not payload.target_month.strip():
        raise HTTPException(status_code=400, detail="يرجى تحديد الشهر المستهدف (مثال: 2026-11).")

    conn = get_db()
    cursor = conn.cursor()

    # Get employee details
    cursor.execute("SELECT id, name, role FROM employees WHERE id = ?", (payload.employee_id,))
    emp = cursor.fetchone()
    if not emp:
        conn.close()
        raise HTTPException(status_code=404, detail="الموظف المختار غير مسجل في النظام.")

    emp_name = emp["name"] if isinstance(emp, dict) or hasattr(emp, "__getitem__") else emp[1]
    emp_role = emp["role"] if isinstance(emp, dict) or hasattr(emp, "__getitem__") else emp[2]

    cursor.execute("""
        INSERT INTO employee_monthly_targets (
            target_month, employee_id, employee_name, employee_role,
            target_title, description, orders_target, sales_target,
            special_instructions, set_by_name, set_by_role, set_by_id,
            status, achieved_orders, achieved_sales
        ) VALUES (?, ?, ?, ?, ?, ?, 0, 0.0, ?, ?, ?, ?, 'in_progress', 0, 0.0)
    """, (
        payload.target_month.strip(),
        payload.employee_id,
        emp_name,
        emp_role,
        payload.target_title.strip(),
        payload.description.strip() if payload.description else "",
        payload.special_instructions.strip() if payload.special_instructions else "",
        payload.set_by_name or "الإدارة (فيصل / ياسر)",
        payload.set_by_role or "operations_manager",
        payload.set_by_id
    ))

    target_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"تم حفظ وإسناد مهام شهر {payload.target_month} للموظف ({emp_name}) بنجاح 📝✅",
        "target_id": target_id
    }

@router.put("/{target_id}")
def update_monthly_target(target_id: int, payload: TargetUpdateSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM employee_monthly_targets WHERE id = ?", (target_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="المهمة / الهدف غير موجود.")

    updates = []
    params = []

    if payload.target_title is not None:
        updates.append("target_title = ?")
        params.append(payload.target_title.strip())
    if payload.description is not None:
        updates.append("description = ?")
        params.append(payload.description.strip())
    if payload.special_instructions is not None:
        updates.append("special_instructions = ?")
        params.append(payload.special_instructions.strip())
    if payload.status is not None:
        updates.append("status = ?")
        params.append(payload.status)
    if payload.manager_feedback is not None:
        updates.append("manager_feedback = ?")
        params.append(payload.manager_feedback.strip())
    if payload.rating is not None:
        updates.append("rating = ?")
        params.append(payload.rating)

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        query = f"UPDATE employee_monthly_targets SET {', '.join(updates)} WHERE id = ?"
        params.append(target_id)
        cursor.execute(query, params)
        conn.commit()

    conn.close()
    return {"success": True, "message": "تم تحديث المهمة بنجاح ✅"}

@router.put("/{target_id}/status")
def toggle_target_status(target_id: int, payload: TargetStatusSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, employee_name, target_title FROM employee_monthly_targets WHERE id = ?", (target_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="المهمة غير موجودة.")

    cursor.execute("""
        UPDATE employee_monthly_targets
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (payload.status, target_id))
    conn.commit()
    conn.close()

    msg = "تم تحديث حالة المهمة إلى مكتملة بنجاح ✅" if payload.status == "completed" else "تم إعادة المهمة إلى قيد التنفيذ ⏳"
    return {"success": True, "message": msg}

@router.delete("/{target_id}")
def delete_monthly_target(target_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, employee_name, target_title FROM employee_monthly_targets WHERE id = ?", (target_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="المهمة غير موجودة.")

    cursor.execute("DELETE FROM employee_monthly_targets WHERE id = ?", (target_id,))
    conn.commit()
    conn.close()

    return {"success": True, "message": "تم حذف المهمة بنجاح 🗑️"}
