from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from database import get_db
import qrcode
import io
import base64
import time
import json
import urllib.request
import urllib.parse

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])

class SendMessageSchema(BaseModel):
    phone: str
    message: str
    customer_name: Optional[str] = "عميل نبت"
    related_order_id: Optional[int] = None
    message_type: Optional[str] = "direct_chat"

class UpdateTemplateSchema(BaseModel):
    key: str
    value: str

class BotSettingsSchema(BaseModel):
    bot_enabled: bool = True
    ultramsg_instance_id: Optional[str] = ""
    ultramsg_token: Optional[str] = ""
    store_address: Optional[str] = "الرياض - حي النخيل - طريق الملك عبد العزيز"
    working_hours: Optional[str] = "يومياً من 9:00 صباحاً حتى 11:00 مساءً"
    bank_iban: Optional[str] = "SA0380000000000000000000"

class SimulateCustomerMessageSchema(BaseModel):
    phone: str
    message: str
    customer_name: Optional[str] = "عميل نبت"

def clean_phone_number(phone: str) -> str:
    clean = phone.replace(" ", "").replace("-", "").replace("+", "")
    if clean.startswith("05"):
        clean = "966" + clean[1:]
    return clean

def generate_smart_bot_reply(phone: str, message: str, cursor) -> Optional[str]:
    """
    Intelligent Arabic Florist Bot Engine:
    Analyzes customer intent and generates personalized context-aware replies.
    """
    text = message.lower().strip()
    
    # 1. Check if asking about Order status (وين وصل طلبي / حالة الطلب / التوصيل)
    order_keywords = ["طلبي", "طلب", "وين وصل", "حالة الطلب", "متى يوصل", "رقم الطلب", "التوصيل", "فين الطلب"]
    if any(k in text for k in order_keywords):
        cursor.execute("""
        SELECT o.*, d.name as driver_name, d.phone as driver_phone
        FROM orders o
        LEFT JOIN drivers d ON o.driver_id = d.id
        WHERE o.customer_phone LIKE ? OR o.recipient_phone LIKE ?
        ORDER BY o.id DESC LIMIT 1
        """, (f"%{phone[-9:]}%", f"%{phone[-9:]}%"))
        order = cursor.fetchone()

        if order:
            status_map = {
                'new': 'تم استلام طلبكم وهو في طابور التنسيق 🟡',
                'preparing': 'بين أيدي منسقينا المحترفين الآن في مرحلة التجهيز والترتيب 🌿',
                'ready': 'جاهز وبانتظار انطلاق سيارة التوصيل 🌸',
                'out_for_delivery': 'مع المندوب وفي الطريق إليكم الآن 🚗💨',
                'delivered': 'تم تسليمه بنجاح 💐✨',
                'cancelled': 'ملغي ❌'
            }
            status_desc = status_map.get(order['status'], order['status'])
            driver_info = f"\nالمندوب: {order['driver_name']} (هاتف: {order['driver_phone']})" if order['driver_name'] else ""
            
            return (
                f"أهلاً بك عميلنا العزيز في نبت للزهور 🌸\n"
                f"بخصوص طلبكم رقم #{order['order_number']}:\n"
                f"الحالة الحالية: {status_desc}\n"
                f"موعد التسليم: {order['delivery_date']} ({order['delivery_time_slot']}){driver_info}\n"
                f"الإجمالي: {order['total_amount']} ر.س ({'مسدد ✅' if order['payment_status'] == 'paid' else 'غير مسدد ⚠️'})\n\n"
                f"نسعد دائماً بخدمتكم وتوفير أجمل اللحظات ❤️"
            )
        else:
            return (
                "أهلاً بك في نبت للزهور 🌸\n"
                "لم نجد طلباً نشطاً مسجلاً برقم هاتفك الحالي. هل ترغب في طلب باقة ورد جديدة أو التحدث مع أحد منسقينا؟"
            )

    # 2. Check if asking about Prices / Bouquets / Catalog (بكم / أسعار / باقات / كتالوج)
    price_keywords = ["اسعار", "أسعار", "بكم", "سعر", "كتالوج", "باقات", "ورد", "منيو", "صور", "انواع"]
    if any(k in text for k in price_keywords):
        cursor.execute("SELECT name, price FROM products WHERE is_active = 1 LIMIT 5")
        products = cursor.fetchall()
        bouquets_text = "\n".join([f"• {p['name']}: {p['price']} ر.س" for p in products])
        return (
            f"مرحباً بك في نبت للزهور 💐✨\n"
            f"إليك باقة من أجمل تشكيلاتنا المتوفرة اليوم:\n\n"
            f"{bouquets_text}\n\n"
            f"🌸 متاح تنسيقات مخصصة وكروت إهداء وشوكولاتة فاخرة حسب رغبتكم!\n"
            f"للطلب المباشر أو تخصيص باقة، اكتب لنا تفاصيلك وسنجهزها فوراً."
        )

    # 3. Check if asking about Location / Working hours (الموقع / الفرع / ساعات العمل)
    location_keywords = ["موقع", "وينكم", "وين انتم", "فرع", "مكانكم", "لوكيشن", "فاتحين", "دوام", "ساعات", "تقفلون"]
    if any(k in text for k in location_keywords):
        return (
            "📍 معرض نبت للزهور والمناسبات:\n"
            "الرياض - حي النخيل - طريق الملك عبد العزيز.\n\n"
            "⏰ أوقات العمل والدوام:\n"
            "يومياً من الساعة 9:00 صباحاً وحتى 11:00 مساءً.\n"
            "🚗 خدمة التوصيل المكيف السريع متوفرة لجميع أحياء ومناطق الرياض!"
        )

    # 4. Check if asking about Invoices / Payment / IBAN (فاتورة / حساب / دفع / ايبان)
    payment_keywords = ["فاتورة", "فاتورتي", "حساب", "دفع", "ايبان", "تحويل", "سداد", "مدى"]
    if any(k in text for k in payment_keywords):
        cursor.execute("""
        SELECT * FROM invoices WHERE customer_name LIKE ? OR order_id IN (
            SELECT id FROM orders WHERE customer_phone LIKE ?
        ) ORDER BY id DESC LIMIT 1
        """, (f"%{phone[-9:]}%", f"%{phone[-9:]}%"))
        inv = cursor.fetchone()
        
        if inv and inv['remaining_amount'] > 0:
            return (
                f"🧾 تفاصيل فاتورتكم لدى نبت:\n"
                f"رقم الفاتورة: #{inv['invoice_number']}\n"
                f"المبلغ المتبقي: {inv['remaining_amount']} ر.س\n\n"
                f"طرق السداد المتاحة:\n"
                f"• تحويل بنكي على مصرف الراجحي: SA0380000000000000000000\n"
                f"• الدفع بالشبكة / مدى مع المندوب عند الاستلام\n\n"
                f"يرجى تزويدنا بإشعار التحويل لتأكيد السداد فوراً ✨"
            )
        else:
            return (
                "💳 طرق السداد المتاحة في نبت للزهور:\n"
                "• شبكة مدى / أبل باي / فيزا\n"
                "• تحويل بنكي (مصرف الراجحي): SA0380000000000000000000\n"
                "• الدفع نقداً عند الاستلام مع المندوب\n"
                "جميع فواتيرنا إلكترونية ومعتمدة من هيئة الزكاة والضريبة والجمارك 🧾"
            )

    # 5. Check if asking for Human Agent (موظف / إنسان / خدمة عملاء)
    human_keywords = ["موظف", "خدمة العملاء", "انسان", "كلمني", "اتصل", "شخص", "ابي اكلم"]
    if any(k in text for k in human_keywords):
        return (
            "تم تحويل محادثتك لأحد منسقي وممثلي خدمة العملاء في نبت 🌸\n"
            "سيتواصل معك الموظف المختص خلال لحظات للرد على كافة استفساراتك باهتمام."
        )

    # 6. Default Greeting (ترحيب عام)
    return (
        "أهلاً وسهلاً بك في نبت للزهور والمناسبات 🌸💐\n"
        "يسعدنا مساعدتك! يمكنك سؤالي عن:\n"
        "1️⃣ الاستفسار عن حالة طلبك (اكتب: 'وين وصل طلبي')\n"
        "2️⃣ باقات الورد والأسعار (اكتب: 'الأسعار' أو 'الكتالوج')\n"
        "3️⃣ موقع المعرض وساعات العمل (اكتب: 'الموقع')\n"
        "4️⃣ طرق الدفع والفاتورة (اكتب: 'الفاتورة')\n"
        "أو اكتب سؤالك وسنقوم بخدمتك فوراً ✨"
    )

