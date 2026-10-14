from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from datetime import date, datetime

router = APIRouter(prefix="/api/employees", tags=["Employees & Leaves"])

ARABIC_WEEKDAYS = {
    0: "الاثنين",
    1: "الثلاثاء",
    2: "الأربعاء",
    3: "الخميس",
    4: "الجمعة",
    5: "السبت",
    6: "الأحد"
}

def normalize_day_name(day_str: Optional[str]) -> str:
    if not day_str:
        return ""
    d = day_str.strip().replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه")
    return d

def get_arabic_weekday_name(target_date: date) -> str:
    return ARABIC_WEEKDAYS.get(target_date.weekday(), "")

def verify_leave_manager_access(username: Optional[str] = None, role: Optional[str] = None):
    """
    التحقق من صلاحية إدارة الموظفين والإجازات:
    محصورة على المسؤولين: نادر (مدير الفرع)، فيصل (مدير تشغيلي)، ياسر (المدير العام)، أو أدوار الإدارة.
    """
    u = (username or "").strip().lower()
    r = (role or "").strip().lower()
    is_nader = "nader" in u or "نادر" in u
    is_faisal = "faisal" in u or "فيصل" in u
    is_yasser = "yasser" in u or "ياسر" in u
    is_manager = r in ["branch_manager", "operations_manager", "general_manager", "admin", "manager"]
    if not (is_nader or is_faisal or is_yasser or is_manager):
        raise HTTPException(
            status_code=403, 
            detail="عذراً! هذه الصلاحية محصورة على مسؤولي النظام فقط (نادر، فيصل، ياسر)."
        )

def check_employee_availability_on_date(cursor, employee_id: int, target_date_str: Optional[str] = None) -> tuple[bool, str]:
    """
    التحقق الصارم من توفر الموظف/المنسق في تاريخ محدد:
    1. فحص يوم الراحة الأسبوعية (مثال: إذا كان إجازته الثلاثاء فلا يمكن إسناد طلب له في يوم الثلاثاء).
    2. فحص الإجازات المسجلة المجدولة والنشطة في جدول employee_leaves.
    """
    if not target_date_str:
        target_dt = date.today()
        target_date_str = target_dt.strftime("%Y-%m-%d")
    else:
        try:
            target_dt = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except Exception:
            target_dt = date.today()
            target_date_str = target_dt.strftime("%Y-%m-%d")

    target_day_name = get_arabic_weekday_name(target_dt)

    cursor.execute("SELECT id, name, weekly_off_day, status, role FROM employees WHERE id = ?", (employee_id,))
    emp = cursor.fetchone()
    if not emp:
        return False, "الموظف غير مسجل"

    emp_name = emp["name"]
    weekly_off = emp["weekly_off_day"] or "الثلاثاء"

    # 1. فحص الراحة الأسبوعية
    if normalize_day_name(weekly_off) == normalize_day_name(target_day_name):
        return False, f"يوم ({target_day_name}) هو يوم الراحة الأسبوعية للموظف ({emp_name}). لا يمكن إسناد طلبات له في هذا اليوم."

    # 2. فحص الإجازات الرسمية المسجلة
    cursor.execute("""
    SELECT leave_type, start_date, end_date, reason FROM employee_leaves
    WHERE employee_id = ? AND start_date <= ? AND end_date >= ? AND status = 'active'
    LIMIT 1
    """, (employee_id, target_date_str, target_date_str))
    leave_row = cursor.fetchone()
    if leave_row:
        return False, f"الموظف ({emp_name}) في ({leave_row['leave_type']}) حتى {leave_row['end_date']}."

    return True, "متاح في المحل"

def sync_leaves_with_employee_status(cursor):
    """
    مزامنة حالة جميع الموظفين مع تاريخ اليوم:
    - إذا كان اليوم يقع ضمن فترة إجازة نشطة أو يصادف يوم راحته الأسبوعية، تصبح حالته 'on_leave'.
    - إذا لم ينطبق أي منهما، تعود حالته إلى 'on_duty' (في المحل).
    """
    today_dt = date.today()
    today_str = today_dt.strftime("%Y-%m-%d")
    today_day_name = get_arabic_weekday_name(today_dt)

    # الموظفون أصحاب الإجازات النشطة اليوم
    cursor.execute("""
    SELECT DISTINCT employee_id FROM employee_leaves
    WHERE start_date <= ? AND end_date >= ? AND status = 'active'
    """, (today_str, today_str))
    on_leave_ids = set([row[0] for row in cursor.fetchall()])

    # الموظفون الذين يصادف يوم راحتهم الأسبوعية اليوم
    cursor.execute("SELECT id, weekly_off_day FROM employees")
    for row in cursor.fetchall():
        w_off = row["weekly_off_day"]
        if w_off and normalize_day_name(w_off) == normalize_day_name(today_day_name):
            on_leave_ids.add(row["id"])

    if on_leave_ids:
        placeholders = ','.join('?' for _ in on_leave_ids)
        cursor.execute(f"UPDATE employees SET status = 'on_leave' WHERE id IN ({placeholders})", list(on_leave_ids))
        cursor.execute(f"UPDATE employees SET status = 'on_duty' WHERE status = 'on_leave' AND id NOT IN ({placeholders})", list(on_leave_ids))
    else:
        cursor.execute("UPDATE employees SET status = 'on_duty' WHERE status = 'on_leave'")

