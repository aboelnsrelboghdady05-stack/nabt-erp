from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from database import get_db
from datetime import datetime, date
import json
from routes.whatsapp import dispatch_via_gateway_if_configured

router = APIRouter(prefix="/api/sync", tags=["Accounting Sync & Webhooks"])

class WebhookItemSchema(BaseModel):
    name: str
    quantity: int = 1
    unit_price: float
    total_price: Optional[float] = None

class ExternalInvoicePayload(BaseModel):
    source_system: Optional[str] = "برنامج الحسابات السحابي (قيود / دفترة / أودو)"
    invoice_number: str
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    customer_name: str
    customer_phone: str
    customer_address: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    recipient_address: Optional[str] = None
    card_message: Optional[str] = None
    subtotal: float
    tax_amount: Optional[float] = 0.0
    total_amount: float
    payment_status: str = "paid" # paid (مسددة), unpaid (غير مسددة), partial
    payment_method: Optional[str] = "pos"
    notes: Optional[str] = None
    items: Optional[List[WebhookItemSchema]] = []

@router.get("/config")
def get_webhook_config(request: Request):
    base_url = str(request.base_url).rstrip("/")
    return {
        "webhook_url": f"{base_url}/api/sync/invoice",
        "api_key": "nabt_sec_live_2026_qoyod_daftra",
        "supported_systems": ["قيود (Qoyod)", "دفترة (Daftra)", "أودو (Odoo)", "زوهو (Zoho)", "Custom Webhook"],
        "sample_curl": f'curl -X POST "{base_url}/api/sync/invoice" -H "Content-Type: application/json" -d \'{{"invoice_number":"INV-9001","customer_name":"فيصل العتيبي","customer_phone":"0501122334","subtotal":250,"tax_amount":37.5,"total_amount":287.5,"payment_status":"unpaid","items":[{{"name":"باقة جوري أحمر","quantity":1,"unit_price":250}}]}}\''
    }

