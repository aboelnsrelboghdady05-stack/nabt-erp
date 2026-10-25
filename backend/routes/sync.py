from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from database import get_db
from datetime import datetime, date
import json
import urllib.request
import urllib.parse
import urllib.error
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

# ========================================================
# DAFTRA (دفترة) READ-ONLY INTEGRATION
# استقبال وسحب الفواتير فقط وعرضها في الداشبورد دون إرسال أي أوامر لدفترة
# ========================================================

class DaftraSettingsSaveSchema(BaseModel):
    subdomain: str
    api_key: Optional[str] = None

def import_daftra_raw_invoice(raw_item: dict, conn, cursor) -> dict:
    inv = raw_item.get("Invoice") or raw_item.get("invoice") or raw_item
    client = raw_item.get("Client") or raw_item.get("client") or raw_item.get("Customer") or raw_item.get("customer") or {}

    raw_id = inv.get("id") or inv.get("invoice_id") or ""
    raw_no = inv.get("invoice_number") or inv.get("no") or inv.get("number") or str(raw_id)
    raw_no_str = str(raw_no).strip()
    if not raw_no_str.startswith("DFT-") and not raw_no_str.startswith("INV-"):
        invoice_number = f"DFT-{raw_no_str}"
    else:
        invoice_number = raw_no_str

    first_name = (client.get("first_name") or client.get("name") or inv.get("client_name") or "عميل دفترة").strip()
    last_name = (client.get("last_name") or "").strip()
    client_name = f"{first_name} {last_name}".strip() or "عميل دفترة"

    client_phone = (client.get("phone1") or client.get("phone") or client.get("mobile") or inv.get("client_phone") or "0500000000").strip()
    client_address = (client.get("address1") or client.get("address") or inv.get("client_address") or "المعرض / توصيل").strip()

    total = float(inv.get("total") or inv.get("total_amount") or 0.0)
    subtotal = float(inv.get("sub_total") or inv.get("subtotal") or (total / 1.15 if total > 0 else 0.0))
    tax = float(inv.get("tax_total") or inv.get("tax_amount") or (total - subtotal))

    # Payment status (Daftra: 1 = paid, 2 = partial, 0/3 = unpaid)
    raw_status = inv.get("payment_status")
    paid_val = float(inv.get("paid") or 0.0)
    if str(raw_status) in ["1", "paid"] or (paid_val >= total and total > 0):
        pay_status = "paid"
    elif str(raw_status) in ["2", "partial"] or (0 < paid_val < total):
        pay_status = "partial"
    else:
        pay_status = "unpaid"

    issue_date = str(inv.get("date") or inv.get("created_at") or date.today().strftime("%Y-%m-%d")).split("T")[0].split(" ")[0]
    due_date = str(inv.get("due_date") or issue_date).split("T")[0].split(" ")[0]

    # Items
    items_list = []
    raw_items = inv.get("InvoiceItem") or inv.get("items") or []
    for it in raw_items:
        it_dict = it.get("InvoiceItem") if isinstance(it, dict) and "InvoiceItem" in it else it
        if isinstance(it_dict, dict):
            it_name = it_dict.get("item") or it_dict.get("name") or it_dict.get("description") or "تنسيق ورد"
            it_qty = int(float(it_dict.get("quantity") or 1))
            it_unit_price = float(it_dict.get("unit_price") or it_dict.get("price") or (total / it_qty if it_qty else total))
            items_list.append(WebhookItemSchema(
                name=it_name,
                quantity=it_qty,
                unit_price=it_unit_price,
                total_price=it_unit_price * it_qty
            ))

    if not items_list:
        items_list.append(WebhookItemSchema(name="طلب وتنسيق ورد", quantity=1, unit_price=subtotal, total_price=subtotal))

    payload = ExternalInvoicePayload(
        source_system="دفترة (Daftra)",
        invoice_number=invoice_number,
        issue_date=issue_date,
        due_date=due_date,
        customer_name=client_name,
        customer_phone=client_phone,
        customer_address=client_address,
        subtotal=subtotal,
        tax_amount=tax,
        total_amount=total,
        payment_status=pay_status,
        payment_method="pos",
        notes="مستورد من برنامج دفترة (قراءة فقط 🛡️)",
        items=items_list
    )

    import asyncio
    return asyncio.run(receive_invoice_from_accounting(payload))

