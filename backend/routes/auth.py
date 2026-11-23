from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter(prefix="/api/auth", tags=["Authentication & Password Management"])

class LoginRequest(BaseModel):
    identifier: str  # username, phone, or name (e.g. 'yasser', '0544338827', 'ياسر')
    password: str

class ChangePasswordRequest(BaseModel):
    employee_id: int
    current_password: Optional[str] = None
    new_password: str

def normalize_digits(s: str) -> str:
    if not s:
        return ""
    eastern_arabic = "٠١٢٣٤٥٦٧٨٩"
    persian = "۰۱۲۳۴۵۶۷۸۹"
    for i in range(10):
        s = s.replace(eastern_arabic[i], str(i)).replace(persian[i], str(i))
    return s.strip()

@router.post("/login")
def login(payload: LoginRequest):
    identifier_raw = payload.identifier.strip()
    identifier = normalize_digits(identifier_raw)
    password = normalize_digits(payload.password.strip())

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Extract digits if user entered a phone number
        phone_digits = "".join(ch for ch in identifier if ch.isdigit())
        phone_like = f"%{phone_digits[-9:]}%" if len(phone_digits) >= 9 else None

        query = """
        SELECT id, name, username, phone, role, status, specialty, password
        FROM employees
        WHERE LOWER(username) = LOWER(?)
           OR LOWER(username) = LOWER(?)
           OR phone = ?
           OR phone = ?
           OR name = ?
           OR name LIKE ?
        """
        params = [
            identifier, identifier_raw,
            identifier, phone_digits,
            identifier_raw, f"%{identifier_raw}%"
        ]

        if phone_like:
            query += " OR phone LIKE ?"
            params.append(phone_like)

        query += " LIMIT 1"
        cursor.execute(query, params)
        emp = cursor.fetchone()
    finally:
        conn.close()

    if not emp:
        raise HTTPException(status_code=401, detail="اسم المستخدم أو رقم الجوال غير مسجل في النظام")

    emp_dict = dict(emp)
    stored_password = normalize_digits(emp_dict.get('password') or '123456')

    if password != stored_password:
        raise HTTPException(status_code=401, detail="كلمة المرور غير صحيحة")

    # Don't return plain password to client
    emp_dict.pop('password', None)

    return {
        "success": True,
        "message": f"أهلاً بك {emp_dict['name']} 🌸",
        "user": emp_dict
    }

@router.put("/change-password")
def change_password(payload: ChangePasswordRequest):
    new_password = payload.new_password.strip()
    if len(new_password) < 3:
        raise HTTPException(status_code=400, detail="يجب أن تتكون كلمة المرور الجديدة من 3 خانات على الأقل")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, password FROM employees WHERE id = ?", (payload.employee_id,))
    emp = cursor.fetchone()
    if not emp:
        conn.close()
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    stored_password = emp['password'] or '123456'

    # If current_password is provided, verify it
    if payload.current_password is not None and payload.current_password.strip() != "":
        if payload.current_password.strip() != stored_password:
            conn.close()
            raise HTTPException(status_code=400, detail="كلمة المرور الحالية غير صحيحة")

    cursor.execute("UPDATE employees SET password = ? WHERE id = ?", (new_password, payload.employee_id))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "تم تحديث كلمة المرور بنجاح ✅"
    }

@router.get("/users")
def get_auth_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, username, phone, role, status FROM employees ORDER BY id ASC")
    users = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return users