@router.post("/invoice")
async def receive_invoice_from_accounting(payload: ExternalInvoicePayload):
    """
    Webhook Receiver: Called automatically when an invoice is issued in Qoyod, Daftra, Odoo, Zoho, etc.
    Immediately syncs to Dashboard, Invoices, Orders, Drivers, and fires WhatsApp confirmation!
    """
    conn = get_db()
    cursor = conn.cursor()

    today_str = date.today().strftime("%Y-%m-%d")
    issue_date = payload.issue_date or today_str
    
    # 1. Ensure or find Customer in CRM
    cursor.execute("SELECT id FROM customers WHERE phone = ?", (payload.customer_phone,))
    existing_cust = cursor.fetchone()
    if existing_cust:
        customer_id = existing_cust[0]
        # Update customer spend
        if payload.payment_status == 'paid':
            cursor.execute("UPDATE customers SET orders_count = orders_count + 1, total_spent = total_spent + ? WHERE id = ?", (payload.total_amount, customer_id))
    else:
        cursor.execute("""
        INSERT INTO customers (name, phone, address, total_spent, orders_count, special_occasions)
        VALUES (?, ?, ?, ?, 1, '[]')
        """, (payload.customer_name, payload.customer_phone, payload.recipient_address or payload.customer_address or "", payload.total_amount if payload.payment_status == 'paid' else 0.0))
        customer_id = cursor.lastrowid

    # 2. Check if invoice number already exists, if so update it
    cursor.execute("SELECT id, order_id FROM invoices WHERE invoice_number = ?", (payload.invoice_number,))
    existing_inv = cursor.fetchone()

    paid_amt = payload.total_amount if payload.payment_status == "paid" else 0.0
    rem_amt = 0.0 if payload.payment_status == "paid" else payload.total_amount

    if existing_inv:
        # Update existing invoice
        inv_id = existing_inv[0]
        order_id = existing_inv[1]
        cursor.execute("""
        UPDATE invoices
        SET total_amount = ?, paid_amount = ?, remaining_amount = ?, status = ?, payment_method = ?
        WHERE id = ?
        """, (payload.total_amount, paid_amt, rem_amt, payload.payment_status, payload.payment_method, inv_id))
        
        if order_id:
            cursor.execute("""
            UPDATE orders SET payment_status = ?, total_amount = ? WHERE id = ?
            """, (payload.payment_status, payload.total_amount, order_id))
    else:
        # 3. Create Corresponding Operations Order (الطلب الخاص بتجهيز الورد والتوصيل)
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM orders")
        order_seq = cursor.fetchone()[0] + 1
        order_number = f"ORD-{payload.invoice_number.replace('INV-', '')}"

        # Assign first available driver if found
        cursor.execute("SELECT id FROM drivers WHERE status = 'available' LIMIT 1")
        avail_driver = cursor.fetchone()
        driver_id = avail_driver[0] if avail_driver else None

        # Smart Florist Assignment: ONLY assign to florists currently on duty in the shop (never on leave!)
        from routes.employees import get_best_available_florist
        avail_florist = get_best_available_florist(cursor)
        florist_id = avail_florist['id'] if avail_florist else None

        cursor.execute("""
        INSERT INTO orders (
            order_number, customer_id, customer_name, customer_phone,
            recipient_name, recipient_phone, recipient_address,
            card_message, delivery_date, delivery_time_slot, driver_id, florist_id,
            status, subtotal, delivery_fee, discount, tax, total_amount,
            payment_status, payment_method, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'مسائي (4ع - 8م)', ?, ?, 'new', ?, 0.0, 0.0, ?, ?, ?, ?, ?)
        """, (
            order_number, customer_id, payload.customer_name, payload.customer_phone,
            payload.recipient_name or payload.customer_name,
            payload.recipient_phone or payload.customer_phone,
            payload.recipient_address or payload.customer_address or "توصيل للعميل",
            payload.card_message or "هدية ورد ومشاعر طيبة 💐",
            issue_date, driver_id, florist_id, payload.subtotal, payload.tax_amount or 0.0,
            payload.total_amount, payload.payment_status, payload.payment_method or "pos",
            f"تم الإصدار عبر: {payload.source_system}. ملاحظات: {payload.notes or '-'}"
        ))
        order_id = cursor.lastrowid

        # Insert items into order_items
        for item in payload.items:
            unit_p = item.unit_price
            tot_p = item.total_price or (item.quantity * unit_p)
            cursor.execute("""
            INSERT INTO order_items (order_id, product_name, quantity, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?)
            """, (order_id, item.name, item.quantity, unit_p, tot_p))

        # 4. Insert Invoice into invoices table
        cursor.execute("""
        INSERT INTO invoices (
            invoice_number, order_id, customer_id, customer_name, subtotal,
            tax_amount, total_amount, paid_amount, remaining_amount,
            status, payment_method, issue_date, due_date, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.invoice_number, order_id, customer_id, payload.customer_name,
            payload.subtotal, payload.tax_amount or 0.0, payload.total_amount,
            paid_amt, rem_amt, payload.payment_status, payload.payment_method or "pos",
            issue_date, payload.due_date or issue_date, f"مستلمة آلياً من {payload.source_system}"
        ))
        inv_id = cursor.lastrowid

        # If paid, record payment receipt
        if payload.payment_status == "paid":
            cursor.execute("SELECT COALESCE(MAX(id), 0) FROM payments")
            p_seq = cursor.fetchone()[0] + 1
            cursor.execute("""
            INSERT INTO payments (payment_number, invoice_id, amount, payment_method, reference_number, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (f"PAY-{p_seq:05d}", inv_id, payload.total_amount, payload.payment_method, f"ACC-{payload.invoice_number}", "سداد مسجل في برنامج الحسابات"))

        # 5. IMMEDIATELY FIRE AUTOMATIC WHATSAPP NOTIFICATION TO CUSTOMER (Stage 1)!
        pay_status_ar = "مسدد" if payload.payment_status == 'paid' else "غير مسدد"
        amount_str = f"{payload.total_amount:g}" if float(payload.total_amount).is_integer() else f"{payload.total_amount:.2f}"
        wa_message = (
            f"شكرًا لأنك اخترت نبت | Nabt\n"
            f".\n"
            f".\n"
            f"استلمنا طلبك رقم #{order_number} بنجاح!\n"
            f".\n"
            f"قيمة الطلب: {amount_str} ر.س\n"
            f"حالة السداد: ({pay_status_ar})\n"
            f".\n"
            f"تاريخ التوصيل: {issue_date} \n"
            f"موعد التوصيل:مسائي (4ع - 8م))\n"
            f".\n"
            f".\n"
            f"من اليوم أنت جزء من نبت | Nabt 🌱"
        )
        cursor.execute("""
        INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
        VALUES (?, ?, 'outbound', 'order_update', ?, 'delivered', ?)
        """, (payload.customer_phone, payload.customer_name, wa_message, order_id))
        dispatch_via_gateway_if_configured(payload.customer_phone, wa_message)

        # If driver assigned, notify driver on WhatsApp
        if driver_id:
            cursor.execute("SELECT name, phone FROM drivers WHERE id = ?", (driver_id,))
            driver_row = cursor.fetchone()
            if driver_row:
                driver_msg = (
                    f"مرحباً يا بطل {driver_row['name']} 🚗🌸\n"
                    f"وصلت فاتورة وطلب توصيل جديد من الحسابات #{payload.invoice_number}!\n"
                    f"العميل: {payload.customer_name}\n"
                    f"المستلم: {payload.recipient_name or payload.customer_name}\n"
                    f"جوال: {payload.recipient_phone or payload.customer_phone}\n"
                    f"العنوان: {payload.recipient_address or payload.customer_address or 'يحدد لاحقاً'}\n"
                    f"الحالة: {payload.payment_status}"
                )
                cursor.execute("""
                INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
                VALUES (?, ?, 'outbound', 'driver_alert', ?, 'delivered', ?)
                """, (driver_row['phone'], driver_row['name'], driver_msg, order_id))

        # If florist assigned, notify florist on WhatsApp
        if florist_id and avail_florist:
            items_summary = " + ".join([f"{it.quantity}x {it.name}" for it in payload.items]) if payload.items else "تنسيق ورد"
            florist_msg = (
                f"🌸 مهمة تنسيق ورد جديد\n"
                f"مرحباً يا فنان {avail_florist['name']}\n"
                f"تم إسناد طلب جديد إليك من الإدارة للتجهيز:\n"
                f"• رقم الطلب: #{order_number}\n"
                f"• تفاصيل الطلب: {items_summary}\n"
                f"• 🎨 ألوان الورد والتغليف: حسب التنسيق العام والطلب\n"
                f"• كرت الإهداء: \"{payload.card_message or 'بدون كرت إهداء'}\"\n"
                f"• موعد التسليم: {issue_date} \n"
                f"• وقت التسليم(مسائي (4ع - 8م))\n"
                f"• ملاحظات التجهيز: {payload.notes or 'تنسيق قياسي أنيق'}\n"
                f"• 📸 صورة (مساندة) مرجعية: مرفقة في السيستم افتح تفاصيل الطلب لمطابقتها!\n\n"
                f"شد حيلك وأبدأ التجهيز وأكد لنا إذا جهز! 💐"
            )
            cursor.execute("""
            INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
            VALUES (?, ?, 'outbound', 'florist_alert', ?, 'delivered', ?)
            """, (avail_florist['phone'], avail_florist['name'], florist_msg, order_id))
            dispatch_via_gateway_if_configured(avail_florist['phone'], florist_msg)

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"Invoice {payload.invoice_number} synced successfully to dashboard, orders, and WhatsApp.",
        "invoice_id": inv_id,
        "invoice_number": payload.invoice_number,
        "order_id": order_id,
        "payment_status": payload.payment_status,
        "whatsapp_dispatched": True
    }