def get_best_available_florist(cursor, target_date: Optional[str] = None) -> Optional[dict]:
    """
    اختيار أفضل منسق متاح لتجهيز الطلب:
    - يستبعد تماماً أي منسق في إجازة أو يصادف تاريخ التسليم يوم راحته الأسبوعية.
    - يختار المنسق صاحب أقل عدد طلبات نشطة قيد التجهيز.
    """
    if not target_date:
        target_date = date.today().strftime("%Y-%m-%d")

    sync_leaves_with_employee_status(cursor)

    cursor.execute("""
    SELECT e.*,
           (SELECT COUNT(*) FROM orders WHERE florist_id = e.id AND status IN ('new', 'preparing')) as current_workload
    FROM employees e
    WHERE e.role = 'florist'
    ORDER BY current_workload ASC, e.id ASC
    """)
    florists = [dict(row) for row in cursor.fetchall()]

    for f in florists:
        is_avail, _ = check_employee_availability_on_date(cursor, f["id"], target_date)
        if is_avail:
            return f

    return None

class EmployeeCreateSchema(BaseModel):
    name: str
    phone: str
    role: str = "florist"
    username: Optional[str] = None
    password: Optional[str] = "123456"
    specialty: Optional[str] = "تنسيق ورد وتغليف فاخر"
    status: Optional[str] = "on_duty"
    weekly_off_day: Optional[str] = "الثلاثاء"
    notes: Optional[str] = None
    requester_username: Optional[str] = None
    requester_role: Optional[str] = None

class EmployeeStatusSchema(BaseModel):
    status: str

class LeaveCreateSchema(BaseModel):
    employee_id: int
    leave_type: str = "إجازة سنوية"
    start_date: str
    end_date: str
    reason: Optional[str] = None
    created_by_username: Optional[str] = None
    created_by_role: Optional[str] = None

class LeaveUpdateSchema(BaseModel):
    leave_type: str = "إجازة سنوية"
    start_date: str
    end_date: str
    reason: Optional[str] = None
    modified_by_username: Optional[str] = None
    modified_by_role: Optional[str] = None

class WeeklyOffUpdateSchema(BaseModel):
    weekly_off_day: str
    modified_by_username: Optional[str] = None
    modified_by_role: Optional[str] = None

class EmployeePhoneUpdateSchema(BaseModel):
    phone: str
    modified_by_username: Optional[str] = None
    modified_by_role: Optional[str] = None