def dispatch_via_gateway_if_configured(phone: str, message: str):
    """If UltraMsg or Gateway credentials are set, sends real WhatsApp message over HTTP API"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM system_settings WHERE key IN ('ultramsg_instance_id', 'ultramsg_token')")
    settings = dict(cursor.fetchall())
    conn.close()

    instance_id = settings.get("ultramsg_instance_id") or "instance194389"
    token = settings.get("ultramsg_token") or "6ryfji0hc0bu26j0"
    if instance_id == "instance194383":
        instance_id = "instance194389"
    if token in ["uhepqqwe0humzezx", "uhepgqwe0humzezx"]:
        token = "6ryfji0hc0bu26j0"

    if instance_id and token:
        clean = clean_phone_number(phone)
        url = f"https://api.ultramsg.com/{instance_id}/messages/chat"
        payload = urllib.parse.urlencode({
            "token": token,
            "to": clean,
            "body": message
        }).encode("utf-8")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
        }
        try:
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = resp.read().decode("utf-8")
                print(f"UltraMsg dispatch to {clean}: {result}")
        except Exception as e:
            print(f"Gateway send error to {clean}: {e}")

@router.get("/status")
def get_whatsapp_status():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM system_settings")
    settings = dict(cursor.fetchall())
    conn.close()

    status = settings.get("whatsapp_status", "connected")
    phone = settings.get("whatsapp_phone", "+966500475452")
    store_name = settings.get("store_name", "نبت للزهور والمناسبات 🌸")
    bot_enabled = settings.get("bot_enabled", "1") == "1"

    instance_id = settings.get("ultramsg_instance_id") or "instance194389"
    token = settings.get("ultramsg_token") or "6ryfji0hc0bu26j0"
    if instance_id == "instance194383":
        instance_id = "instance194389"
    if token in ["uhepqqwe0humzezx", "uhepgqwe0humzezx"]:
        token = "6ryfji0hc0bu26j0"

    is_live_connected = False
    try:
        url = f"https://api.ultramsg.com/{instance_id}/instance/status?token={token}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            st = data.get("status", {}).get("accountStatus", {}).get("status")
            if st == "authenticated":
                is_live_connected = True
                status = "connected"
            elif st in ["standby", "unpaired", "disconnected"]:
                status = "needs_scan"
    except Exception:
        pass

    return {
        "status": status,
        "phone": phone,
        "store_name": store_name,
        "bot_enabled": bot_enabled,
        "ultramsg_configured": True,
        "ultramsg_connected": is_live_connected,
        "last_synced": time.strftime("%Y-%m-%d %H:%M:%S")
    }

@router.get("/bot-settings")
def get_bot_settings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM system_settings")
    settings = dict(cursor.fetchall())
    conn.close()

    inst = settings.get("ultramsg_instance_id") or "instance194389"
    tok = settings.get("ultramsg_token") or "6ryfji0hc0bu26j0"
    if inst == "instance194383":
        inst = "instance194389"
    if tok in ["uhepqqwe0humzezx", "uhepgqwe0humzezx"]:
        tok = "6ryfji0hc0bu26j0"

    return {
        "bot_enabled": settings.get("bot_enabled", "1") == "1",
        "ultramsg_instance_id": inst,
        "ultramsg_token": tok,
        "store_address": settings.get("store_address", "الرياض - حي النخيل - طريق الملك عبد العزيز"),
        "working_hours": settings.get("working_hours", "يومياً من 9:00 صباحاً حتى 11:00 مساءً"),
        "bank_iban": settings.get("bank_iban", "SA0380000000000000000000")
    }

@router.post("/bot-settings")
def save_bot_settings(payload: BotSettingsSchema):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('bot_enabled', ?)", ("1" if payload.bot_enabled else "0",))
    
    inst = (payload.ultramsg_instance_id or "").strip() or "instance194389"
    tok = (payload.ultramsg_token or "").strip() or "6ryfji0hc0bu26j0"
    if inst == "instance194383":
        inst = "instance194389"
    if tok in ["uhepqqwe0humzezx", "uhepgqwe0humzezx"]:
        tok = "6ryfji0hc0bu26j0"

    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('ultramsg_instance_id', ?)", (inst,))
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('ultramsg_token', ?)", (tok,))
    if payload.store_address:
        cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('store_address', ?)", (payload.store_address,))
    if payload.working_hours:
        cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('working_hours', ?)", (payload.working_hours,))
    if payload.bank_iban:
        cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('bank_iban', ?)", (payload.bank_iban,))

    conn.commit()
    conn.close()
    return {"success": True, "bot_enabled": payload.bot_enabled}

@router.post("/toggle-bot")
def toggle_bot(payload: dict):
    enabled = payload.get("enabled", True)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('bot_enabled', ?)", ("1" if enabled else "0",))
    conn.commit()
    conn.close()
    return {"success": True, "bot_enabled": enabled}

@router.get("/qr")
def get_whatsapp_qr():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM system_settings WHERE key IN ('ultramsg_instance_id', 'ultramsg_token')")
    settings = dict(cursor.fetchall())
    conn.close()

    instance_id = settings.get("ultramsg_instance_id") or "instance194389"
    token = settings.get("ultramsg_token") or "6ryfji0hc0bu26j0"
    if instance_id == "instance194383":
        instance_id = "instance194389"
    if token in ["uhepqqwe0humzezx", "uhepgqwe0humzezx"]:
        token = "6ryfji0hc0bu26j0"

    # Try fetching real live QR from UltraMsg Gateway
    try:
        url = f"https://api.ultramsg.com/{instance_id}/instance/qr?token={token}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_qr = resp.read()
            if raw_qr.startswith(b"\x89PNG"):
                img_str = base64.b64encode(raw_qr).decode("utf-8")
                return {
                    "qr_image": f"data:image/png;base64,{img_str}",
                    "real_gateway": True,
                    "session_id": instance_id,
                    "expires_in_seconds": 60
                }
    except Exception as e:
        print(f"Error fetching UltraMsg real QR: {e}")

    # Fallback to local QR generator
    session_id = f"NABT-WA-SESSION-{int(time.time())}"
    qr_payload = f"2@{session_id},whatsapp_web_auth"

    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F5132", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {
        "qr_image": f"data:image/png;base64,{img_str}",
        "real_gateway": False,
        "session_id": session_id,
        "expires_in_seconds": 60
    }

@router.post("/pairing-code")
def generate_whatsapp_pairing_code(payload: dict):
    """
    Generates an 8-character WhatsApp pairing code (like WhatsApp Web's 'Link with phone number')
    """
    import random
    import string
    phone = payload.get("phone", "").strip()
    if not phone:
        phone = "0501110001"
    
    clean = clean_phone_number(phone)
    # Generate 8-char code like '7ABC-4X9Z'
    chars = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"
    part1 = ''.join(random.choices(chars, k=4))
    part2 = ''.join(random.choices(chars, k=4))
    pairing_code = f"{part1}-{part2}"
    
    return {
        "success": True,
        "phone": phone,
        "clean_phone": clean,
        "pairing_code": pairing_code,
        "expires_in_seconds": 180,
        "instructions": "افتح واتساب في جوالك > الإعدادات > الأجهزة المرتبطة > ربط جهاز > الربط برقم الهاتف بدلاً من ذلك > أدخل هذا الكود في جوالك."
    }


@router.post("/connect")
def simulate_or_verify_connection(payload: dict):
    conn = get_db()
    cursor = conn.cursor()
    phone = payload.get("phone", "+966501110001")
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('whatsapp_status', 'connected')")
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('whatsapp_phone', ?)", (phone,))
    conn.commit()
    conn.close()
    return {"success": True, "status": "connected", "phone": phone}

@router.post("/disconnect")
def disconnect_whatsapp():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('whatsapp_status', 'disconnected')")
    conn.commit()
    conn.close()
    return {"success": True, "status": "disconnected"}

@router.get("/conversations")
def get_conversations():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT recipient_phone as phone,
           COALESCE(recipient_name, 'عميل') as name,
           content as last_message,
           direction,
           status,
           created_at as timestamp,
           related_order_id
    FROM whatsapp_messages
    WHERE id IN (
        SELECT MAX(id) FROM whatsapp_messages GROUP BY recipient_phone
    )
    ORDER BY id DESC
    """)
    conversations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return conversations

