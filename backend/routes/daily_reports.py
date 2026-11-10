from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from datetime import datetime

router = APIRouter(prefix="/api/daily-reports", tags=["Employee Daily Reports"])

class DailyReportCreateSchema(BaseModel):
    employee_id: int
    report_date: Optional[str] = None  # Format: YYYY-MM-DD, defaults to today
    shift_type: Optional[str] = "morning"  # morning (صباحية), evening (مسائية), full (دوام كامل)
    work_hours: Optional[str] = None  # ساعات العمل e.g. "8 ساعات (من 9 ص إلى 5 م)"
    tasks_completed: str  # ما تم إنجازه خلال أوقات العمل
    orders_count: Optional[int] = 0  # عدد الطلبات المنسقة أو المنفذة
    challenges_or_notes: Optional[str] = None  # التحديات أو النواقص أو متطلبات العمل
    handover_notes: Optional[str] = None  # تسليم الوردية وملاحظات الزملاء

class DailyReportUpdateSchema(BaseModel):
    shift_type: Optional[str] = None
    work_hours: Optional[str] = None
    tasks_completed: Optional[str] = None
    orders_count: Optional[int] = None
    challenges_or_notes: Optional[str] = None
    handover_notes: Optional[str] = None

class DailyReportReviewSchema(BaseModel):
    manager_status: str = "reviewed"  # reviewed (تم الاطلاع والاعتماد), appreciated (شكر وتقدير متميز)
    manager_review: Optional[str] = None  # رد وملاحظات الإدارة
    reviewed_by: Optional[str] = "فيصل (مدير تشغيلي)"

@router.get("")
def get_daily_reports(
    date: Optional[str] = None,
    month: Optional[str] = None,
    employee_id: Optional[int] = None,
    status: Optional[str] = None
):
    conn = get_db()
    cursor = conn.cursor()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_month = datetime.now().strftime("%Y-%m")
    
    # 1. Fetch all active employees for status & pending calculations
    cursor.execute("SELECT id, name, role, phone, specialty FROM employees ORDER BY id ASC")
    all_employees = [dict(r) for r in cursor.fetchall()]
    
    # 2. Build report query filters
    where_clauses = []
    params = []
    
    target_date = None
    if date and date != "all":
        target_date = date
        where_clauses.append("r.report_date = ?")
        params.append(date)
    elif month:
        where_clauses.append("r.report_date LIKE ?")
        params.append(f"{month}%")
    elif not date and not month:
        # Default to today
        target_date = today_str
        where_clauses.append("r.report_date = ?")
        params.append(today_str)
        
    if employee_id:
        where_clauses.append("r.employee_id = ?")
        params.append(employee_id)
        
    if status and status != "all":
        where_clauses.append("r.manager_status = ?")
        params.append(status)
        
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    
    query = f"""
    SELECT r.*,
           e.name as employee_name,
           e.role as employee_role,
           e.specialty as employee_specialty,
           e.phone as employee_phone
    FROM employee_daily_reports r
    JOIN employees e ON r.employee_id = e.id
    {where_sql}
    ORDER BY r.report_date DESC, r.created_at DESC
    """
    
    cursor.execute(query, params)
    reports = [dict(r) for r in cursor.fetchall()]
    
    # Calculate stats for the selected date (or today)
    check_date = target_date or today_str
    submitted_ids = {r["employee_id"] for r in reports if r.get("report_date") == check_date}
    pending_employees = [emp for emp in all_employees if emp["id"] not in submitted_ids]
    
    total_orders_reported = sum(r.get("orders_count", 0) or 0 for r in reports)
    reviewed_count = sum(1 for r in reports if r.get("manager_status") in ("reviewed", "appreciated"))
    
    stats = {
        "today_date": today_str,
        "selected_date": check_date,
        "total_reports": len(reports),
        "total_employees": len(all_employees),
        "submitted_count": len(submitted_ids),
        "pending_count": len(pending_employees),
        "pending_employees": pending_employees,
        "total_orders_reported": total_orders_reported,
        "reviewed_count": reviewed_count
    }
    
    conn.close()
    return {
        "success": True,
        "reports": reports,
        "stats": stats,
        "employees": all_employees
    }

@router.get("/suggest-orders-count")
def suggest_orders_count(employee_id: int, date: Optional[str] = None):
    """
    اقترح عدد الطلبات المنسقة أو المنجزة لهذا الموظف في تاريخ محدد من جدول الطلبات
    """
    conn = get_db()
    cursor = conn.cursor()
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute("""
    SELECT COUNT(*) as cnt, COALESCE(SUM(total_amount), 0) as total_val
    FROM orders
    WHERE florist_id = ? AND delivery_date = ?
    """, (employee_id, target_date))
    
    row = cursor.fetchone()
    count_val = dict(row)["cnt"] if row else 0
    total_val = dict(row)["total_val"] if row else 0.0
    
    conn.close()
    return {
        "success": True,
        "employee_id": employee_id,
        "date": target_date,
        "suggested_orders_count": count_val,
        "orders_total_amount": total_val
    }

