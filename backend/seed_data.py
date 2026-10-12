import json
from datetime import datetime, date, timedelta
from database import get_db, init_db

def seed_database():
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] > 0:
        print("Database already contains data, skipping seed.")
        conn.close()
        return

    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    # 1. Seed Products (منتجات وباقات محل الورد)
    products = [
        ("باقة الجوري الملكي الأحمر (50 وردة)", "باقات يد", 280.0, 110.0, 45, "https://images.unsplash.com/photo-1561181286-d3fee7d55364?w=500", "تنسيق فاخر من الورد الجوري الأحمر الهولندي الطبيعي مع تغليف أسود ملكي وشريط حرير."),
        ("باقة التوليب الأبيض والوردي", "باقات يد", 220.0, 85.0, 30, "https://images.unsplash.com/photo-1526047932273-341f2a7631f9?w=500", "أزهار التوليب الهولندية المنعشة بألوان ناعمة تناسب التهاني والتخرج."),
        ("فازة زهور الأوركيد والبيبي جوري الفاخرة", "فازات", 360.0, 140.0, 20, "https://images.unsplash.com/photo-1582794543139-8ac9cb0f7b11?w=500", "فازة سيراميك أنيقة بتنسيق متوازن من زهور الأوركيد والبيبي جوري وأغصان اليوكالبتوس العطرية."),
        ("بوكس ورد مع شوكولاتة بستاني", "هدايا مع ورد", 320.0, 130.0, 25, "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=500", "صندوق هدايا دائري أنيق يحوي تنسيق ورود زاهية مع علبة شوكولاتة بلجيكية فاخرة."),
        ("باقة الربيع المنعشة (مكس زهور ملونة)", "باقات يد", 190.0, 70.0, 40, "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=500", "مزيج منعش من دوار الشمس، الهيدرانجيا، والبيبي جوري الأصفر مع تغليف بيج."),
        ("فازة كلاسيك زجاجية مع ليليوم وجوري", "فازات", 240.0, 95.0, 15, "https://images.unsplash.com/photo-1525310072745-f49212b5ac6d?w=500", "فازة زجاجية شفافة فخمة مع زهور الليليوم العطرة والورود البيضاء."),
        ("شوكولاتة باتشي فاخرة (ربع كيلو)", "إضافات", 85.0, 50.0, 50, "https://images.unsplash.com/photo-1549007994-cb92caebd54b?w=500", "إضافة شوكولاتة مغلفة فاخرة مع الباقة."),
        ("بالون هيليوم (مبروك التخرج / ألف مبروك)", "إضافات", 35.0, 12.0, 80, "https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=500", "بالون هيليوم مميز للمناسبات السعيدة."),
        ("كرت إهداء فاخر مختوم بالشمع الأحمر", "كروت", 15.0, 3.0, 150, "https://images.unsplash.com/photo-1586075010923-2dd4570fb338?w=500", "كرت ورقي مقوى يدوي الصنع مع ختم شمعي فاخر وطباعة إهداء مخصصة.")
    ]

    for p in products:
        cursor.execute("""
        INSERT INTO products (name, category, price, cost, stock, image_url, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, p)

    # 2. Seed Drivers (المناديب)
    drivers = [
        ("أحمد عبد الله المنصور", "0501234567", "تويوتا يارس مكيفة مجهزة لحفظ برودة الورد", "available", 25.0, 0, "سريع وملتزم بالمواعيد في شمال الرياض"),
        ("خالد فهد العتيبي", "0559876543", "هيونداي إلنترا مكيفة", "available", 25.0, 0, "متخصص في توصيل الحفلات وشرق الرياض"),
        ("ياسر محمد الشمري", "0543219876", "كيا سيراتو مكيفة", "available", 25.0, 0, "تغطية غرب وجنوب الرياض")
    ]
    for d in drivers:
        cursor.execute("""
        INSERT INTO drivers (name, phone, vehicle, status, commission_per_order, total_delivered, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, d)

    conn.commit()
    conn.close()
    return

    # 3. Seed Customers (العملاء)
    customers = [
        (
            "سارة عبد العزيز آل سعود", 
            "0505112233", 
            "sara@example.com", 
            "الرياض - حي النخيل - فيلا 14", 
            "عميلة VIP - تفضل التوليب الأبيض وتغليف ناعم", 
            json.dumps([{"type": "ذكرى زواج", "date": "11-20", "notes": "باقة توليب وجوري أبيض"}, {"type": "عيد ميلاد", "date": "04-15", "notes": "هدية خاصة"}]),
            1240.0,
            4
        ),
        (
            "محمد إبراهيم القحطاني", 
            "0544223344", 
            "m.alqahtani@example.com", 
            "الرياض - حي حطين - شارع الأمير تركي", 
            "يطلب دائماً شوكولاتة مع الورد", 
            json.dumps([{"type": "يوم الأم", "date": "03-21", "notes": "فازة كبيرة فاخرة"}]),
            880.0,
            3
        ),
        (
            "نورة ناصر الدوسري", 
            "0566334455", 
            "noura.d@example.com", 
            "الرياض - حي الملقا", 
            "تفضل باقات الورد الجوري الملكي والبالونات", 
            json.dumps([{"type": "تخرج أختها", "date": "10-25", "notes": "باقة ورد كبيرة باللون البنفسجي"}]),
            560.0,
            2
        ),
        (
            "فيصل سلطان الحربي", 
            "0533445566", 
            "faisal.h@example.com", 
            "الرياض - حي الياسمين", 
            "زبون جديد - دفع عند الاستلام", 
            json.dumps([]),
            310.0,
            1
        )
    ]
    for c in customers:
        cursor.execute("""
        INSERT INTO customers (name, phone, email, address, notes, special_occasions, total_spent, orders_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, c)

    # 4. Seed Orders (الطلبات)
    orders_data = [
        {
            "order_number": "NBT-2601",
            "customer_id": 1,
            "customer_name": "سارة عبد العزيز آل سعود",
            "customer_phone": "0505112233",
            "recipient_name": "د. ندى المنصور",
            "recipient_phone": "0509988776",
            "recipient_address": "مستشفى الملك فيصل التخصصي - مبنى العيادات",
            "location_url": "https://maps.google.com/?q=24.6711,46.6766",
            "card_message": "ألف حمد لله على السلامة يا دكتورة ندى، طهور إن شاء الله ومنورة دايماً 🌸 محبيك عائلة آل سعود",
            "delivery_date": today_str,
            "delivery_time_slot": "مسائي (4م - 8م)",
            "driver_id": 2, # خالد العتيبي
            "status": "out_for_delivery",
            "subtotal": 360.0,
            "delivery_fee": 35.0,
            "discount": 0.0,
            "tax": 59.25,
            "total_amount": 454.25,
            "payment_status": "paid",
            "payment_method": "pos",
            "notes": "يرجى تسليم الباقة للاستقبال باسم الدكتورة ندى",
            "items": [
                {"product_id": 3, "product_name": "فازة زهور الأوركيد والبيبي جوري الفاخرة", "qty": 1, "price": 360.0},
                {"product_id": 9, "product_name": "كرت إهداء فاخر مختوم بالشمع الأحمر", "qty": 1, "price": 15.0}
            ]
        },
        {
            "order_number": "NBT-2602",
            "customer_id": 2,
            "customer_name": "محمد إبراهيم القحطاني",
            "customer_phone": "0544223344",
            "recipient_name": "هند عبد الله",
            "recipient_phone": "0551122334",
            "recipient_address": "الرياض - حي حطين - مجمع لوميير السكني",
            "location_url": "https://maps.google.com/?q=24.7743,46.6022",
            "card_message": "كل عام وأنتِ أجمل أعيادي ورفيقة دربي ❤️ ذكرى زواج سعيدة",
            "delivery_date": today_str,
            "delivery_time_slot": "مسائي (7م - 10م)",
            "driver_id": 1, # أحمد المنصور
            "status": "preparing",
            "subtotal": 365.0,
            "delivery_fee": 30.0,
            "discount": 15.0,
            "tax": 57.0,
            "total_amount": 437.0,
            "payment_status": "paid",
            "payment_method": "online",
            "notes": "تنسيق الورد باهتمام فائق مع شريط مخملي أحمر",
            "items": [
                {"product_id": 1, "product_name": "باقة الجوري الملكي الأحمر (50 وردة)", "qty": 1, "price": 280.0},
                {"product_id": 7, "product_name": "شوكولاتة باتشي فاخرة (ربع كيلو)", "qty": 1, "price": 85.0}
            ]
        },
        {
            "order_number": "NBT-2603",
            "customer_id": 3,
            "customer_name": "نورة ناصر الدوسري",
            "customer_phone": "0566334455",
            "recipient_name": "ريم الدوسري",
            "recipient_phone": "0566778899",
            "recipient_address": "جامعة الملك سعود - كلية العلوم الإدارية",
            "location_url": "https://maps.google.com/?q=24.7162,46.6190",
            "card_message": "مبارك التخرج بمرتبة الشرف ومنها لأعلى المراتب يا ريم 🎓💐",
            "delivery_date": tomorrow_str,
            "delivery_time_slot": "صباحي (10ص - 1م)",
            "driver_id": None,
            "status": "new",
            "subtotal": 255.0,
            "delivery_fee": 30.0,
            "discount": 0.0,
            "tax": 42.75,
            "total_amount": 327.75,
            "payment_status": "unpaid", # غير مسدد
            "payment_method": "transfer",
            "notes": "العميلة سترسل إشعار التحويل البنكي قبل التجهيز",
            "items": [
                {"product_id": 2, "product_name": "باقة التوليب الأبيض والوردي", "qty": 1, "price": 220.0},
                {"product_id": 8, "product_name": "بالون هيليوم (مبروك التخرج / ألف مبروك)", "qty": 1, "price": 35.0}
            ]
        },
        {
            "order_number": "NBT-2604",
            "customer_id": 4,
            "customer_name": "فيصل سلطان الحربي",
            "customer_phone": "0533445566",
            "recipient_name": "فيصل الحربي",
            "recipient_phone": "0533445566",
            "recipient_address": "الرياض - حي الياسمين - فيلا 42",
            "location_url": "https://maps.google.com/?q=24.8100,46.6500",
            "card_message": "حمداً لله على سلامة الوالدة الكريمة أجر وعافية يارب 🌹",
            "delivery_date": yesterday_str,
            "delivery_time_slot": "مسائي (5م - 8م)",
            "driver_id": 1,
            "status": "delivered",
            "subtotal": 190.0,
            "delivery_fee": 25.0,
            "discount": 0.0,
            "tax": 32.25,
            "total_amount": 247.25,
            "payment_status": "paid",
            "payment_method": "cash",
            "notes": "تم الاستلام نقدياً مع المندوب",
            "items": [
                {"product_id": 5, "product_name": "باقة الربيع المنعشة (مكس زهور ملونة)", "qty": 1, "price": 190.0}
            ]
        }
    ]

    for o in orders_data:
        cursor.execute("""
        INSERT INTO orders (
            order_number, customer_id, customer_name, customer_phone,
            recipient_name, recipient_phone, recipient_address, location_url,
            card_message, delivery_date, delivery_time_slot, driver_id,
            status, subtotal, delivery_fee, discount, tax, total_amount,
            payment_status, payment_method, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            o["order_number"], o["customer_id"], o["customer_name"], o["customer_phone"],
            o["recipient_name"], o["recipient_phone"], o["recipient_address"], o["location_url"],
            o["card_message"], o["delivery_date"], o["delivery_time_slot"], o["driver_id"],
            o["status"], o["subtotal"], o["delivery_fee"], o["discount"], o["tax"], o["total_amount"],
            o["payment_status"], o["payment_method"], o["notes"]
        ))
        order_id = cursor.lastrowid

        # Insert items
        for item in o["items"]:
            cursor.execute("""
            INSERT INTO order_items (order_id, product_id, product_name, quantity, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (order_id, item["product_id"], item["product_name"], item["qty"], item["price"], item["qty"] * item["price"]))

        # Create corresponding Invoice
        inv_number = f"INV-{o['order_number'].replace('NBT-', '')}"
        paid_amt = o["total_amount"] if o["payment_status"] == "paid" else 0.0
        rem_amt = 0.0 if o["payment_status"] == "paid" else o["total_amount"]
        
        cursor.execute("""
        INSERT INTO invoices (
            invoice_number, order_id, customer_id, customer_name, subtotal,
            tax_amount, total_amount, paid_amount, remaining_amount,
            status, payment_method, issue_date, due_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inv_number, order_id, o["customer_id"], o["customer_name"],
            o["subtotal"] + o["delivery_fee"] - o["discount"],
            o["tax"], o["total_amount"], paid_amt, rem_amt,
            o["payment_status"], o["payment_method"], o["delivery_date"], o["delivery_date"]
        ))
        inv_id = cursor.lastrowid

        # If paid, record payment entry
        if o["payment_status"] == "paid":
            cursor.execute("""
            INSERT INTO payments (payment_number, invoice_id, amount, payment_method, reference_number, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (f"PAY-{inv_id:04d}", inv_id, o["total_amount"], o["payment_method"], f"TXN-POS-{inv_id}", "سداد كامل الفاتورة"))

    # 5. Seed Expenses (المصروفات والمشتريات)
    expenses = [
        ("شراء ورود طبيعية مستوردة من هولندا (توليب، جوري، بيبي جوري)", "شراء ورد خام", 1850.0, "transfer", today_str, "شركة زهور الشرق الأوسط للمستوردات", "شحنة ورود مكيفة طازجة للمحل"),
        ("شراء رولات تغليف كورية فاخرة وشرائط ساتان وأشرطة حرير", "تغليف وشرائط", 480.0, "pos", yesterday_str, "مؤسسة خيوط الإبداع لمواد التغليف", "كمية تكفي أسبوعين لمختلف المناسبات"),
        ("فاتورة كهرباء المعرض وتشغيل برادات حفظ الورد المركزية", "كهرباء", 650.0, "online", (today - timedelta(days=5)).strftime("%Y-%m-%d"), "الشركة السعودية للكهرباء", "فاتورة الشهر الحالي"),
        ("بنزين وصيانة دورية لسيارات التوصيل والتبريد", "صيانة", 320.0, "pos", (today - timedelta(days=2)).strftime("%Y-%m-%d"), "محطة ونفط الرياض", "تغيير زيت وفحص تبريد ثلاجات التوصيل")
    ]
    for ex in expenses:
        cursor.execute("""
        INSERT INTO expenses (title, category, amount, payment_method, expense_date, vendor_name, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ex)

    # 6. Seed WhatsApp Settings & Sample Logs
    settings = {
        "whatsapp_status": "connected",
        "whatsapp_phone": "+966501110001",
        "store_name": "نبت للزهور والمناسبات 🌸",
        "auto_confirm_msg": "شكرًا لأنك اخترت نبت | Nabt\nاستلمنا طلبك رقم #{order_number} بنجاح!\nقيمة الطلب: {total_amount} ر.س\nحالة السداد: ({payment_status})\nتاريخ التوصيل: {delivery_date}\nموعد التوصيل: {delivery_time_slot}\nنسعى دائمًا بأن نكون جزء من لحظاتك الجميلة 💐",
        "auto_preparing_msg": "طلبكم الجميل رقم #{order_number} الآن بأيدي منسقينا المحترفين في نبت 🌿\nيتم تجهيزه بأجمل الورود الطازجة بكل عناية وحب ❤️",
        "auto_driver_msg": "طلبكم رقم #{order_number} أصبح الآن مع المندوب",
        "auto_delivered_msg": "سلمنا طلبك رقم #{order_number} بنجاح 💐🎉\nشكراً لأنك اخترت نبت | Nabt",
        "driver_dispatch_template": "مرحباً يا بطل {driver_name} 🚗\nلديك طلب توصيل جديد من نبت 🌸\nرقم الطلب: #{order_number}\nالمستلم: {recipient_name}\nجوال المستلم: {recipient_phone}\nالعنوان: {recipient_address}\nالموقع: {location_url}\nموعد التسليم: {delivery_date} ({time_slot})",
        "florist_dispatch_template": "🌸 مهمة تنسيق ورد جديد\nمرحباً يا فنان {florist_name}\nتم إسناد طلب جديد إليك من الإدارة للتجهيز:\n• رقم الطلب: #{order_number}\n• تفاصيل الطلب: {items_summary}\n• 🎨 ألوان الورد والتغليف: {flower_colors}\n• كرت الإهداء: \"{card_message}\"\n• موعد التسليم: {delivery_date} \n• وقت التسليم({delivery_time_slot})\n• ملاحظات التجهيز: {notes}\n• 📸 صورة (مساندة) مرجعية: مرفقة في السيستم افتح تفاصيل الطلب لمطابقتها!\n\nشد حيلك وأبدأ التجهيز وأكد لنا إذا جهز! 💐"
    }
    for k, v in settings.items():
        cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (k, v))

    # Seed WhatsApp recent messages
    wa_msgs = [
        ("0505112233", "سارة عبد العزيز آل سعود", "outbound", "order_update", "أهلاً بك سارة في نبت للزهور 🌸 تم استلام وتأكيد طلبكم رقم #NBT-2601 بنجاح!", "delivered", 1),
        ("0505112233", "سارة عبد العزيز آل سعود", "outbound", "order_update", "طلبكم رقم #NBT-2601 أصبح الآن مع المندوب (خالد العتيبي) وهو في الطريق للمستشفى 🚗🌸", "read", 1),
        ("0559876543", "خالد فهد العتيبي (المندوب)", "outbound", "driver_alert", "مرحباً يا بطل خالد 🚗 لديك طلب توصيل جديد رقم #NBT-2601 المستلم: د. ندى المنصور", "read", 1),
        ("0544223344", "محمد إبراهيم القحطاني", "outbound", "order_update", "طلبكم الجميل رقم #NBT-2602 الآن قيد التجهيز والتنسيق بأجود الورود الحمراء 🌿", "delivered", 2),
        ("0544223344", "محمد إبراهيم القحطاني", "inbound", "direct_chat", "شكراً لكم، يرجى كتابة كرت الإهداء بخط رقعة مميز لو تكرمتم", "read", 2)
    ]
    for wm in wa_msgs:
        cursor.execute("""
        INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, wm)

    # 7. Seed Employees & Leaves (الموظفين والمنسقين والإجازات)
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        emp_list = [
            ("فهد ناصر السالم", "0551112233", "florist", "باقات يد وتغليف مخملي", "on_duty", "منسق أول - خبير الورود الهولندية"),
            ("مروان خالد الشامي", "0552223344", "florist", "فازات أوركيد وهدايا وبوكسات", "on_duty", "منسق فازات وتنسيقات المناسبات"),
            ("ريم عبد الله القحطاني", "0553334455", "florist", "باقات عرائس وتنسيق طبيعي", "on_leave", "منسقة زهور - في إجازة سنوية"),
            ("عمر فهد الهذلول", "0554445566", "cashier", "محاسبة ونقاط بيع", "on_duty", "كاشير ومحاسب الفرع")
        ]
        for e in emp_list:
            cursor.execute("""
            INSERT INTO employees (name, phone, role, specialty, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """, e)
        
        # Add leave record for Reem (ID 3)
        cursor.execute("""
        INSERT INTO employee_leaves (employee_id, leave_type, start_date, end_date, reason, status)
        VALUES (3, 'إجازة سنوية', date('now', '-2 days'), date('now', '+7 days'), 'إجازة سنوية مجدولة - مستبعدة من استلام الطلبات', 'active')
        """)

    conn.commit()
    conn.close()
    print("Seed data loaded successfully!")

if __name__ == "__main__":
    seed_database()