@router.get("/daftra/status")
def get_daftra_status(request: Request):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT value FROM system_settings WHERE key = 'daftra_subdomain'")
    sub_row = cursor.fetchone()
    cursor.execute("SELECT value FROM system_settings WHERE key = 'daftra_api_key'")
    key_row = cursor.fetchone()
    cursor.execute("SELECT value FROM system_settings WHERE key = 'daftra_last_sync'")
    sync_row = cursor.fetchone()

    subdomain = sub_row[0] if sub_row else ""
    api_key = key_row[0] if key_row else ""
    last_sync = sync_row[0] if sync_row else "لم يتم السحب بعد"

    cursor.execute("SELECT COUNT(*) FROM invoices WHERE notes LIKE '%دفترة%'")
    daftra_invoices_count = int(cursor.fetchone()[0])
    
    base_url = str(request.base_url).rstrip("/")
    conn.close()

    return {
        "subdomain": subdomain,
        "has_api_key": bool(api_key),
        "api_key_masked": (api_key[:4] + "••••••••" + api_key[-4:]) if len(api_key) > 8 else ("••••" if api_key else ""),
        "webhook_url": f"{base_url}/api/sync/daftra/webhook",
        "last_sync": last_sync,
        "total_imported": daftra_invoices_count,
        "read_only_mode": True
    }

@router.post("/daftra/settings")
def save_daftra_settings(payload: DaftraSettingsSaveSchema):
    conn = get_db()
    cursor = conn.cursor()
    clean_sub = payload.subdomain.replace("https://", "").replace("http://", "").split(".")[0].strip()
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('daftra_subdomain', ?)", (clean_sub,))
    if payload.api_key and payload.api_key.strip():
        cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('daftra_api_key', ?)", (payload.api_key.strip(),))
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم حفظ إعدادات دفترة بنجاح (وضع القراءة فقط 🛡️)"}

@router.post("/daftra/webhook")
async def receive_daftra_webhook(request: Request):
    """
    نقطة استقبال الويب هوك الخاص بدفترة (Webhook Receiver):
    يستقبل الفاتورة فور إصدارها في دفترة ويعرضها مباشرة في الداشبورد.
    لا يقوم بإرسال أي أوامر إلى دفترة نهائياً (استقبال وقراءة فقط).
    """
    try:
        body = await request.json()
    except Exception:
        try:
            form = await request.form()
            body = dict(form)
        except Exception:
            body = {}

    if not body:
        raise HTTPException(status_code=400, detail="البيانات المستقبلة فارغة")

    conn = get_db()
    cursor = conn.cursor()
    
    try:
        result = import_daftra_raw_invoice(body, conn, cursor)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('daftra_last_webhook', ?)", (now_str,))
        conn.commit()
        conn.close()
        return {
            "success": True,
            "message": "تم استقبال فاتورة دفترة وعرضها في الداشبورد بنجاح (قراءة فقط)",
            "read_only": True,
            "details": result
        }
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء معالجة فاتورة دفترة: {str(e)}")

@router.post("/daftra/pull")
def pull_daftra_invoices():
    """
    سحب الفواتير من دفترة مباشرة - قراءة فقط (Strictly Read-Only GET)
    لا يرسل أي أوامر أو تعديلات إلى حساب دفترة إطلاقاً.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM system_settings WHERE key = 'daftra_subdomain'")
    sub_row = cursor.fetchone()
    cursor.execute("SELECT value FROM system_settings WHERE key = 'daftra_api_key'")
    key_row = cursor.fetchone()

    subdomain = (sub_row[0] if sub_row else "").strip()
    api_key = (key_row[0] if key_row else "").strip()

    if not subdomain or not api_key:
        conn.close()
        raise HTTPException(status_code=400, detail="يرجى إدخال رابط الدومين ومفتاح الـ API الخاص بدفترة أولاً")

    clean_subdomain = subdomain.replace("https://", "").replace("http://", "").split(".")[0].strip()
    
    url = f"https://{clean_subdomain}.daftra.com/api2/invoices.json?limit=50&order=id:desc"
    req = urllib.request.Request(
        url,
        headers={
            "APIKEY": api_key,
            "Accept": "application/json",
            "User-Agent": "NabtERP-ReadOnly-Sync/1.0"
        },
        method="GET"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = response.read().decode('utf-8')
            res_data = json.loads(res_body)
    except urllib.error.HTTPError as e:
        conn.close()
        error_detail = f"خطأ من دفترة ({e.code}): تحقق من صحة اسم النطاق ({clean_subdomain}) ومفتاح الـ API"
        raise HTTPException(status_code=400, detail=error_detail)
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"تعذر الاتصال بـ دفترة: {str(e)}")

    invoices_data = res_data.get("data") or []
    if isinstance(res_data, list):
        invoices_data = res_data

    imported_count = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in invoices_data:
        try:
            import_daftra_raw_invoice(item, conn, cursor)
            imported_count += 1
        except Exception as err:
            print(f"[Daftra Import Error]: {err}")

    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('daftra_last_sync', ?)", (now_str,))
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('daftra_total_imported', ?)", (str(imported_count),))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"تم سحب وتحديث {imported_count} فاتورة من دفترة بنجاح، وعرضها في الداشبورد والفواتير (قراءة فقط 🛡️)",
        "count": imported_count,
        "last_sync": now_str,
        "read_only": True
    }