@router.post("/simulate")
def simulate_accounting_invoice():
    """
    Test Simulator: Generates a realistic invoice as if coming from Qoyod or Daftra
    to demonstrate live sync to dashboard, unpaid/paid tracking, and WhatsApp firing.
    """
    import random
    names = ["عبد العزيز بن عبد الرحمن الراجحي", "خلود بنت فهد المطيري", "تركي بن سعد الدوسري", "أميرة عبد الله السديري"]
    phones = ["0505991122", "0543322110", "0561122445", "0539988776"]
    idx = random.randint(0, len(names) - 1)
    
    inv_num = f"QYD-{random.randint(1000, 9999)}"
    is_paid = random.choice([True, False])
    
    mock_payload = ExternalInvoicePayload(
        source_system="برنامج قيود المحاسبي (Qoyod)",
        invoice_number=inv_num,
        customer_name=names[idx],
        customer_phone=phones[idx],
        recipient_name="مها السديري",
        recipient_phone="0559988112",
        recipient_address="الرياض - حي حطين - شارع الثغر",
        card_message="ألف مبروك الترقية يا غالية وعقبال أعلى المراتب 🌸💐",
        subtotal=280.0,
        tax_amount=42.0,
        total_amount=322.0,
        payment_status="paid" if is_paid else "unpaid",
        payment_method="pos" if is_paid else "cash",
        notes="فاتورة سحابية تم تصديرها من نقطة البيع",
        items=[
            WebhookItemSchema(name="باقة الجوري الهولندي الفاخر", quantity=1, unit_price=280.0, total_price=280.0)
        ]
    )

    import asyncio
    return asyncio.run(receive_invoice_from_accounting(mock_payload))

