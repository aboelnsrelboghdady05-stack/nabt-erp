from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from datetime import datetime

router = APIRouter(prefix="/api/evaluations", tags=["Employee Evaluations & Florist Performance"])

class EvaluationSubmitSchema(BaseModel):
    employee_id: int
    eval_month: Optional[str] = None
    rating: int = 5
    score: int = 95
    quality_score: int = 5
    speed_score: int = 5
    discipline_score: int = 5
    manager_feedback: Optional[str] = None
    evaluator_name: str = "فيصل (مدير تشغيلي)"

@router.get("")
def get_evaluations_and_performance(
    month: Optional[str] = Query(None, description="Month format YYYY-MM or 'all'"),
    employee_id: Optional[int] = Query(None, description="Filter by specific employee ID")
):
    if not isinstance(month, str):
        month = None
    if not isinstance(employee_id, int):
        employee_id = None
        
    active_month = month.strip() if month else datetime.now().strftime("%Y-%m")
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # 1. Fetch employees (prioritizing florists)
        emp_query = "SELECT id, name, phone, role, status, specialty, weekly_off_day FROM employees"
        params = []
        if employee_id:
            emp_query += " WHERE id = ?"
            params.append(employee_id)
        emp_query += " ORDER BY CASE WHEN role = 'florist' THEN 0 ELSE 1 END, id ASC"
        
        cursor.execute(emp_query, params)
        employees = [dict(r) for r in cursor.fetchall()]
        
        evaluations_list = []
        total_orders_all = 0
        total_sales_all = 0.0
        
        for emp in employees:
            e_id = emp["id"]
            
            # 2. Fetch orders assigned/executed by this florist
            order_query = """
            SELECT id, order_number, customer_name, customer_phone, delivery_date, delivery_time_slot,
                   total_amount, status, payment_status, created_at, notes, flower_colors, completed_image,
                   order_type
            FROM orders
            WHERE florist_id = ?
            """
            order_params = [e_id]
            
            if active_month and active_month != "all":
                order_query += " AND (delivery_date LIKE ? OR created_at LIKE ?)"
                order_params.extend([f"{active_month}%", f"{active_month}%"])
                
            order_query += " ORDER BY id DESC"
            cursor.execute(order_query, order_params)
            orders_rows = [dict(r) for r in cursor.fetchall()]
            
            total_orders = len(orders_rows)
            total_sales = sum(float(r.get("total_amount") or 0.0) for r in orders_rows)
            avg_order_val = round(total_sales / total_orders, 2) if total_orders > 0 else 0.0
            
            completed_orders = sum(1 for r in orders_rows if r.get("status") in ("delivered", "completed", "prepared"))
            in_progress_orders = sum(1 for r in orders_rows if r.get("status") in ("new", "preparing"))
            
            total_orders_all += total_orders
            total_sales_all += total_sales
            
            # 3. Fetch latest evaluation for this employee
            eval_query = """
            SELECT id, eval_month, rating, score, quality_score, speed_score, discipline_score,
                   manager_feedback, evaluator_name, created_at, updated_at
            FROM employee_evaluations
            WHERE employee_id = ?
            """
            eval_params = [e_id]
            if active_month and active_month != "all":
                eval_query += " AND eval_month = ?"
                eval_params.append(active_month)
            eval_query += " ORDER BY id DESC LIMIT 1"
            
            cursor.execute(eval_query, eval_params)
            eval_row = cursor.fetchone()
            
            eval_data = dict(eval_row) if eval_row else {
                "id": None,
                "eval_month": active_month,
                "rating": 5 if total_orders > 0 else 0,
                "score": 95 if total_orders > 0 else 80,
                "quality_score": 5 if total_orders > 0 else 0,
                "speed_score": 5 if total_orders > 0 else 0,
                "discipline_score": 5 if total_orders > 0 else 0,
                "manager_feedback": "في انتظار تسجيل تقييم الإدارة لهذا الشهر" if total_orders == 0 else "أداء ممتاز في تنفيذ طلبات وباقات الورد",
                "evaluator_name": "إدارة نبت ورد",
                "created_at": None,
                "updated_at": None
            }
            
            evaluations_list.append({
                "employee_id": e_id,
                "employee_name": emp["name"],
                "employee_role": emp["role"],
                "employee_phone": emp["phone"],
                "employee_status": emp["status"],
                "employee_specialty": emp["specialty"] or "تنسيق ورد وتغليف",
                "weekly_off_day": emp["weekly_off_day"] or "الثلاثاء",
                
                # Performance metrics
                "total_orders": total_orders,
                "total_sales": round(total_sales, 2),
                "avg_order_value": avg_order_val,
                "completed_orders": completed_orders,
                "in_progress_orders": in_progress_orders,
                "orders_list": orders_rows,
                
                # Manager evaluation
                "evaluation_id": eval_data.get("id"),
                "eval_month": eval_data.get("eval_month") or active_month,
                "rating": eval_data.get("rating") or 5,
                "score": eval_data.get("score") or 95,
                "quality_score": eval_data.get("quality_score") or 5,
                "speed_score": eval_data.get("speed_score") or 5,
                "discipline_score": eval_data.get("discipline_score") or 5,
                "manager_feedback": eval_data.get("manager_feedback"),
                "evaluator_name": eval_data.get("evaluator_name"),
                "evaluated_at": eval_data.get("updated_at") or eval_data.get("created_at")
            })
            
        # Top Florist calculation
        florists_only = [e for e in evaluations_list if e["employee_role"] == "florist"]
        top_florist = max(florists_only, key=lambda x: x["total_orders"], default=None) if florists_only else None
        top_sales_florist = max(florists_only, key=lambda x: x["total_sales"], default=None) if florists_only else None
        
        stats = {
            "total_orders_all": total_orders_all,
            "total_sales_all": round(total_sales_all, 2),
            "active_florists_count": len(florists_only),
            "total_employees_count": len(evaluations_list),
            "top_florist_name": top_florist["employee_name"] if top_florist and top_florist["total_orders"] > 0 else "—",
            "top_florist_orders": top_florist["total_orders"] if top_florist else 0,
            "top_sales_florist_name": top_sales_florist["employee_name"] if top_sales_florist and top_sales_florist["total_sales"] > 0 else "—",
            "top_sales_amount": top_sales_florist["total_sales"] if top_sales_florist else 0.0,
            "active_month": active_month
        }
        
        return {
            "success": True,
            "evaluations": evaluations_list,
            "stats": stats,
            "active_month": active_month
        }
    finally:
        conn.close()

