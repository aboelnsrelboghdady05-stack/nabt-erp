import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nabt_erp.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn

def init_db():
    conn = get_db()
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA cache_size = -64000")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA mmap_size = 268435456")
    cursor = conn.cursor()

    # 1. Customers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        email TEXT,
        address TEXT,
        notes TEXT,
        special_occasions TEXT, -- JSON format: [{"type": "ذكرى زواج", "date": "2026-11-15", "notes": "يحب الجوري الأحمر"}]
        total_spent REAL DEFAULT 0.0,
        orders_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Drivers Table (المناديب)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS drivers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        vehicle TEXT DEFAULT 'سيارة مكيفة لنقل الورد',
        status TEXT DEFAULT 'available', -- available, on_delivery, off_duty
        commission_per_order REAL DEFAULT 25.0,
        total_delivered INTEGER DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. Products Table (باقات ومنتجات الورد)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL, -- باقات يد، فازات، هدايا مع ورد، إضافات، كروت
        price REAL NOT NULL,
        cost REAL DEFAULT 0.0,
        stock INTEGER DEFAULT 999,
        image_url TEXT,
        description TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 4. Orders Table (الطلبات)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        customer_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        recipient_name TEXT,
        recipient_phone TEXT,
        recipient_address TEXT,
        location_url TEXT,
        card_message TEXT, -- نص كرت الإهداء
        delivery_date TEXT NOT NULL, -- YYYY-MM-DD
        delivery_time_slot TEXT, -- صباحي (9ص-1م)، مسائي (4ع-8م)، فوري
        driver_id INTEGER,
        status TEXT DEFAULT 'new', -- new (جديد), preparing (قيد التنسيق والتجهيز), ready (جاهز للتسليم), out_for_delivery (مع المندوب), delivered (تم التوصيل), cancelled (ملغي)
        subtotal REAL NOT NULL DEFAULT 0.0,
        delivery_fee REAL DEFAULT 0.0,
        discount REAL DEFAULT 0.0,
        tax REAL DEFAULT 0.0,
        total_amount REAL NOT NULL DEFAULT 0.0,
        payment_status TEXT DEFAULT 'unpaid', -- paid (مسدد), unpaid (غير مسدد), partial (مسدد جزئياً)
        payment_method TEXT DEFAULT 'cash', -- cash, pos (شبكة), bank_transfer, stc_pay, online
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
        FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL
    )
    """)

    # 5. Order Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        unit_price REAL NOT NULL,
        total_price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
    )
    """)

    # 6. Invoices Table (الفواتير الإلكترونية والحسابات)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        order_id INTEGER UNIQUE,
        customer_id INTEGER,
        customer_name TEXT,
        subtotal REAL NOT NULL,
        tax_amount REAL NOT NULL DEFAULT 0.0,
        total_amount REAL NOT NULL,
        paid_amount REAL DEFAULT 0.0,
        remaining_amount REAL NOT NULL,
        status TEXT DEFAULT 'unpaid', -- paid, unpaid, partial
        payment_method TEXT DEFAULT 'cash',
        issue_date TEXT NOT NULL,
        due_date TEXT,
        zatca_qr TEXT, -- Base64 or QR payload
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
    )
    """)

    # 7. Payments Table (سندات القبض والدفعات)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_number TEXT UNIQUE NOT NULL,
        invoice_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        payment_method TEXT NOT NULL, -- cash, pos, transfer, stc_pay, online
        reference_number TEXT,
        notes TEXT,
        payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
    )
    """)

    # 8. Expenses Table (المصروفات والمشتريات)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL, -- شراء ورد خام، تغليف وشرائط، إيجار، رواتب، كهرباء، صيانة، تسويق، أخرى
        amount REAL NOT NULL,
        payment_method TEXT DEFAULT 'cash',
        expense_date TEXT NOT NULL,
        vendor_name TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 9. WhatsApp Messages & Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS whatsapp_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_phone TEXT NOT NULL,
        recipient_name TEXT,
        direction TEXT DEFAULT 'outbound', -- outbound, inbound
        message_type TEXT DEFAULT 'order_update', -- order_update, driver_alert, direct_chat, custom
        content TEXT NOT NULL,
        status TEXT DEFAULT 'sent', -- sent, delivered, read, failed
        related_order_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (related_order_id) REFERENCES orders(id) ON DELETE SET NULL
    )
    """)

    # 10. WhatsApp Session & Settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # 11. Employees / Staff Table (الموظفين والمستخدمين)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL, -- florist (منسق زهور), driver (مندوب), cashier (كاشير/محاسب), manager (مدير)
        status TEXT DEFAULT 'on_duty', -- on_duty (في المحل على رأس العمل), on_leave (في إجازة), off_duty (خارج الدوام)
        specialty TEXT, -- تخصص المنسق: باقات يد، فازات، هدايا وبوكسات
        active_orders_count INTEGER DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 12. Employee Leaves Table (الإجازات وتحديد المتواجدين في المحل)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_leaves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        leave_type TEXT NOT NULL, -- إجازة سنوية، إجازة مرضية، راحة أسبوعية، إجازة طارئة
        start_date TEXT NOT NULL, -- YYYY-MM-DD
        end_date TEXT NOT NULL,   -- YYYY-MM-DD
        reason TEXT,
        status TEXT DEFAULT 'active', -- active (سارية حالياً), scheduled (مجدولة), completed (منتهية), cancelled
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
    )
    """)

    # Migration: Add florist_id to orders if not exists
    cursor.execute("PRAGMA table_info(orders)")
    columns = [row[1] for row in cursor.fetchall()]
    if "florist_id" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN florist_id INTEGER REFERENCES employees(id)")
    if "reference_image" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN reference_image TEXT")
    if "flower_colors" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN flower_colors TEXT")
    if "received_at" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN received_at TIMESTAMP")
    if "preparing_started_at" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN preparing_started_at TIMESTAMP")
    if "prepared_at" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN prepared_at TIMESTAMP")
    if "delivered_at" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN delivered_at TIMESTAMP")
    if "acceptance_status" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN acceptance_status TEXT DEFAULT 'pending'")
    if "accepted_at" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN accepted_at TIMESTAMP")
    if "rejected_at" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN rejected_at TIMESTAMP")
    if "rejection_reason" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN rejection_reason TEXT")
    if "completed_image" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN completed_image TEXT")
    if "completed_at" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN completed_at TIMESTAMP")
    if "approval_status" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN approval_status TEXT DEFAULT 'pending'")
    if "approved_by" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN approved_by TEXT")
    if "approved_at" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN approved_at TIMESTAMP")
    if "previous_florist_id" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN previous_florist_id INTEGER")

    # Migration: Add username, password, and weekly_off_day to employees
    cursor.execute("PRAGMA table_info(employees)")
    emp_columns = [row[1] for row in cursor.fetchall()]
    if "username" not in emp_columns:
        cursor.execute("ALTER TABLE employees ADD COLUMN username TEXT")
    if "password" not in emp_columns:
        cursor.execute("ALTER TABLE employees ADD COLUMN password TEXT DEFAULT '123456'")
    if "weekly_off_day" not in emp_columns:
        cursor.execute("ALTER TABLE employees ADD COLUMN weekly_off_day TEXT DEFAULT 'الثلاثاء'")

    # Ensure the 5 designated team users exist with their exact credentials and weekly off days
    users_to_ensure = [
        ("ياسر (المدير العام)", "0500000001", "general_manager", "yasser", "123456", "إدارة عامة وإشراف", "الجمعة"),
        ("فيصل (مدير تشغيلي)", "0501110001", "operations_manager", "faisal", "123456", "إدارة تشغيلية وتنسيق", "السبت"),
        ("نادر (مدير فرع)", "0502220002", "branch_manager", "nader", "123456", "إدارة الفرع والطلبات", "الأحد"),
        ("عمر (منسق ورد)", "0533688697", "florist", "omar", "123456", "تنسيق باقات وتغليف", "الثلاثاء"),
        ("ريكو (منسق ورد)", "0544917489", "florist", "rico", "123456", "تنسيق فازات وهدايا", "الاثنين")
    ]
    for uname_full, uphone, urole, ulogin, upwd, uspec, uoffday in users_to_ensure:
        cursor.execute("SELECT id, password, weekly_off_day, phone FROM employees WHERE username = ? OR phone = ? OR LOWER(name) LIKE ?", 
                       (ulogin, uphone, f"%{ulogin}%"))
        existing_row = cursor.fetchone()
        if existing_row:
            emp_id = existing_row[0]
            existing_pwd = existing_row[1] or upwd
            existing_off = existing_row[2] or uoffday
            # If user is Omar or Rico, prioritize their new numbers
            existing_phone = uphone if ulogin in ["omar", "rico"] else (existing_row[3] or uphone)
            cursor.execute("""
            UPDATE employees 
            SET name = ?, phone = ?, role = ?, username = ?, specialty = ?, status = 'on_duty',
                password = ?, weekly_off_day = ?
            WHERE id = ?
            """, (uname_full, existing_phone, urole, ulogin, uspec, existing_pwd, existing_off, emp_id))
        else:
            cursor.execute("""
            INSERT INTO employees (name, phone, role, username, password, specialty, status, weekly_off_day)
            VALUES (?, ?, ?, ?, ?, ?, 'on_duty', ?)
            """, (uname_full, uphone, urole, ulogin, upwd, uspec, uoffday))

    # Ensure Store WhatsApp Sender Phone is Faisal's number (0501110001 / +966501110001)
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('whatsapp_phone', '+966501110001')")
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('whatsapp_status', 'connected')")
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('auto_confirm_msg', ?)", 
        ("شكرًا لأنك اخترت نبت | Nabt\nاستلمنا طلبك رقم #{order_number} بنجاح!\nقيمة الطلب: {total_amount} ر.س\nحالة السداد: ({payment_status})\nتاريخ التوصيل: {delivery_date}\nموعد التوصيل: {delivery_time_slot}\nنسعى دائمًا بأن نكون جزء من لحظاتك الجميلة 💐",))
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('auto_driver_msg', ?)", 
        ("طلبكم رقم #{order_number} أصبح الآن مع المندوب",))
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('auto_delivered_msg', ?)", 
        ("سلمنا طلبك رقم #{order_number} بنجاح 💐🎉\nشكراً لأنك اخترت نبت | Nabt",))
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('florist_dispatch_template', ?)", 
        ("🌸 مهمة تنسيق ورد جديد\nمرحباً يا فنان {florist_name}\nتم إسناد طلب جديد إليك من الإدارة للتجهيز:\n• رقم الطلب: #{order_number}\n• تفاصيل الطلب: {items_summary}\n• 🎨 ألوان الورد والتغليف: {flower_colors}\n• كرت الإهداء: \"{card_message}\"\n• موعد التسليم: {delivery_date} \n• وقت التسليم({delivery_time_slot})\n• ملاحظات التجهيز: {notes}\n• 📸 صورة (مساندة) مرجعية: مرفقة في السيستم افتح تفاصيل الطلب لمطابقتها!\n\nشد حيلك وأبدأ التجهيز وأكد لنا إذا جهز! 💐",))

    # 13. Purchase Requests Table (طلبات المشتريات والتعميد)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_number TEXT UNIQUE NOT NULL,
        item_name TEXT NOT NULL,
        category TEXT NOT NULL,
        quantity TEXT NOT NULL,
        estimated_amount REAL NOT NULL DEFAULT 0.0,
        urgency TEXT DEFAULT 'normal',
        reason TEXT,
        requested_by_id INTEGER,
        requested_by_name TEXT NOT NULL,
        requested_by_role TEXT NOT NULL,
        status TEXT DEFAULT 'pending_review',
        endorsed_by_id INTEGER,
        endorsed_by_name TEXT,
        endorsed_by_role TEXT,
        endorsed_at TIMESTAMP,
        endorsement_notes TEXT,
        approved_by_id INTEGER,
        approved_by_name TEXT,
        approved_at TIMESTAMP,
        gm_notes TEXT,
        rejected_by_name TEXT,
        rejected_at TIMESTAMP,
        rejection_reason TEXT,
        expense_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 14. Creative Projects Tasks (مهام مشاريع نبت الإبداعية)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS creative_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_number TEXT UNIQUE NOT NULL,
        details TEXT NOT NULL,
        due_date TEXT NOT NULL,
        due_time TEXT,
        assigned_to_id INTEGER,
        assigned_to_name TEXT NOT NULL,
        assigned_to_phone TEXT,
        created_by_id INTEGER,
        created_by_name TEXT NOT NULL,
        status TEXT DEFAULT 'pending', -- pending, in_progress, completed, cancelled
        completed_at TIMESTAMP,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assigned_to_id) REFERENCES employees(id) ON DELETE SET NULL,
        FOREIGN KEY (created_by_id) REFERENCES employees(id) ON DELETE SET NULL
    )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database schema created successfully.")