@router.post("/reset-all-data")
def reset_all_data():
    """
    تصفير جميع البيانات والعمليات لبدء العمل الحقيقي:
    - حذف جميع الطلبات والبنود (orders, order_items)
    - حذف جميع الفواتير والمدفوعات (invoices, payments)
    - حذف جميع المصروفات (expenses)
    - حذف جميع طلبات المشتريات (purchase_requests)
    - حذف جميع الإجازات (employee_leaves)
    - حذف سجل رسائل الواتساب (whatsapp_messages)
    - تفريغ بيانات العملاء التجريبية (customers)
    - تصفير عدادات المناديب وتعيين حالتهم لمتاح (drivers)
    - تصفير عدادات الموظفين وإعادتهم للعمل (employees)
    - تصفير عدادات الترقيم التلقائي (sqlite_sequence) لتبدأ الطلبات من #1 والفواتير من #1
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM order_items")
    cursor.execute("DELETE FROM payments")
    cursor.execute("DELETE FROM invoices")
    cursor.execute("DELETE FROM orders")
    cursor.execute("DELETE FROM expenses")
    cursor.execute("DELETE FROM purchase_requests")
    cursor.execute("DELETE FROM employee_leaves")
    cursor.execute("DELETE FROM whatsapp_messages")
    cursor.execute("DELETE FROM customers")

    cursor.execute("UPDATE drivers SET total_delivered = 0, status = 'available'")
    cursor.execute("UPDATE employees SET active_orders_count = 0, status = 'on_duty'")

    tables_to_reset = [
        'orders', 'order_items', 'invoices', 'payments', 
        'expenses', 'purchase_requests', 'employee_leaves', 
        'whatsapp_messages', 'customers'
    ]
    for tbl in tables_to_reset:
        try:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (tbl,))
        except Exception:
            pass

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "تم تصفير وحذف جميع العمليات والإجازات والطلبات بنجاح. السيستم نظيف وجاهز للعمل الحقيقي من الصفر 🌸"
    }
