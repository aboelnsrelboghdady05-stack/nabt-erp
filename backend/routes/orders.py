from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from database import get_db
from datetime import datetime, date, timezone
import json
import os
import shutil
import uuid
from routes.whatsapp import dispatch_via_gateway_if_configured, clean_phone_number

router = APIRouter(prefix="/api/orders", tags=["Orders"])

class OrderItemSchema(BaseModel):
    product_id: Optional[int] = None
    product_name: str
    quantity: int = 1
    unit_price: float

class OrderCreateSchema(BaseModel):
    customer_id: Optional[int] = None
    customer_name: str
    customer_phone: str
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    recipient_address: Optional[str] = None
    location_url: Optional[str] = None
    card_message: Optional[str] = None
    reference_image: Optional[str] = None
    flower_colors: Optional[str] = None
    delivery_date: str
    delivery_time_slot: Optional[str] = None
    driver_id: Optional[int] = None
    florist_id: Optional[int] = None
    created_by: Optional[str] = "المدير (Admin)"
    delivery_fee: float = 35.0
    discount: float = 0.0
    payment_status: str = "unpaid" # paid, unpaid
    payment_method: str = "pos" # cash, pos, transfer, stc_pay, online
    notes: Optional[str] = None
    items: List[OrderItemSchema]



class OrderStatusUpdateSchema(BaseModel):
    status: str # new, preparing, ready, out_for_delivery, delivered, cancelled

class OrderAcceptSchema(BaseModel):
    florist_id: Optional[int] = None
    florist_name: Optional[str] = None

class OrderRejectSchema(BaseModel):
    florist_id: Optional[int] = None
    florist_name: Optional[str] = None
    reason: Optional[str] = "المنسق مشغول بطلبات أخرى حالياً"

class OrderCompleteWorkSchema(BaseModel):
    completed_image: str
    florist_id: Optional[int] = None
    florist_name: Optional[str] = None

class OrderApproveSchema(BaseModel):
    approved_by: str = "فيصل (الآدمن)" # or نادر (المدير)
    action: str = "approve" # approve or request_revision
    notes: Optional[str] = None

class AssignDriverSchema(BaseModel):
    driver_id: int

class AssignFloristSchema(BaseModel):
    florist_id: int

@router.post("/upload-reference")
async def upload_reference_image(file: UploadFile = File(...)):
    """
    Upload customer reference design image for florist
    """
    filename = file.filename or "reference.jpg"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        ext = ".jpg"
    
    unique_name = f"ref_{uuid.uuid4().hex[:12]}{ext}"
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static", "uploads", "orders")
    os.makedirs(uploads_dir, exist_ok=True)
    target_path = os.path.join(uploads_dir, unique_name)
    
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {
        "success": True,
        "image_url": f"/static/uploads/orders/{unique_name}",
        "filename": unique_name
    }

@router.post("/upload-completed")
async def upload_completed_order_image(file: UploadFile = File(...)):
    """
    Upload florist completed bouquet/gift photo before manager/admin approval
    """
    filename = file.filename or "completed.jpg"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        ext = ".jpg"
    
    unique_name = f"done_{uuid.uuid4().hex[:12]}{ext}"
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static", "uploads", "orders")
    os.makedirs(uploads_dir, exist_ok=True)
    target_path = os.path.join(uploads_dir, unique_name)
    
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {
        "success": True,
        "image_url": f"/static/uploads/orders/{unique_name}",
        "filename": unique_name
    }

@router.get("")
def get_orders(
    status: Optional[str] = None, 
    date_filter: Optional[str] = None, 
    search: Optional[str] = None,
    florist_id: Optional[int] = None
):
    try:
        check_and_process_florist_timeouts()
    except Exception as e:
        print(f"[Timeout Check Warning]: {e}")

    conn = get_db()
    cursor = conn.cursor()

    query = """
    SELECT o.*, d.name as driver_name, d.phone as driver_phone,
           e.name as florist_name, e.phone as florist_phone
    FROM orders o
    LEFT JOIN drivers d ON o.driver_id = d.id
    LEFT JOIN employees e ON o.florist_id = e.id
    WHERE 1=1
    """
    params = []

    if florist_id:
        query += " AND o.florist_id = ?"
        params.append(florist_id)

    if status and status != "all":
        query += " AND o.status = ?"
        params.append(status)
    if date_filter:
        query += " AND o.delivery_date = ?"
        params.append(date_filter)
    if search:
        query += " AND (o.order_number LIKE ? OR o.customer_name LIKE ? OR o.customer_phone LIKE ? OR o.recipient_name LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    query += " ORDER BY o.id DESC"
    cursor.execute(query, params)
    orders = [dict(row) for row in cursor.fetchall()]

    # Fetch items for each order
    for o in orders:
        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (o["id"],))
        o["items"] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return orders