@router.post("")
def submit_daily_report(payload: DailyReportCreateSchema):
    """
    كتابة أو تعديل التقرير اليومي للموظف
    """
    conn = get_db()
    cursor = conn.cursor()
    
    rep_date = payload.report_date or datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Check employee exists
    cursor.execute("SELECT id, name, role FROM employees WHERE id = ?", (payload.employee_id,))
    emp = cursor.fetchone()
    if not emp:
        conn.close()
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    emp_name = dict(emp)["name"]
    
    # Check if a report already exists for this employee on this date
    cursor.execute("""
    SELECT id, manager_status FROM employee_daily_reports
    WHERE employee_id = ? AND report_date = ?
    """, (payload.employee_id, rep_date))
    existing = cursor.fetchone()
    
    if existing:
        rep_id = dict(existing)["id"]
        cursor.execute("""
        UPDATE employee_daily_reports
        SET shift_type = ?,
            work_hours = ?,
            tasks_completed = ?,
            orders_count = ?,
            challenges_or_notes = ?,
            handover_notes = ?,
            updated_at = ?
        WHERE id = ?
        """, (
            payload.shift_type or "morning",
            payload.work_hours or "ساعات العمل المعتادة",
            payload.tasks_completed,
            payload.orders_count or 0,
            payload.challenges_or_notes,
            payload.handover_notes,
            now_str,
            rep_id
        ))
        conn.commit()
        conn.close()
        return {
            "success": True,
            "report_id": rep_id,
            "message": f"تم تحديث التقرير اليومي للموظف ({emp_name}) ليوم {rep_date} بنجاح 📝"
        }
    else:
        cursor.execute("""
        INSERT INTO employee_daily_reports (
            employee_id, report_date, shift_type, work_hours,
            tasks_completed, orders_count, challenges_or_notes, handover_notes,
            manager_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (
            payload.employee_id,
            rep_date,
            payload.shift_type or "morning",
            payload.work_hours or "ساعات العمل المعتادة",
            payload.tasks_completed,
            payload.orders_count or 0,
            payload.challenges_or_notes,
            payload.handover_notes,
            now_str,
            now_str
        ))
        rep_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {
            "success": True,
            "report_id": rep_id,
            "message": f"تم تسجيل التقرير اليومي للموظف ({emp_name}) ليوم {rep_date} بنجاح ✨"
        }

@router.put("/{report_id}")
def update_daily_report(report_id: int, payload: DailyReportUpdateSchema):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM employee_daily_reports WHERE id = ?", (report_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="التقرير اليومي غير موجود")
        
    updates = []
    params = []
    
    if payload.shift_type is not None:
        updates.append("shift_type = ?")
        params.append(payload.shift_type)
    if payload.work_hours is not None:
        updates.append("work_hours = ?")
        params.append(payload.work_hours)
    if payload.tasks_completed is not None:
        updates.append("tasks_completed = ?")
        params.append(payload.tasks_completed)
    if payload.orders_count is not None:
        updates.append("orders_count = ?")
        params.append(payload.orders_count)
    if payload.challenges_or_notes is not None:
        updates.append("challenges_or_notes = ?")
        params.append(payload.challenges_or_notes)
    if payload.handover_notes is not None:
        updates.append("handover_notes = ?")
        params.append(payload.handover_notes)
        
    if updates:
        updates.append("updated_at = ?")
        params.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        params.append(report_id)
        
        cursor.execute(f"UPDATE employee_daily_reports SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        
    conn.close()
    return {"success": True, "message": "تم تحديث التقرير بنجاح"}

@router.post("/{report_id}/review")
def review_daily_report(report_id: int, payload: DailyReportReviewSchema):
    """
    اطلاع واعتماد الإدارة على التقرير اليومي وإضافة تعليق أو شكر
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT r.id, e.name as emp_name, r.report_date
    FROM employee_daily_reports r
    JOIN employees e ON r.employee_id = e.id
    WHERE r.id = ?
    """, (report_id,))
    report = cursor.fetchone()
    if not report:
        conn.close()
        raise HTTPException(status_code=404, detail="التقرير غير موجود")
        
    rep = dict(report)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
    UPDATE employee_daily_reports
    SET manager_status = ?,
        manager_review = ?,
        reviewed_by = ?,
        reviewed_at = ?,
        updated_at = ?
    WHERE id = ?
    """, (
        payload.manager_status or "reviewed",
        payload.manager_review or "تم الاطلاع والاعتماد من قبل الإدارة.",
        payload.reviewed_by or "فيصل (مدير تشغيلي)",
        now_str,
        now_str,
        report_id
    ))
    conn.commit()
    conn.close()
    
    status_label = "شكر وتقدير 👏" if payload.manager_status == "appreciated" else "تم الاعتماد والاطلاع ✅"
    return {
        "success": True,
        "message": f"تم اعتماد تقرير ({rep['emp_name']}) ليوم {rep['report_date']} ({status_label})"
    }

@router.delete("/{report_id}")
def delete_daily_report(report_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM employee_daily_reports WHERE id = ?", (report_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="التقرير غير موجود")
        
    cursor.execute("DELETE FROM employee_daily_reports WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم حذف التقرير اليومي بنجاح"}