@router.get("")
def get_employees(role: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    sync_leaves_with_employee_status(cursor)
    conn.commit()

    today_dt = date.today()
    today_day_name = get_arabic_weekday_name(today_dt)

    query = """
    SELECT e.*,
           (SELECT COUNT(*) FROM orders WHERE florist_id = e.id AND status IN ('new', 'preparing')) as current_preparing_orders,
           (SELECT COUNT(*) FROM orders WHERE florist_id = e.id AND status = 'delivered') as total_completed_orders,
           (SELECT leave_type || ' (حتى ' || end_date || ')' FROM employee_leaves WHERE employee_id = e.id AND start_date <= date('now') AND end_date >= date('now') AND status = 'active' LIMIT 1) as current_leave_info
    FROM employees e
    WHERE 1=1
    """
    params = []
    if role and role != "all":
        query += " AND e.role = ?"
        params.append(role)

    query += " ORDER BY e.role ASC, e.id ASC"
    cursor.execute(query, params)
    employees = [dict(row) for row in cursor.fetchall()]

    for emp in employees:
        w_off = emp.get("weekly_off_day") or "الثلاثاء"
        emp["is_today_weekly_off"] = (normalize_day_name(w_off) == normalize_day_name(today_day_name))
        emp["today_day_name"] = today_day_name

    conn.close()
    return employees

@router.get("/available-florists")
def get_available_florists(delivery_date: Optional[str] = None):
    """
    إرجاع المنسقين المتواجدين في المحل مع فحص فوري ليوم الراحة وتاريخ الإجازة
    """
    conn = get_db()
    cursor = conn.cursor()
    sync_leaves_with_employee_status(cursor)
    conn.commit()

    target_date = delivery_date or date.today().strftime("%Y-%m-%d")

    cursor.execute("""
    SELECT e.*,
           (SELECT COUNT(*) FROM orders WHERE florist_id = e.id AND status IN ('new', 'preparing')) as current_workload
    FROM employees e
    WHERE e.role = 'florist'
    ORDER BY current_workload ASC
    """)
    florists = [dict(row) for row in cursor.fetchall()]

    for f in florists:
        is_avail, reason = check_employee_availability_on_date(cursor, f["id"], target_date)
        f["is_available_on_date"] = is_avail
        f["unavailability_reason"] = reason if not is_avail else None

    conn.close()
    return florists

@router.post("")
def create_employee(payload: EmployeeCreateSchema):
    """
    إضافة موظف جديد وإنشاء حساب تسجيل دخول له:
    مصرح فقط للمسؤولين (نادر، فيصل، ياسر).
    """
    verify_leave_manager_access(payload.requester_username, payload.requester_role)

    conn = get_db()
    cursor = conn.cursor()

    clean_username = (payload.username or "").strip().lower()
    if not clean_username:
        clean_username = f"emp_{payload.phone.strip()[-4:]}"
    clean_username = clean_username.replace(" ", "_")

    password = (payload.password or "123456").strip()

    cursor.execute("SELECT id FROM employees WHERE phone = ? OR LOWER(username) = ?", (payload.phone.strip(), clean_username))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="الموظف مسجل مسبقاً بنفس رقم الجوال أو اسم المستخدم. يرجى اختيار اسم مستخدم ورقم مختلفين.")

    try:
        cursor.execute("""
        INSERT INTO employees (name, phone, role, username, password, specialty, status, weekly_off_day, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.name.strip(),
            payload.phone.strip(),
            payload.role,
            clean_username,
            password,
            payload.specialty.strip() if payload.specialty else "تنسيق ورد وتغليف فاخر",
            payload.status or 'on_duty',
            payload.weekly_off_day or 'الثلاثاء',
            payload.notes
        ))
        emp_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"حدث خطأ أثناء حفظ الموظف: {str(e)}")

    conn.close()
    return {
        "success": True, 
        "id": emp_id,
        "username": clean_username,
        "password": password,
        "message": f"تم إنشاء حساب الموظف ({payload.name}) بنجاح! اسم المستخدم: {clean_username}"
    }

@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int, 
    requester_username: Optional[str] = Query(None), 
    requester_role: Optional[str] = Query(None)
):
    """
    حذف موظف من النظام:
    مصرح للمسؤولين (نادر، فيصل، ياسر).
    يمنع حذف الحسابات الإدارية الأساسية.
    """
    verify_leave_manager_access(requester_username, requester_role)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, username, role FROM employees WHERE id = ?", (employee_id,))
    emp = cursor.fetchone()
    if not emp:
        conn.close()
        raise HTTPException(status_code=404, detail="الموظف غير موجود")

    emp_username = (emp["username"] or "").lower()
    emp_name = emp["name"]

    if emp_username in ["yasser", "faisal", "nader"] or employee_id in [1, 2, 3] or "مدير عام" in emp_name:
        conn.close()
        raise HTTPException(status_code=400, detail="عذراً! لا يمكن حذف حسابات الإدارة الأساسية (ياسر، فيصل، نادر).")

    try:
        cursor.execute("DELETE FROM employee_leaves WHERE employee_id = ?", (employee_id,))
        cursor.execute("UPDATE orders SET florist_id = NULL WHERE florist_id = ?", (employee_id,))
        cursor.execute("UPDATE orders SET previous_florist_id = NULL WHERE previous_florist_id = ?", (employee_id,))
        cursor.execute("UPDATE creative_tasks SET assigned_to_id = NULL WHERE assigned_to_id = ?", (employee_id,))
        cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء حذف الموظف: {str(e)}")

    conn.close()
    return {
        "success": True, 
        "message": f"تم حذف الموظف ({emp_name}) وكافة بياناته بنجاح."
    }

@router.put("/{employee_id}/status")
def update_employee_status(employee_id: int, payload: EmployeeStatusSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("UPDATE employees SET status = ? WHERE id = ?", (payload.status, employee_id))
    conn.commit()
    conn.close()
    return {"success": True, "status": payload.status}

@router.put("/{employee_id}/weekly-off")
def update_weekly_off_day(employee_id: int, payload: WeeklyOffUpdateSchema):
    """
    تحديث يوم الراحة الأسبوعية للموظف:
    مصرح للمسؤولين فقط (مدير الفرع نادر أو مدراء الإدارة).
    """
    verify_leave_manager_access(payload.modified_by_username, payload.modified_by_role)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM employees WHERE id = ?", (employee_id,))
    emp = cursor.fetchone()
    if not emp:
        conn.close()
        raise HTTPException(status_code=404, detail="الموظف غير موجود")

    clean_day = payload.weekly_off_day.strip()
    cursor.execute("UPDATE employees SET weekly_off_day = ? WHERE id = ?", (clean_day, employee_id))

    sync_leaves_with_employee_status(cursor)
    conn.commit()
    conn.close()

    return {
        "success": True,
        "weekly_off_day": clean_day,
        "message": f"تم تحديد يوم ({clean_day}) كيوم راحة أسبوعية للموظف ({emp['name']}) بنجاح. لن يتم إسناد أي طلبات له في هذا اليوم."
    }

@router.put("/{employee_id}/phone")
def update_employee_phone(employee_id: int, payload: EmployeePhoneUpdateSchema):
    verify_leave_manager_access(payload.modified_by_username, payload.modified_by_role)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM employees WHERE id = ?", (employee_id,))
    emp = cursor.fetchone()
    if not emp:
        conn.close()
        raise HTTPException(status_code=404, detail="الموظف غير موجود")

    clean_phone = payload.phone.strip()
    cursor.execute("UPDATE employees SET phone = ? WHERE id = ?", (clean_phone, employee_id))
    conn.commit()
    conn.close()

    return {
        "success": True, 
        "phone": clean_phone, 
        "message": f"تم تحديث رقم جوال الموظف ({emp['name']}) بنجاح إلى ({clean_phone})."
    }

@router.get("/leaves")
def get_leaves():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT l.*, e.name as employee_name, e.role as employee_role, e.phone as employee_phone, e.weekly_off_day
    FROM employee_leaves l
    JOIN employees e ON l.employee_id = e.id
    ORDER BY l.start_date DESC, l.id DESC
    """)
    leaves = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return leaves

