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

@router.post("/login")
def login(payload: LoginRequest):
    identifier = payload.identifier.strip()
    password = payload.password.strip()

    conn = get_db()
    cursor = conn.cursor()

    # Search by username, phone, or name
    cursor.execute("""
    SELECT id, name, username, phone, role, status, specialty, password
    FROM employees
    WHERE LOWER(username) = LOWER(?) 
       OR phone = ? 
       OR name = ? 
       OR name LIKE ?
    LIMIT 1
    """, (identifier, identifier, identifier, f"%{identifier}%"))
    
    emp = cursor.fetchone()
    conn.close()

    if not emp:
        raise HTTPException(status_code=401, detail="اسم المستخدم غير مسجل في النظام")

    emp_dict = dict(emp)
    stored_password = emp_dict.get('password') or '123456'

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