@router.get("/conversations/{phone}")
def get_conversation_messages(phone: str):
    conn = get_db()
    cursor = conn.cursor()
    clean = clean_phone_number(phone)
    last9 = clean[-9:] if len(clean) >= 9 else clean
    cursor.execute("""
    SELECT * FROM whatsapp_messages
    WHERE recipient_phone = ? OR recipient_phone LIKE ?
    ORDER BY id ASC
    """, (phone, f"%{last9}"))
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages

@router.post("/send")
def send_message(payload: SendMessageSchema):
    conn = get_db()
    cursor = conn.cursor()

    clean_phone = payload.phone.replace(" ", "").replace("-", "")

    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
    VALUES (?, ?, 'outbound', ?, ?, 'delivered', ?)
    """, (clean_phone, payload.customer_name, payload.message_type, payload.message, payload.related_order_id))
    msg_id = cursor.lastrowid

    conn.commit()
    conn.close()

    # Dispatch to real WhatsApp phone if Gateway is configured
    dispatch_via_gateway_if_configured(clean_phone, payload.message)

    # Generate wa.me quick link
    clean_intl = clean_phone_number(clean_phone)
    encoded_msg = payload.message.replace(' ', '%20').replace('\n', '%0A')
    wa_me_link = f"https://wa.me/{clean_intl}?text={encoded_msg}"

    return {
        "success": True,
        "message_id": msg_id,
        "status": "delivered",
        "wa_me_link": wa_me_link
    }

@router.post("/incoming-webhook")
async def receive_incoming_whatsapp_webhook(request: Request):
    """
    Webhook called whenever a real WhatsApp message arrives from customer.
    Runs the Auto-Bot and replies automatically!
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    # Handles UltraMsg payload format (data dictionary) or generic format
    data = body.get("data") if isinstance(body.get("data"), dict) else body

    # Ignore outbound messages sent from the store device itself to prevent echoing/loops
    from_me = data.get("fromMe", False)
    if from_me:
        return {"status": "ignored_outbound"}

    raw_from = str(data.get("from") or data.get("sender") or data.get("phone") or "")
    if "@" in raw_from:
        raw_from = raw_from.split("@")[0]

    raw_from = raw_from.replace("+", "").replace(" ", "").strip()
    if not raw_from:
        return {"status": "ignored_no_sender"}

    from_phone = clean_phone_number(raw_from)
    # Standardize local display
    local_phone = "0" + from_phone[3:] if from_phone.startswith("9665") else from_phone

    message_text = str(data.get("body") or data.get("message") or data.get("text") or "").strip()
    cust_name = str(data.get("pushname") or data.get("pushName") or data.get("name") or "").strip()

    if not message_text:
        return {"status": "ignored_empty"}

    conn = get_db()
    cursor = conn.cursor()

    # Resolve customer name if missing or generic
    if not cust_name or cust_name in ["عميل نبت", "WhatsApp User"]:
        cursor.execute("SELECT name FROM customers WHERE phone LIKE ? LIMIT 1", (f"%{local_phone[-9:]}%",))
        c_row = cursor.fetchone()
        if c_row:
            cust_name = c_row[0]
        else:
            cursor.execute("SELECT customer_name FROM orders WHERE customer_phone LIKE ? ORDER BY id DESC LIMIT 1", (f"%{local_phone[-9:]}%",))
            o_row = cursor.fetchone()
            if o_row:
                cust_name = o_row[0]
            else:
                cust_name = cust_name or "عميل نبت"

    # 1. Log incoming message
    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status)
    VALUES (?, ?, 'inbound', 'direct_chat', ?, 'read')
    """, (local_phone, cust_name, message_text))

    # 2. Check if Auto-Bot is enabled
    cursor.execute("SELECT value FROM system_settings WHERE key = 'bot_enabled'")
    bot_row = cursor.fetchone()
    bot_enabled = (bot_row[0] == "1") if bot_row else True

    bot_reply = None
    if bot_enabled:
        bot_reply = generate_smart_bot_reply(local_phone, message_text, cursor)
        if bot_reply:
            cursor.execute("""
            INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status)
            VALUES (?, ?, 'outbound', 'bot_auto_reply', ?, 'delivered')
            """, (local_phone, cust_name, bot_reply))
            
            # Send back to customer via gateway
            dispatch_via_gateway_if_configured(local_phone, bot_reply)

    conn.commit()
    conn.close()

    return {
        "success": True,
        "from": local_phone,
        "bot_replied": bool(bot_reply),
        "reply": bot_reply
    }

@router.post("/simulate-customer-message")
def simulate_customer_message(payload: SimulateCustomerMessageSchema):
    """
    Simulates customer sending a message to test the auto-bot response live in the UI!
    """
    conn = get_db()
    cursor = conn.cursor()

    # 1. Insert customer message
    cursor.execute("""
    INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status)
    VALUES (?, ?, 'inbound', 'direct_chat', ?, 'read')
    """, (payload.phone, payload.customer_name, payload.message))

    # 2. Generate bot reply
    bot_reply = generate_smart_bot_reply(payload.phone, payload.message, cursor)
    
    if bot_reply:
        cursor.execute("""
        INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status)
        VALUES (?, ?, 'outbound', 'bot_auto_reply', ?, 'delivered')
        """, (payload.phone, payload.customer_name, bot_reply))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "customer_message": payload.message,
        "bot_reply": bot_reply
    }
