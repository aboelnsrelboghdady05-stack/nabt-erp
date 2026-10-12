from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db
from datetime import date

router = APIRouter(prefix="/api/expenses", tags=["Expenses"])

class ExpenseCreateSchema(BaseModel):
    title: str
    category: str # شراء ورد خام، تغليف وشرائط، إيجار، رواتب، كهرباء، صيانة، تسويق، أخرى
    amount: float
    payment_method: str = "cash"
    expense_date: Optional[str] = None
    vendor_name: Optional[str] = None
    notes: Optional[str] = None

@router.get("")
def get_expenses(category: Optional[str] = None, month: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM expenses WHERE 1=1"
    params = []
    if category and category != "all":
        query += " AND category = ?"
        params.append(category)
    if month:
        query += " AND expense_date LIKE ?"
        params.append(f"{month}%")

    query += " ORDER BY expense_date DESC, id DESC"
    cursor.execute(query, params)
    expenses = [dict(row) for row in cursor.fetchall()]

    # Summary by category
    cursor.execute("""
    SELECT category, SUM(amount) as total
    FROM expenses
    GROUP BY category
    ORDER BY total DESC
    """)
    category_summary = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return {
        "expenses": expenses,
        "category_summary": category_summary,
        "total_amount": sum(e["amount"] for e in expenses)
    }

@router.post("")
def create_expense(payload: ExpenseCreateSchema):
    conn = get_db()
    cursor = conn.cursor()
    exp_date = payload.expense_date or date.today().strftime("%Y-%m-%d")

    cursor.execute("""
    INSERT INTO expenses (title, category, amount, payment_method, expense_date, vendor_name, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (payload.title, payload.category, payload.amount, payload.payment_method, exp_date, payload.vendor_name, payload.notes))
    
    exp_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "id": exp_id}
