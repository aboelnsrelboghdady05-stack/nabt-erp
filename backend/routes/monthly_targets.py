from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from datetime import datetime

router = APIRouter(prefix="/api/monthly-targets", tags=["Employee Monthly Targets"])

class TargetCreateSchema(BaseModel):
    employee_id: int
    target_month: str  # Format: YYYY-MM e.g. '2026-11'
    target_title: str
    description: Optional[str] = None
    orders_target: Optional[int] = 0
    sales_target: Optional[float] = 0.0
    special_instructions: Optional[str] = None
    set_by_name: Optional[str] = "الإدارة (فيصل / ياسر)"
    set_by_role: Optional[str] = "operations_manager"
    set_by_id: Optional[int] = None

class TargetUpdateSchema(BaseModel):
    target_title: Optional[str] = None
    description: Optional[str] = None
    orders_target: Optional[int] = None
    sales_target: Optional[float] = None
    special_instructions: Optional[str] = None
    status: Optional[str] = None # in_progress, achieved, exceeded, needs_improvement
    manager_feedback: Optional[str] = None
    rating: Optional[int] = None

@router.get("")
def get_monthly_targets(
    month: Optional[str] = None,
    employee_id: Optional[int] = None,
    status: Optional[str] = None
):
    conn = get_db()
    cursor = conn.cursor()

    # Default to current month if not provided
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
    total_target_orders = 0
    total_achieved_orders = 0
    total_target_sales = 0.0
    total_achieved_sales = 0.0

    for row in rows:
        item = dict(row)
        emp_id = item.get("employee_id")
        t_month = item.get("target_month") or current_month

        # Calculate live stats from orders for this employee during the target month
        try:
            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(total_amount), 0.0)
                FROM orders
                WHERE florist_id = ?
                  AND created_at LIKE ?
                  AND status != 'cancelled'
            """, (emp_id, f"{t_month}%"))
            ord_res = cursor.fetchone()
            actual_orders = ord_res[0] if ord_res else 0
            actual_sales = float(ord_res[1]) if ord_res else 0.0
        except Exception:
            actual_orders = item.get("achieved_orders") or 0
            actual_sales = float(item.get("achieved_sales") or 0.0)

        # Merge live count if greater than manually recorded
        final_orders = max(actual_orders, item.get("achieved_orders") or 0)
        final_sales = max(actual_sales, float(item.get("achieved_sales") or 0.0))

        item["achieved_orders"] = final_orders
        item["achieved_sales"] = final_sales

        target_orders = item.get("orders_target") or 0
        target_sales = float(item.get("sales_target") or 0.0)

        item["orders_progress_pct"] = round((final_orders / target_orders * 100), 1) if target_orders > 0 else 0
        item["sales_progress_pct"] = round((final_sales / target_sales * 100), 1) if target_sales > 0 else 0

        # Auto status helper
        if item.get("orders_progress_pct", 0) >= 100:
            item["auto_status"] = "achieved"
        elif item.get("orders_progress_pct", 0) >= 50:
            item["auto_status"] = "in_progress"
        else:
            item["auto_status"] = item.get("status") or "in_progress"

        targets.append(item)

        total_target_orders += target_orders
        total_achieved_orders += final_orders
        total_target_sales += target_sales
        total_achieved_sales += final_sales

    # Month overview stats
    overall_progress_pct = round((total_achieved_orders / total_target_orders * 100), 1) if total_target_orders > 0 else 0

    stats = {
        "targets_count": len(targets),
        "total_target_orders": total_target_orders,
        "total_achieved_orders": total_achieved_orders,
        "total_target_sales": total_target_sales,
        "total_achieved_sales": total_achieved_sales,
        "overall_progress_pct": overall_progress_pct,
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
        raise HTTPException(status_code=400, detail="يرجى كتابة عنوان الهدف الشهري.")
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'in_progress', 0, 0.0)
    """, (
        payload.target_month.strip(),
        payload.employee_id,
        emp_name,
        emp_role,
        payload.target_title.strip(),
        payload.description.strip() if payload.description else "",
        payload.orders_target or 0,
        payload.sales_target or 0.0,
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
        "message": f"تم تحديد هدف شهر {payload.target_month} للموظف ({emp_name}) بنجاح 🎯",
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
        raise HTTPException(status_code=404, detail="الهدف المطلوب غير موجود.")

    updates = []
    params = []

    if payload.target_title is not None:
        updates.append("target_title = ?")
        params.append(payload.target_title.strip())
    if payload.description is not None:
        updates.append("description = ?")
        params.append(payload.description.strip())
    if payload.orders_target is not None:
        updates.append("orders_target = ?")
        params.append(payload.orders_target)
    if payload.sales_target is not None:
        updates.append("sales_target = ?")
        params.append(payload.sales_target)
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
    return {"success": True, "message": "تم تحديث الهدف بنجاح ✅"}

@router.delete("/{target_id}")
def delete_monthly_target(target_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, employee_name, target_title FROM employee_monthly_targets WHERE id = ?", (target_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="الهدف غير موجود.")

    cursor.execute("DELETE FROM employee_monthly_targets WHERE id = ?", (target_id,))
    conn.commit()
    conn.close()

    return {"success": True, "message": "تم حذف الهدف بنجاح 🗑️"}
