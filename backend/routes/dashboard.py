from fastapi import APIRouter
from database import get_db
from datetime import date, timedelta
import json

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

from typing import Optional

import time

_DASH_CACHE = {}
_DASH_CACHE_TTL = 3.0  # 3 seconds cache

@router.get("/stats")
def get_dashboard_stats(florist_id: Optional[int] = None):
    cache_key = f"dash:{florist_id}"
    now_ts = time.time()
    if cache_key in _DASH_CACHE:
        cached_ts, cached_val = _DASH_CACHE[cache_key]
        if now_ts - cached_ts < _DASH_CACHE_TTL:
            return cached_val

    conn = get_db()
    cursor = conn.cursor()
    today_str = date.today().strftime("%Y-%m-%d")
    month_prefix = date.today().strftime("%Y-%m")

    # If florist_id is specified (Florist view), filter orders by their ID and hide financial/accounting totals
    if florist_id:
        # Today's orders for this florist
        cursor.execute("SELECT COUNT(*) FROM orders WHERE delivery_date = ? AND status != 'cancelled' AND florist_id = ?", (today_str, florist_id))
        today_orders_count = int(cursor.fetchone()[0])
        today_sales = 0.0

        # Monthly orders for this florist
        cursor.execute("SELECT COUNT(*) FROM orders WHERE delivery_date LIKE ? AND status != 'cancelled' AND florist_id = ?", (f"{month_prefix}%", florist_id))
        monthly_orders_count = int(cursor.fetchone()[0])
        monthly_sales = 0.0

        total_paid = 0.0
        total_unpaid = 0.0
        monthly_expenses = 0.0
        net_profit = 0.0

        # Status breakdown for this florist only
        cursor.execute("""
        SELECT status, COUNT(*) FROM orders WHERE florist_id = ? GROUP BY status
        """, (florist_id,))
        status_counts = {"new": 0, "preparing": 0, "ready": 0, "out_for_delivery": 0, "delivered": 0, "cancelled": 0}
        for row in cursor.fetchall():
            status_counts[row[0]] = row[1]

        # Urgent / Pending orders for this florist (Today first, then upcoming active orders)
        cursor.execute("""
        SELECT o.id, o.order_number, o.customer_name, o.recipient_name, o.delivery_date, o.delivery_time_slot, 
               o.total_amount, o.status, o.payment_status, o.order_type, o.event_name, d.name as driver_name
        FROM orders o
        LEFT JOIN drivers d ON o.driver_id = d.id
        WHERE o.status NOT IN ('delivered', 'cancelled') AND o.florist_id = ?
        ORDER BY CASE WHEN o.delivery_date = ? THEN 0 ELSE 1 END, o.delivery_date ASC, o.id DESC
        LIMIT 15
        """, (florist_id, today_str))
        urgent_orders = [dict(row) for row in cursor.fetchall()]
    else:
        # Today's Sales
        cursor.execute("SELECT COALESCE(SUM(total_amount), 0), COUNT(*) FROM orders WHERE delivery_date = ? AND status != 'cancelled'", (today_str,))
        today_sales_row = cursor.fetchone()
        today_sales = float(today_sales_row[0])
        today_orders_count = int(today_sales_row[1])

        # Monthly Sales
        cursor.execute("SELECT COALESCE(SUM(total_amount), 0), COUNT(*) FROM orders WHERE delivery_date LIKE ? AND status != 'cancelled'", (f"{month_prefix}%",))
        month_sales_row = cursor.fetchone()
        monthly_sales = float(month_sales_row[0])
        monthly_orders_count = int(month_sales_row[1])

        # Invoices Stats: Paid vs Unpaid
        cursor.execute("SELECT COALESCE(SUM(paid_amount), 0), COALESCE(SUM(remaining_amount), 0) FROM invoices")
        inv_row = cursor.fetchone()
        total_paid = float(inv_row[0])
        total_unpaid = float(inv_row[1])

        # Total Expenses (This month)
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE expense_date LIKE ?", (f"{month_prefix}%",))
        monthly_expenses = float(cursor.fetchone()[0])

        # Net Profit estimate (Monthly sales - Monthly expenses)
        net_profit = monthly_sales - monthly_expenses

        # Order Status Breakdown
        cursor.execute("""
        SELECT status, COUNT(*) FROM orders GROUP BY status
        """)
        status_counts = {"new": 0, "preparing": 0, "ready": 0, "out_for_delivery": 0, "delivered": 0, "cancelled": 0}
        for row in cursor.fetchall():
            status_counts[row[0]] = row[1]

        # Active Pending Orders (Today first, then upcoming active orders)
        cursor.execute("""
        SELECT o.id, o.order_number, o.customer_name, o.recipient_name, o.delivery_date, o.delivery_time_slot, 
               o.total_amount, o.status, o.payment_status, o.order_type, o.event_name, d.name as driver_name
        FROM orders o
        LEFT JOIN drivers d ON o.driver_id = d.id
        WHERE o.status NOT IN ('delivered', 'cancelled')
        ORDER BY CASE WHEN o.delivery_date = ? THEN 0 ELSE 1 END, o.delivery_date ASC, o.id DESC
        LIMIT 15
        """, (today_str,))
        urgent_orders = [dict(row) for row in cursor.fetchall()]

    # Active Drivers (Combined query)
    cursor.execute("SELECT status, COUNT(*) FROM drivers GROUP BY status")
    driver_counts = {r[0]: int(r[1]) for r in cursor.fetchall()}
    drivers_on_delivery = driver_counts.get("on_delivery", 0)
    drivers_available = driver_counts.get("available", 0)

    # Top Selling Products
    cursor.execute("""
    SELECT product_name, SUM(quantity) as total_qty, SUM(total_price) as total_val
    FROM order_items
    GROUP BY product_name
    ORDER BY total_qty DESC
    LIMIT 5
    """)
    top_products = [dict(row) for row in cursor.fetchall()]

    # Special Orders (الطلبات الخاصة والفعاليات والمناسبات الكبرى)
    cursor.execute("""
    SELECT id, order_number, customer_name, customer_phone, event_name, event_venue,
           delivery_date, delivery_time_slot, total_amount, status, notes
    FROM orders
    WHERE (order_type = 'large_event' OR event_name IS NOT NULL) AND status != 'cancelled'
    ORDER BY delivery_date ASC, id ASC
    LIMIT 10
    """)
    special_orders = [dict(row) for row in cursor.fetchall()]

    # Customers with special occasions
    cursor.execute("SELECT id, name, phone, special_occasions FROM customers WHERE special_occasions IS NOT NULL AND special_occasions != '[]' LIMIT 20")
    upcoming_occasions = []
    for row in cursor.fetchall():
        try:
            occasions = json.loads(row["special_occasions"])
            for occ in occasions:
                upcoming_occasions.append({
                    "customer_id": row["id"],
                    "customer_name": row["name"],
                    "customer_phone": row["phone"],
                    "occasion_type": occ.get("type", "مناسبة خاصة"),
                    "date": occ.get("date", ""),
                    "notes": occ.get("notes", "")
                })
        except Exception:
            pass

    conn.close()

    result = {
        "today_sales": today_sales,
        "today_orders_count": today_orders_count,
        "monthly_sales": monthly_sales,
        "monthly_orders_count": monthly_orders_count,
        "total_paid": total_paid,
        "total_unpaid": total_unpaid,
        "monthly_expenses": monthly_expenses,
        "net_profit": net_profit,
        "status_counts": status_counts,
        "drivers": {
            "on_delivery": drivers_on_delivery,
            "available": drivers_available,
            "total": drivers_on_delivery + drivers_available
        },
        "urgent_orders": urgent_orders,
        "top_products": top_products,
        "special_orders": special_orders,
        "upcoming_occasions": upcoming_occasions[:5]
    }
    _DASH_CACHE[cache_key] = (time.time(), result)
    return result