@router.get("/{order_id}")
def get_order_detail(order_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT o.*, d.name as driver_name, d.phone as driver_phone,
           e.name as florist_name, e.phone as florist_phone,
           inv.id as invoice_id, inv.invoice_number, inv.status as invoice_status, inv.remaining_amount
    FROM orders o
    LEFT JOIN drivers d ON o.driver_id = d.id
    LEFT JOIN employees e ON o.florist_id = e.id
    LEFT JOIN invoices inv ON inv.order_id = o.id
    WHERE o.id = ?
    """, (order_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    order = dict(row)
    cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    order["items"] = [dict(r) for r in cursor.fetchall()]

    # Also fetch related WhatsApp messages
    cursor.execute("SELECT * FROM whatsapp_messages WHERE related_order_id = ? ORDER BY id DESC", (order_id,))
    order["whatsapp_messages"] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return order

@router.post("")
def create_order(payload: OrderCreateSchema):
    conn = get_db()
    cursor = conn.cursor()

    # 1. Ensure or find customer
    customer_id = payload.customer_id
    if not customer_id:
        cursor.execute("SELECT id FROM customers WHERE phone = ?", (payload.customer_phone,))
        existing_cust = cursor.fetchone()
        if existing_cust:
            customer_id = existing_cust[0]
        else:
            cursor.execute("""
            INSERT INTO customers (name, phone, address, special_occasions)
            VALUES (?, ?, ?, '[]')
            """, (payload.customer_name, payload.customer_phone, payload.recipient_address or ""))
            customer_id = cursor.lastrowid

    # 2. Calculate totals (Prices are TAX-INCLUSIVE 15%)
    gross_items = sum(item.quantity * item.unit_price for item in payload.items)
    total_amount = round(max(0.0, gross_items + payload.delivery_fee - payload.discount), 2)
    subtotal = round(total_amount / 1.15, 2)
    tax = round(total_amount - subtotal, 2)
    taxable_amount = subtotal

    # 3. Generate Order Number
    year_prefix = date.today().strftime("%y")
    cursor.execute("SELECT COALESCE(MAX(id), 0) FROM orders")
    count = cursor.fetchone()[0] + 1
    order_number = f"NBT-{year_prefix}{count:04d}"

    # 3.5. Smart Florist Assignment
    from routes.employees import get_best_available_florist, check_employee_availability_on_date
    from routes.whatsapp import dispatch_via_gateway_if_configured, clean_phone_number
    import urllib.parse

    assigned_florist = None
    if payload.florist_id:
        is_avail, unavail_reason = check_employee_availability_on_date(cursor, payload.florist_id, payload.delivery_date)
        if not is_avail:
            conn.close()
            raise HTTPException(status_code=400, detail=f"عذراً! {unavail_reason} يرجى اختيار منسق آخر أو ترك الحقل فارغاً للإسناد التلقائي.")
        
        cursor.execute("SELECT * FROM employees WHERE id = ? AND role = 'florist'", (payload.florist_id,))
        f_row = cursor.fetchone()
        if f_row:
            assigned_florist = dict(f_row)
    
    if not assigned_florist:
        assigned_florist = get_best_available_florist(cursor, target_date=payload.delivery_date)

    florist_id = assigned_florist['id'] if assigned_florist else None

    # 4. Insert Order
    assigned_at_val = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if florist_id else None
    cursor.execute("""
    INSERT INTO orders (
        order_number, customer_id, customer_name, customer_phone,
        recipient_name, recipient_phone, recipient_address, location_url,
        card_message, reference_image, flower_colors, delivery_date, delivery_time_slot, driver_id, florist_id,
        status, subtotal, delivery_fee, discount, tax, total_amount,
        payment_status, payment_method, notes, received_at,
        florist_assigned_at, florist_reminder_count
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, 0)
    """, (
        order_number, customer_id, payload.customer_name, payload.customer_phone,
        payload.recipient_name or payload.customer_name,
        payload.recipient_phone or payload.customer_phone,
        payload.recipient_address, payload.location_url,
        payload.card_message, payload.reference_image, payload.flower_colors, payload.delivery_date, payload.delivery_time_slot,
        payload.driver_id, florist_id, subtotal, payload.delivery_fee, payload.discount, tax, total_amount,
        payload.payment_status, payload.payment_method, payload.notes,
        assigned_at_val
    ))
    order_id = cursor.lastrowid

    # Increment active workload of florist if assigned
    if florist_id:
        cursor.execute("UPDATE employees SET active_orders_count = active_orders_count + 1 WHERE id = ?", (florist_id,))

    # 5. Insert Items
    for item in payload.items:
        cursor.execute("""
        INSERT INTO order_items (order_id, product_id, product_name, quantity, unit_price, total_price)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (order_id, item.product_id, item.product_name, item.quantity, item.unit_price, item.quantity * item.unit_price))

        # Decrement product stock if product_id is provided
        if item.product_id:
            cursor.execute("UPDATE products SET stock = MAX(0, stock - ?) WHERE id = ?", (item.quantity, item.product_id))

    # 6. Create Invoice
    invoice_number = f"INV-{year_prefix}{count:04d}"
    paid_amt = total_amount if payload.payment_status == "paid" else 0.0
    rem_amt = 0.0 if payload.payment_status == "paid" else total_amount

    cursor.execute("""
    INSERT INTO invoices (
        invoice_number, order_id, customer_id, customer_name, subtotal,
        tax_amount, total_amount, paid_amount, remaining_amount,
        status, payment_method, issue_date, due_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        invoice_number, order_id, customer_id, payload.customer_name,
        taxable_amount, tax, total_amount, paid_amt, rem_amt,
        payload.payment_status, payload.payment_method, payload.delivery_date, payload.delivery_date
    ))
    invoice_id = cursor.lastrowid

    # 7. Record Payment if paid
    if payload.payment_status == "paid":
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM payments")
        p_count = cursor.fetchone()[0] + 1
        cursor.execute("""
        INSERT INTO payments (payment_number, invoice_id, amount, payment_method, reference_number, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (f"PAY-{p_count:05d}", invoice_id, total_amount, payload.payment_method, f"TXN-{order_number}", "سداد كامل للطلب عند الإنشاء"))

    # 8. Update Customer totals
    cursor.execute("""
    UPDATE customers 
    SET orders_count = orders_count + 1,
        total_spent = total_spent + ?
    WHERE id = ?
    """, (total_amount if payload.payment_status == 'paid' else 0.0, customer_id))

    # 9. Send Automated WhatsApp Confirmation to Customer (المرحلة الأولى: استكمال الطلب)
    pay_status_ar = "مسدد" if payload.payment_status == 'paid' else "غير مسدد"
    slot_text = payload.delivery_time_slot or "مسائي (4ع - 8م)"
    amount_str = f"{total_amount:g}" if float(total_amount).is_integer() else f"{total_amount:.2f}"
    wa_msg = (
        f"شكرًا لأنك اخترت نبت | Nabt\n"
        f".\n"
        f".\n"
        f"استلمنا طلبك رقم #{order_number} بنجاح!\n"
        f".\n"
        f"قيمة الطلب: {amount_str} ر.س\n"
        f"حالة السداد: ({pay_status_ar})\n"
        f".\n"
        f"تاريخ التوصيل: {payload.delivery_date} \n"
        f"موعد التوصيل:{slot_text}\n"
        f".\n"
        f".\n"
        f"من اليوم أنت جزء من نبت | Nabt 🌱"
    )
    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
    VALUES (?, ?, 'outbound', 'order_update', ?, 'delivered', ?)
    """, (payload.customer_phone, payload.customer_name, wa_msg, order_id))

    # 10. Send Automated WhatsApp Florist Task Dispatch
    florist_wa_link = None
    if assigned_florist:
        items_summary = " + ".join([f"{it.quantity}x {it.product_name}" for it in payload.items])
        flower_colors_text = payload.flower_colors or "تنسيق قياسي أنيق"
        card_text = payload.card_message or "بدون كرت إهداء"
        slot_text = payload.delivery_time_slot or "مسائي (4ع - 8م)"
        # ensure no duplicate parentheses
        clean_slot = slot_text.strip()
        if clean_slot.startswith("(") and clean_slot.endswith(")"):
            clean_slot = clean_slot[1:-1].strip()
        notes_text = payload.notes or "تنسيق قياسي أنيق"
        ref_text = "مرفقة في السيستم افتح تفاصيل الطلب لمطابقتها!" if payload.reference_image else "بدون صورة (تنسيق نبت القياسي)"

        florist_msg = (
            f"🌸 مهمة تنسيق ورد جديد\n"
            f"مرحباً يا فنان {assigned_florist['name']}\n"
            f"تم إسناد طلب جديد إليك من الإدارة للتجهيز:\n"
            f"• رقم الطلب: #{order_number}\n"
            f"• تفاصيل الطلب: {items_summary}\n"
            f"• 🎨 ألوان الورد والتغليف: {flower_colors_text}\n"
            f"• كرت الإهداء: \"{card_text}\"\n"
            f"• موعد التسليم: {payload.delivery_date} \n"
            f"• وقت التسليم({clean_slot})\n"
            f"• ملاحظات التجهيز: {notes_text}\n"
            f"• 📸 صورة (مساندة) مرجعية: {ref_text}\n\n"
            f"شد حيلك وأبدأ التجهيز وأكد لنا إذا جهز! 💐"
        )
        cursor.execute("""
        INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
        VALUES (?, ?, 'outbound', 'florist_alert', ?, 'delivered', ?)
        """, (assigned_florist['phone'], assigned_florist['name'], florist_msg, order_id))

        clean_f_phone = clean_phone_number(assigned_florist['phone'])
        encoded_f_msg = urllib.parse.quote(florist_msg)
        florist_wa_link = f"https://wa.me/{clean_f_phone}?text={encoded_f_msg}"

    # If driver assigned, also queue driver alert
    driver_row = None
    driver_msg = None
    if payload.driver_id:
        cursor.execute("SELECT name, phone FROM drivers WHERE id = ?", (payload.driver_id,))
        driver_row = cursor.fetchone()
        if driver_row:
            driver_msg = (
                f"مرحباً يا بطل {driver_row['name']} 🚗\n"
                f"طلب جديد برقم #{order_number}\n"
                f"المستلم: {payload.recipient_name or payload.customer_name}\n"
                f"جوال: {payload.recipient_phone or payload.customer_phone}\n"
                f"العنوان: {payload.recipient_address or 'يحدد لاحقاً'}\n"
                f"التاريخ: {payload.delivery_date} ({payload.delivery_time_slot})"
            )
            cursor.execute("""
            INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
            VALUES (?, ?, 'outbound', 'driver_alert', ?, 'delivered', ?)
            """, (driver_row['phone'], driver_row['name'], driver_msg, order_id))

    conn.commit()
    conn.close()

    # Asynchronous WhatsApp dispatches (after DB commit)
    if payload.customer_phone:
        dispatch_via_gateway_if_configured(payload.customer_phone, wa_msg)
    if assigned_florist and florist_msg:
        dispatch_via_gateway_if_configured(assigned_florist['phone'], florist_msg)
    if payload.driver_id and driver_row and driver_msg:
        dispatch_via_gateway_if_configured(driver_row['phone'], driver_msg)

    return {
        "success": True,
        "order_id": order_id,
        "order_number": order_number,
        "total_amount": total_amount,
        "invoice_number": invoice_number,
        "assigned_florist": {
            "id": assigned_florist["id"],
            "name": assigned_florist["name"],
            "phone": assigned_florist["phone"],
            "wa_me_link": florist_wa_link
        } if assigned_florist else None
    }

@router.put("/{order_id}/status")
def update_order_status(order_id: int, payload: OrderStatusUpdateSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    new_status = payload.status
    timestamp_clause = ""
    if new_status == "preparing":
        timestamp_clause = ", preparing_started_at = COALESCE(preparing_started_at, CURRENT_TIMESTAMP)"
    elif new_status == "ready":
        timestamp_clause = ", prepared_at = COALESCE(prepared_at, CURRENT_TIMESTAMP)"
    elif new_status == "delivered":
        timestamp_clause = ", delivered_at = COALESCE(delivered_at, CURRENT_TIMESTAMP)"

    cursor.execute(f"UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP{timestamp_clause} WHERE id = ?", (new_status, order_id))

    # Trigger automatic WhatsApp notification based on new status
    msg = None
    if new_status == "preparing":
        msg = (
            f"يا هلا فيك ✋🏻\n"
            f".\n"
            f"طلبكم رقم #{order['order_number']}\n"
            f"يتجهز الحين من أيادي منسقينا المحترفين 🌱✨\n"
            f".\n"
            f".\n"
            f"من اليوم أنت جزء من نبت | Nabt 🌱"
        )
    elif new_status == "ready":
        msg = f"تم تجهيز وتنسيق طلبكم الفاخر من الورد للطلب #{order['order_number']} وهي جاهزة للانطلاق للتسليم 🌸✨"
    elif new_status == "out_for_delivery":
        # المرحلة الثانية: استلام المندوب للطلب (بالطريق للتوصيل)
        msg = (
            f"يا هلا فيك ✋🏻\n"
            f".\n"
            f".\n"
            f"طلبكم رقم #{order['order_number']} بالطريق للتوصيل 🚗\n"
            f".\n"
            f"من اليوم أنت جزء من نبت | Nabt🌱"
        )
    elif new_status == "delivered":
        # المرحلة الثالثة: استلام الطلب
        msg = (
            f"سلمنا طلبك 🫱🏻‍🫲🏼\n"
            f".\n"
            f".\n"
            f"رقم #{order['order_number']} بنجاح\n"
            f".\n"
            f"شكراً لأنك اخترت نبت | Nabt"
        )
        # Update driver stats
        if order['driver_id']:
            cursor.execute("UPDATE drivers SET total_delivered = total_delivered + 1, status = 'available' WHERE id = ?", (order['driver_id'],))
        # Update customer spent if was unpaid and marked delivered with cash
        if order['payment_status'] == 'unpaid':
            cursor.execute("UPDATE orders SET payment_status = 'paid' WHERE id = ?", (order_id,))
            cursor.execute("UPDATE invoices SET status = 'paid', paid_amount = total_amount, remaining_amount = 0 WHERE order_id = ?", (order_id,))

    if msg:
        cursor.execute("""
        INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
        VALUES (?, ?, 'outbound', 'order_update', ?, 'delivered', ?)
        """, (order['customer_phone'], order['customer_name'], msg, order_id))

    conn.commit()
    conn.close()

    if msg and order['customer_phone']:
        dispatch_via_gateway_if_configured(order['customer_phone'], msg)

    return {"success": True, "status": new_status, "whatsapp_notified": bool(msg)}

@router.put("/{order_id}/assign-driver")
def assign_driver(order_id: int, payload: AssignDriverSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    cursor.execute("SELECT * FROM drivers WHERE id = ?", (payload.driver_id,))
    driver = cursor.fetchone()
    if not driver:
        conn.close()
        raise HTTPException(status_code=404, detail="Driver not found")

    cursor.execute("UPDATE orders SET driver_id = ?, status = 'out_for_delivery', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (payload.driver_id, order_id))
    cursor.execute("UPDATE drivers SET status = 'on_delivery' WHERE id = ?", (payload.driver_id,))

    # WhatsApp Driver Dispatch Message
    driver_msg = (
        f"مرحباً يا بطل {driver['name']} 🚗🌸\n"
        f"تم إسناد طلب جديد إليك برقم: #{order['order_number']}\n"
        f"المستلم: {order['recipient_name'] or order['customer_name']}\n"
        f"الهاتف: {order['recipient_phone'] or order['customer_phone']}\n"
        f"العنوان: {order['recipient_address']}\n"
        f"رابط الموقع: {order['location_url'] or 'لم يحدد'}\n"
        f"كرت الإهداء: {order['card_message'] or 'بدون كرت'}\n"
        f"الوقت: {order['delivery_date']} ({order['delivery_time_slot']})"
    )
    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
    VALUES (?, ?, 'outbound', 'driver_alert', ?, 'delivered', ?)
    """, (driver['phone'], driver['name'], driver_msg, order_id))

    # المرحلة الثانية: إشعار العميل باستلام المندوب للطلب
    cust_stage2_msg = (
        f"يا هلا فيك ✋🏻\n"
        f".\n"
        f".\n"
        f"طلبكم رقم #{order['order_number']} بالطريق للتوصيل 🚗\n"
        f".\n"
        f"من اليوم أنت جزء من نبت | Nabt🌱"
    )
    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
    VALUES (?, ?, 'outbound', 'order_update', ?, 'delivered', ?)
    """, (order['customer_phone'], order['customer_name'], cust_stage2_msg, order_id))

    conn.commit()
    conn.close()

    dispatch_via_gateway_if_configured(driver['phone'], driver_msg)
    if order['customer_phone']:
        dispatch_via_gateway_if_configured(order['customer_phone'], cust_stage2_msg)

    return {"success": True, "driver_name": driver["name"]}

@router.put("/{order_id}/assign-florist")
def assign_florist(order_id: int, payload: AssignFloristSchema):
    conn = get_db()
    cursor = conn.cursor()

    from routes.employees import sync_leaves_with_employee_status, check_employee_availability_on_date
    sync_leaves_with_employee_status(cursor)

    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="الطلب غير موجود")

    cursor.execute("SELECT * FROM employees WHERE id = ?", (payload.florist_id,))
    florist = cursor.fetchone()
    if not florist:
        conn.close()
        raise HTTPException(status_code=404, detail="المنسق غير موجود")

    # STRICT CHECK: Check availability on order delivery_date (both leave & weekly off day)
    target_date = order['delivery_date'] or date.today().strftime("%Y-%m-%d")
    is_avail, unavail_reason = check_employee_availability_on_date(cursor, payload.florist_id, target_date)
    if not is_avail:
        conn.close()
        raise HTTPException(status_code=400, detail=f"عذراً! {unavail_reason} يرجى اختيار منسق متواجد ومتاح للعمل في هذا اليوم.")

    cursor.execute("""
    UPDATE orders 
    SET florist_id = ?, 
        florist_assigned_at = CURRENT_TIMESTAMP, 
        florist_reminder_count = 0, 
        florist_reminded_at = NULL, 
        acceptance_status = 'pending',
        updated_at = CURRENT_TIMESTAMP 
    WHERE id = ?
    """, (payload.florist_id, order_id))

    # Fetch items for items_summary
    cursor.execute("SELECT product_name, quantity FROM order_items WHERE order_id = ?", (order_id,))
    o_items = cursor.fetchall()
    items_summary = " + ".join([f"{it['quantity']}x {it['product_name']}" for it in o_items]) if o_items else "تنسيق ورد"
    flower_colors_text = order['flower_colors'] or "تنسيق قياسي أنيق"
    card_text = order['card_message'] or "بدون كرت إهداء"
    slot_text = order['delivery_time_slot'] or "مسائي (4ع - 8م)"
    clean_slot = slot_text.strip()
    if clean_slot.startswith("(") and clean_slot.endswith(")"):
        clean_slot = clean_slot[1:-1].strip()
    notes_text = order['notes'] or "تنسيق قياسي أنيق"
    ref_text = "مرفقة في السيستم افتح تفاصيل الطلب لمطابقتها!" if order['reference_image'] else "بدون صورة (تنسيق نبت القياسي)"

    # Send WhatsApp notification to florist
    florist_msg = (
        f"🌸 مهمة تنسيق ورد جديد\n"
        f"مرحباً يا فنان {florist['name']}\n"
        f"تم إسناد طلب جديد إليك من الإدارة للتجهيز:\n"
        f"• رقم الطلب: #{order['order_number']}\n"
        f"• تفاصيل الطلب: {items_summary}\n"
        f"• 🎨 ألوان الورد والتغليف: {flower_colors_text}\n"
        f"• كرت الإهداء: \"{card_text}\"\n"
        f"• موعد التسليم: {order['delivery_date']} \n"
        f"• وقت التسليم({clean_slot})\n"
        f"• ملاحظات التجهيز: {notes_text}\n"
        f"• 📸 صورة (مساندة) مرجعية: {ref_text}\n\n"
        f"شد حيلك وأبدأ التجهيز وأكد لنا إذا جهز! 💐"
    )
    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
        VALUES (?, ?, 'outbound', 'florist_alert', ?, 'delivered', ?)
        """, (florist['phone'], florist['name'], florist_msg, order_id))

    conn.commit()
    conn.close()

    dispatch_via_gateway_if_configured(florist['phone'], florist_msg)
    return {"success": True, "florist_name": florist["name"]}