@router.post("/leaves")
def record_employee_leave(payload: LeaveCreateSchema):
    """
    تسجيل إجازة جديدة:
    مصرح فقط للمسؤولين (مدير الفرع نادر أو مدراء الإدارة).
    """
    verify_leave_manager_access(payload.created_by_username, payload.created_by_role)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT name, role FROM employees WHERE id = ?", (payload.employee_id,))
    emp = cursor.fetchone()
    if not emp:
        conn.close()
        raise HTTPException(status_code=404, detail="الموظف غير موجود")

    cursor.execute("""
    INSERT INTO employee_leaves (employee_id, leave_type, start_date, end_date, reason, status)
    VALUES (?, ?, ?, ?, ?, 'active')
    """, (payload.employee_id, payload.leave_type, payload.start_date, payload.end_date, payload.reason))
    leave_id = cursor.lastrowid

    sync_leaves_with_employee_status(cursor)

    conn.commit()
    conn.close()

    return {
        "success": True,
        "leave_id": leave_id,
        "message": f"تم تسجيل إجازة {payload.leave_type} للموظف ({emp['name']}). لن يتم إسناد أي طلبات له أثناء فترة الإجازة."
    }

@router.put("/leaves/{leave_id}")
def update_employee_leave(leave_id: int, payload: LeaveUpdateSchema):
    """
    تعديل إجازة مسجلة:
    مخصص للمسؤولين وتحديداً يوزر نادر (مدير الفرع).
    """
    verify_leave_manager_access(payload.modified_by_username, payload.modified_by_role)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT l.*, e.name as employee_name FROM employee_leaves l JOIN employees e ON l.employee_id = e.id WHERE l.id = ?", (leave_id,))
    leave = cursor.fetchone()
    if not leave:
        conn.close()
        raise HTTPException(status_code=404, detail="الإجازة غير موجودة")

    cursor.execute("""
    UPDATE employee_leaves 
    SET leave_type = ?, start_date = ?, end_date = ?, reason = ?
    WHERE id = ?
    """, (payload.leave_type, payload.start_date, payload.end_date, payload.reason, leave_id))

    sync_leaves_with_employee_status(cursor)
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"تم تعديل إجازة ({leave['employee_name']}) بنجاح بواسطة المدير نادر / الإدارة."
    }

@router.delete("/leaves/{leave_id}")
def cancel_leave(
    leave_id: int, 
    user_name: Optional[str] = Query(None),
    user_role: Optional[str] = Query(None)
):
    """
    إلغاء إجازة:
    مخصص للمسؤولين وتحديداً يوزر نادر أو مدراء الإدارة.
    """
    verify_leave_manager_access(user_name, user_role)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT employee_id FROM employee_leaves WHERE id = ?", (leave_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="الإجازة غير موجودة")

    cursor.execute("DELETE FROM employee_leaves WHERE id = ?", (leave_id,))
    sync_leaves_with_employee_status(cursor)

    conn.commit()
    conn.close()
    return {"success": True, "message": "تم إلغاء الإجازة وعاد الموظف إلى حالة العمل (في المحل)."}