@router.post("")
def submit_evaluation(payload: EvaluationSubmitSchema):
    """
    إدخال أو تعديل تقييم المنسق / الموظف
    """
    month_val = payload.eval_month or datetime.now().strftime("%Y-%m")
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Verify employee exists
        cursor.execute("SELECT id, name FROM employees WHERE id = ?", (payload.employee_id,))
        emp = cursor.fetchone()
        if not emp:
            raise HTTPException(status_code=404, detail="الموظف غير موجود")
            
        emp_name = emp["name"]
        
        # Check if evaluation for this employee and month exists
        cursor.execute("""
        SELECT id FROM employee_evaluations
        WHERE employee_id = ? AND eval_month = ?
        """, (payload.employee_id, month_val))
        existing = cursor.fetchone()
        
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if existing:
            cursor.execute("""
            UPDATE employee_evaluations
            SET rating = ?, score = ?, quality_score = ?, speed_score = ?, discipline_score = ?,
                manager_feedback = ?, evaluator_name = ?, updated_at = ?
            WHERE id = ?
            """, (
                payload.rating,
                payload.score,
                payload.quality_score,
                payload.speed_score,
                payload.discipline_score,
                payload.manager_feedback or f"أداء مميز للمنسق {emp_name}",
                payload.evaluator_name,
                now_str,
                existing["id"]
            ))
            eval_id = existing["id"]
            msg = f"تم تحديث تقييم المنسق ({emp_name}) بنجاح ⭐"
        else:
            cursor.execute("""
            INSERT INTO employee_evaluations (
                employee_id, eval_month, rating, score, quality_score, speed_score, discipline_score,
                manager_feedback, evaluator_name, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload.employee_id,
                month_val,
                payload.rating,
                payload.score,
                payload.quality_score,
                payload.speed_score,
                payload.discipline_score,
                payload.manager_feedback or f"أداء مميز للمنسق {emp_name}",
                payload.evaluator_name,
                now_str,
                now_str
            ))
            eval_id = cursor.lastrowid
            msg = f"تم تسجيل واعتماد تقييم المنسق ({emp_name}) بنجاح ⭐"
            
        conn.commit()
        return {
            "success": True,
            "evaluation_id": eval_id,
            "message": msg
        }
    finally:
        conn.close()

@router.delete("/{eval_id}")
def delete_evaluation(eval_id: int):
    """
    حذف تقييم مسجل
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM employee_evaluations WHERE id = ?", (eval_id,))
        conn.commit()
        return {"success": True, "message": "تم حذف التقييم بنجاح"}
    finally:
        conn.close()