@router.delete("/all")
def clear_all_orders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM payments")
    cursor.execute("DELETE FROM invoices")
    cursor.execute("DELETE FROM order_items")
    cursor.execute("DELETE FROM orders")
    cursor.execute("DELETE FROM whatsapp_messages WHERE related_order_id IS NOT NULL")
    cursor.execute("UPDATE drivers SET total_delivered = 0, status = 'available' WHERE status != 'deleted'")
    cursor.execute("UPDATE employees SET active_orders_count = 0")
    cursor.execute("UPDATE customers SET orders_count = 0, total_spent = 0.0")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('orders', 'order_items', 'invoices', 'payments')")
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('clear_all_orders_v1', '1')")
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم حذف كافة الطلبات وتصفير الفواتير بنجاح"}

@router.delete("/{order_id}")
def cancel_or_delete_order(order_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
    cursor.execute("UPDATE invoices SET status = 'cancelled' WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Order marked as cancelled"}

# ========================================================
# WORKFLOW: FLORIST ACCEPTANCE & REJECTION / AUTO-FORWARD
# ========================================================

@router.put("/{order_id}/accept")
def accept_order(order_id: int, payload: OrderAcceptSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="الطلب غير موجود")

    cursor.execute("""
    UPDATE orders
    SET acceptance_status = 'accepted',
        status = 'preparing',
        accepted_at = CURRENT_TIMESTAMP,
        preparing_started_at = COALESCE(preparing_started_at, CURRENT_TIMESTAMP),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (order_id,))

    # Log internal notification / whatsapp alert
    florist_name = payload.florist_name or "المنسق"
    accept_msg = f"✅ تم قبول الطلب #{order['order_number']} بنجاح بواسطة المنسق ({florist_name}) وبدأ التنسيق والتجهيز 🌿"
    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
    VALUES ('0500475452', 'فيصل (الآدمن)', 'inbound', 'order_update', ?, 'delivered', ?)
    """, (accept_msg, order_id))

    cust_preparing_msg = None
    if order['customer_phone']:
        cust_preparing_msg = (
            f"يا هلا فيك ✋🏻\n"
            f".\n"
            f"طلبكم رقم #{order['order_number']}\n"
            f"يتجهز الحين من أيادي منسقينا المحترفين 🌱✨\n"
            f".\n"
            f".\n"
            f"من اليوم أنت جزء من نبت | Nabt 🌱"
        )
        cursor.execute("""
        INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
        VALUES (?, ?, 'outbound', 'order_update', ?, 'delivered', ?)
        """, (order['customer_phone'], order['customer_name'], cust_preparing_msg, order_id))

    conn.commit()
    conn.close()

    if cust_preparing_msg and order['customer_phone']:
        dispatch_via_gateway_if_configured(order['customer_phone'], cust_preparing_msg)

    return {"success": True, "message": "تم قبول الطلب وبدأ التنسيق بنجاح", "status": "preparing", "acceptance_status": "accepted"}

def parse_db_utc(dt_str):
    if not dt_str:
        return None
    s = str(dt_str).strip().replace("T", " ")
    if "." in s:
        s = s.split(".")[0]
    s = s.split("+")[0].split("Z")[0].strip()
    try:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None

def perform_florist_autoforward(order_id: int, reason: str, orig_florist_name: Optional[str] = None, conn=None) -> Optional[dict]:
    close_at_end = False
    if conn is None:
        conn = get_db()
        close_at_end = True
    cursor = conn.cursor()

    cursor.execute("SELECT o.*, e.name as current_florist_name, e.phone as current_florist_phone FROM orders o LEFT JOIN employees e ON o.florist_id = e.id WHERE o.id = ?", (order_id,))
    order = cursor.fetchone()
    if not order:
        if close_at_end:
            conn.close()
        return None

    orig_florist_id = order['florist_id']
    orig_name = orig_florist_name or order['current_florist_name'] or "عمر"

    from routes.employees import check_employee_availability_on_date
    delivery_date = order['delivery_date'] or date.today().strftime("%Y-%m-%d")

    # Find other available florist (Omar <-> Rico auto-switch)
    SELECT_QUERY = """
    SELECT * FROM employees
    WHERE role = 'florist' AND id != ?
    ORDER BY active_orders_count ASC, id ASC
    """
    cursor.execute(SELECT_QUERY, (orig_florist_id or 0,))
    candidates = cursor.fetchall()
    
    # Filter candidates by availability on delivery_date
    available_candidates = []
    for cand in candidates:
        is_avail, _ = check_employee_availability_on_date(cursor, cand['id'], delivery_date)
        if is_avail:
            available_candidates.append(dict(cand))

    next_florist = None
    # If orig is Omar, prefer Rico; if orig is Rico, prefer Omar
    for cand_dict in available_candidates:
        if "عمر" in orig_name and "ريكو" in cand_dict['name']:
            next_florist = cand_dict
            break
        elif "ريكو" in orig_name and "عمر" in cand_dict['name']:
            next_florist = cand_dict
            break
    if not next_florist and available_candidates:
        next_florist = available_candidates[0]

    new_florist_id = next_florist['id'] if next_florist else None
    new_florist_name = next_florist['name'] if next_florist else "منسق احتياطي"

    # Update order with rejection history and auto-forward to next florist
    cursor.execute("""
    UPDATE orders
    SET acceptance_status = 'auto_forwarded',
        previous_florist_id = ?,
        florist_id = ?,
        florist_assigned_at = CURRENT_TIMESTAMP,
        florist_reminder_count = 0,
        florist_reminded_at = NULL,
        rejected_at = CURRENT_TIMESTAMP,
        rejection_reason = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (orig_florist_id, new_florist_id, reason, order_id))

    # Send Notification / WhatsApp Alert to All 3 Managers (Yasser, Faisal, Nader)
    alert_text = (
        f"🚨 إشعار عاجل لإدارة نبت (ياسر / فيصل / نادر)!\n"
        f"المنسق ({orig_name}) لم يقبل الطلب رقم #{order['order_number']}.\n"
        f"السبب: {reason}\n"
        f"🔄 تم تحويل الطلب تلقائياً إلى المنسق البديل: ({new_florist_name}) لمباشرته فوراً!"
    )

    # 1. Alert Yasser (General Manager)
    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
    VALUES ('0500000001', 'ياسر (المدير العام)', 'outbound', 'florist_alert', ?, 'delivered', ?)
    """, (alert_text, order_id))

    # 2. Alert Faisal (Operations Manager)
    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
    VALUES ('0500475452', 'فيصل (مدير تشغيلي)', 'outbound', 'florist_alert', ?, 'delivered', ?)
    """, (alert_text, order_id))

    # 3. Alert Nader (Branch Manager)
    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
    VALUES ('0502220002', 'نادر (مدير فرع)', 'outbound', 'florist_alert', ?, 'delivered', ?)
    """, (alert_text, order_id))

    # 4. Dispatch to new florist (Rico or Omar)
    florist_msg = None
    if next_florist:
        cursor.execute("SELECT product_name, quantity FROM order_items WHERE order_id = ?", (order_id,))
        o_items = cursor.fetchall()
        items_summary = " + ".join([f"{it['quantity']}x {it['product_name']}" for it in o_items]) if o_items else "تنسيق ورد"
        flower_colors_text = order['flower_colors'] or "تنسيق قياسي أنيق"
        card_text = order['card_message'] or "بدون كرت إهداء"
        slot_text = order['delivery_time_slot'] or "مسائي (4ع - 8م)"
        clean_slot = slot_text.strip()
        if clean_slot.startswith("(") and clean_slot.endswith(")"):
            clean_slot = clean_slot[1:-1].strip()
        notes_text = order['notes'] or "تنسيق قياسي أنيق"
        ref_text = "مرفقة في السيستم افتح تفاصيل الطلب لمطابقتها!" if order['reference_image'] else "بدون صورة (تنسيق نبت القياسي)"

        florist_msg = (
            f"🌸 مهمة تنسيق ورد جديد (محول تلقائياً)\n"
            f"مرحباً يا فنان {new_florist_name}\n"
            f"تم إسناد طلب جديد إليك من الإدارة للتجهيز:\n"
            f"• رقم الطلب: #{order['order_number']}\n"
            f"• تفاصيل الطلب: {items_summary}\n"
            f"• 🎨 ألوان الورد والتغليف: {flower_colors_text}\n"
            f"• كرت الإهداء: \"{card_text}\"\n"
            f"• موعد التسليم: {order['delivery_date']} \n"
            f"• وقت التسليم({clean_slot})\n"
            f"• ملاحظات التجهيز: {notes_text} (محول بعد تعذر {orig_name})\n"
            f"• 📸 صورة (مساندة) مرجعية: {ref_text}\n\n"
            f"شد حيلك وأبدأ التجهيز وأكد لنا إذا جهز! 💐"
        )
        cursor.execute("""
        INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
        VALUES (?, ?, 'outbound', 'florist_alert', ?, 'delivered', ?)
        """, (next_florist['phone'], new_florist_name, florist_msg, order_id))

    conn.commit()

    if next_florist and florist_msg:
        dispatch_via_gateway_if_configured(next_florist['phone'], florist_msg)

    res = {
        "success": True,
        "message": f"لم يتم قبول الطلب من {orig_name} وتم إرسال إشعار للمدراء (ياسر، فيصل، نادر) وتحويل الطلب تلقائياً إلى ({new_florist_name}) 🌸",
        "new_florist_name": new_florist_name,
        "alert_text": alert_text
    }
    if close_at_end:
        conn.close()
    return res

def check_and_process_florist_timeouts():
    conn = get_db()
    cursor = conn.cursor()
    now_utc = datetime.now(timezone.utc)

    cursor.execute("""
        SELECT o.*, e.name as current_florist_name, e.phone as current_florist_phone
        FROM orders o
        JOIN employees e ON o.florist_id = e.id
        WHERE o.status = 'new'
          AND (o.acceptance_status IS NULL OR o.acceptance_status != 'accepted')
          AND o.florist_id IS NOT NULL
    """)
    orders = cursor.fetchall()
    actions_taken = []

    for row in orders:
        ord_dict = dict(row)
        order_id = ord_dict['id']
        assigned_time_str = ord_dict.get('florist_assigned_at') or ord_dict.get('received_at') or ord_dict.get('created_at')
        assigned_dt = parse_db_utc(assigned_time_str)
        if not assigned_dt:
            continue

        elapsed_sec = (now_utc - assigned_dt).total_seconds()
        reminded_at_str = ord_dict.get('florist_reminded_at')
        reminded_dt = parse_db_utc(reminded_at_str) if reminded_at_str else None
        reminder_count = ord_dict.get('florist_reminder_count') or 0

        # Condition 2: 3 minutes after 2nd reminder (or 6 minutes total without acceptance) -> Auto-Forward to next florist!
        should_forward = False
        if reminder_count >= 1:
            if reminded_dt and (now_utc - reminded_dt).total_seconds() >= 180:
                should_forward = True
            elif elapsed_sec >= 360:
                should_forward = True
        elif elapsed_sec >= 360:
            should_forward = True

        if should_forward:
            reason = "عدم قبول الطلب وتجاوز مهلة الـ 6 دقائق (التنبيه الأول والتنبيه الثاني)"
            fwd_res = perform_florist_autoforward(order_id, reason, ord_dict.get('current_florist_name'), conn=conn)
            if fwd_res:
                actions_taken.append({
                    "order_id": order_id,
                    "action": "auto_forwarded",
                    "details": fwd_res
                })
            continue

        # Condition 1: 3 minutes elapsed since assignment and 2nd reminder not yet sent -> Send Second Alert to florist!
        if elapsed_sec >= 180 and reminder_count == 0:
            cursor.execute("SELECT product_name, quantity FROM order_items WHERE order_id = ?", (order_id,))
            o_items = cursor.fetchall()
            items_summary = " + ".join([f"{it['quantity']}x {it['product_name']}" for it in o_items]) if o_items else "تنسيق ورد"
            clean_slot = (ord_dict.get('delivery_time_slot') or "مسائي (4ع - 8م)").strip()
            if clean_slot.startswith("(") and clean_slot.endswith(")"):
                clean_slot = clean_slot[1:-1].strip()

            reminder_msg = (
                f"⚠️ تنبيه عاجل وتذكير ثانٍ يا فنان {ord_dict['current_florist_name']} 🌸\n"
                f"لديك طلب جديد رقم #{ord_dict['order_number']} بانتظار قبولك منذ 3 دقائق!\n"
                f"• تفاصيل الطلب: {items_summary}\n"
                f"• موعد التسليم: {ord_dict['delivery_date']} ({clean_slot})\n\n"
                f"⏳ متبقي 3 دقائق فقط لقبول الطلب عبر السيستم قبل أن يتم تحويله تلقائياً لمنسق آخر وإشعار إدارة نبت! 💐"
            )

            # Insert WhatsApp message for florist
            cursor.execute("""
            INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
            VALUES (?, ?, 'outbound', 'florist_alert', ?, 'delivered', ?)
            """, (ord_dict['current_florist_phone'], ord_dict['current_florist_name'], reminder_msg, order_id))

            # Operational alert for Faisal (Operations Manager)
            manager_notice = (
                f"⚠️ متابعة مهام: تم إرسال التنبيه الثاني للمنسق ({ord_dict['current_florist_name']}) "
                f"للطلب #{ord_dict['order_number']} لمرور 3 دقائق دون قبول. المهلة المتبقية للتحويل التلقائي: 3 دقائق."
            )
            cursor.execute("""
            INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
            VALUES ('0500475452', 'فيصل (مدير تشغيلي)', 'outbound', 'florist_alert', ?, 'delivered', ?)
            """, (manager_notice, order_id))

            cursor.execute("""
            UPDATE orders
            SET florist_reminder_count = 1,
                florist_reminded_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (order_id,))
            conn.commit()

            if ord_dict.get('current_florist_phone'):
                dispatch_via_gateway_if_configured(ord_dict['current_florist_phone'], reminder_msg)

            actions_taken.append({
                "order_id": order_id,
                "action": "second_reminder_sent",
                "florist": ord_dict['current_florist_name']
            })

    conn.close()
    return actions_taken

@router.post("/check-florist-timeouts")
def trigger_check_florist_timeouts():
    actions = check_and_process_florist_timeouts()
    return {"success": True, "actions_taken": actions}

@router.put("/{order_id}/reject")
def reject_and_autoforward_order(order_id: int, payload: OrderRejectSchema):
    res = perform_florist_autoforward(order_id, payload.reason or "المنسق مشغول بطلبات حالية", payload.florist_name)
    if not res:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    return res

# ========================================================
# WORKFLOW: FLORIST COMPLETE WORK + PHOTO UPLOAD
# ========================================================

@router.put("/{order_id}/complete-work")
def complete_florist_work(order_id: int, payload: OrderCompleteWorkSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="الطلب غير موجود")

    final_image_url = (payload.completed_image or "").strip()

    # If image was passed as base64 string, decode and save to file cleanly on disk
    if final_image_url.startswith("data:image/"):
        import base64
        try:
            header, encoded = final_image_url.split(",", 1)
            ext = ".jpg"
            if "png" in header:
                ext = ".png"
            elif "webp" in header:
                ext = ".webp"
            img_bytes = base64.b64decode(encoded)
            unique_name = f"done_{uuid.uuid4().hex[:12]}{ext}"
            uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static", "uploads", "orders")
            os.makedirs(uploads_dir, exist_ok=True)
            target_path = os.path.join(uploads_dir, unique_name)
            with open(target_path, "wb") as f:
                f.write(img_bytes)
            final_image_url = f"/static/uploads/orders/{unique_name}"
        except Exception as e:
            print("Failed to decode base64 completed image:", e)

    cursor.execute("""
    UPDATE orders
    SET completed_image = ?,
        completed_at = CURRENT_TIMESTAMP,
        prepared_at = CURRENT_TIMESTAMP,
        approval_status = 'pending',
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (final_image_url, order_id))

    # Send Notification for Approval to All 3 Managers (Yasser, Faisal, Nader)
    approval_alert = (
        f"📸 انتهى المنسق من تجهيز وتنسيق الطلب #{order['order_number']} وقام برفع صورة المنتج الفعلي!\n"
        f"الطلب بانتظار التعميد والاعتماد من (ياسر / فيصل / نادر) قبل تسليمه للمندوب 🚗✨"
    )

    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
    VALUES ('0500000001', 'ياسر (المدير العام)', 'outbound', 'order_update', ?, 'delivered', ?)
    """, (approval_alert, order_id))

    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
    VALUES ('0500475452', 'فيصل (مدير تشغيلي)', 'outbound', 'order_update', ?, 'delivered', ?)
    """, (approval_alert, order_id))

    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
    VALUES ('0502220002', 'نادر (مدير فرع)', 'outbound', 'order_update', ?, 'delivered', ?)
    """, (approval_alert, order_id))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "تم رفع صورة الورد بنجاح، وتم إرسال طلب التعميد إلى المدراء (ياسر، فيصل، نادر) للموافقة",
        "completed_image": final_image_url
    }

# ========================================================
# WORKFLOW: ADMIN / MANAGER APPROVAL (التعميد)
# ========================================================

@router.put("/{order_id}/approve")
def approve_completed_order(order_id: int, payload: OrderApproveSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="الطلب غير موجود")

    if payload.action == "approve":
        cursor.execute("""
        UPDATE orders
        SET approval_status = 'approved',
            approved_by = ?,
            approved_at = CURRENT_TIMESTAMP,
            approval_notes = ?,
            status = 'ready',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (payload.approved_by, payload.notes or "تم التعميد والموافقة على التنسيق بنجاح ✅", order_id))

        msg = f"✨ تم تعميد واعتماد الطلب #{order['order_number']} بنجاح بواسطة ({payload.approved_by})! الطلب الآن جاهز ومتاح للتواصل مع المناديب للتوصيل 🚗"
    else:
        cursor.execute("""
        UPDATE orders
        SET approval_status = 'revision_requested',
            status = 'preparing',
            approval_notes = ?,
            approved_by = ?,
            notes = COALESCE(notes, '') || ' [ملاحظات التعديل: ' || ? || ']',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (payload.notes or "يرجى تعديل التنسيق", payload.approved_by, payload.notes or "يرجى تعديل التنسيق", order_id))

        msg = f"⚠️ تم إرجاع الطلب #{order['order_number']} بملاحظات تعديل من قبل ({payload.approved_by}): {payload.notes or 'يرجى مراجعة التنسيق'}"

        # إشعار منسق الورد المعين عبر الواتساب فوراً
        if order['florist_id']:
            cursor.execute("SELECT name, phone FROM employees WHERE id = ?", (order['florist_id'],))
            florist = cursor.fetchone()
            if florist and florist['phone']:
                florist_alert = (
                    f"⚠️ تنبيه من الإدارة ({payload.approved_by})\n"
                    f"مرحباً يا فنان {florist['name']} 🌸\n"
                    f"تم إرجاع الطلب #{order['order_number']} لوجود ملاحظات تعديل:\n"
                    f"📝 «{payload.notes or 'يرجى مراجعة التنسيق'}»\n\n"
                    f"يرجى فتح الطلب بالسيستم، وتعديل التنسيق ثم رفع الصورة الجديدة! 💐"
                )
                cursor.execute("""
                INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
                VALUES (?, ?, 'outbound', 'order_update', ?, 'delivered', ?)
                """, (florist['phone'], florist['name'], florist_alert, order_id))
                conn.commit()
                conn.close()
                dispatch_via_gateway_if_configured(florist['phone'], florist_alert)
                return {
                    "success": True,
                    "action": payload.action,
                    "approved_by": payload.approved_by,
                    "message": msg
                }

    conn.commit()
    conn.close()

    return {
        "success": True,
        "action": payload.action,
        "approved_by": payload.approved_by,
        "message": msg
    }
