/**
 * Nabt Flowers ERP - Multilingual Engine (Arabic, English, Bengali / Bangladeshi)
 */

const i18nTranslations = {
    ar: {
        dir: 'rtl',
        font: "'Tajawal', sans-serif",
        store_sub: 'إدارة محلات الورد والمناسبات',
        system_cloud: 'نظام نبت السحابي',
        system_status: 'جاهز للعمل',
        version_label: 'نسخة المتجر 1.0.0 • الرياض',
        
        // Navigation Tabs
        nav_dashboard: 'لوحة التحكم',
        nav_orders: 'الطلبات والتنسيق',
        nav_whatsapp: 'مركز الواتس اب',
        nav_invoices: 'الحسابات والفواتير',
        nav_drivers: 'المناديب والتوصيل',
        nav_customers: 'العملاء والمناسبات',
        nav_expenses: 'المصروفات والأرباح',
        nav_purchases: 'المشتريات والتعميد',
        nav_products: 'كتالوج الورد والهدايا',
        nav_employees: 'الموظفين والإجازات',
        nav_creative_tasks: 'مهام مشاريع نبت الإبداعية',
        nav_sync: 'ربط الحسابات (Webhook)',
        
        // Badges & Statuses
        badge_connected: 'متصل',
        badge_disconnected: 'غير متصل',
        badge_unpaid: 'معلقة',
        badge_on_duty: 'في المحل',
        badge_on_leave: 'في إجازة',
        
        // Header
        admin_new_order: 'طلب جديد كـ Admin وتوجيهه للمنسق 🌸',
        btn_new_order_short: 'طلب جديد 🌸',
        simulate_inv: 'محاكاة فاتورة الحسابات',
        whatsapp_btn: 'الواتس اب',
        admin_name: 'المدير (Admin)',
        admin_role: 'صلاحيات كاملة',
        switch_user_title: 'تبديل حساب المستخدم الحالي 👤',
        switch_user_desc: 'اختر يوزر المنسق لمعاينة واجهة المنسق وطلباته فقط',
        florist_user: 'يوزر منسق ورد 🌸',
        
        // Dashboard Tab
        dash_title: 'لوحة التحكم الشاملة',
        accounting_banner_title: 'الربط المحاسبي السحابي نشط وتلقائي',
        accounting_banner_desc: 'أي فاتورة تصدر في نظام الحسابات (قيود / دفترة / أودو / زوهو) تسمّع هنا فوراً، وتُحدّث المبيعات، وتطلق إشعارات الواتساب للعميل والمندوب تلقائياً.',
        btn_simulate_now: 'تجربة استقبال فاتورة الآن',
        btn_webhook_link: 'رابط الـ Webhook',
        kpi_today_sales: 'مبيعات اليوم',
        kpi_today_orders: 'طلبات اليوم',
        kpi_month_sales: 'إجمالي مبيعات الشهر',
        kpi_month_completed: 'طلب مكتمل',
        kpi_unpaid_invoices: 'الفواتير غير المسددة (آجلة)',
        kpi_unpaid_desc: 'مبالغ مستحقة من العملاء',
        kpi_net_profit: 'صافي الربح التقديري',
        kpi_after_expenses: 'بعد خصم المصروفات',
        
        // Orders Tracker
        order_flow_title: 'متابعة تدفق وحالات الطلبات في المحل',
        order_flow_sub: 'تحديث فوري وتلقائي مع إشعارات الواتس اب',
        status_new: 'طلب جديد 🟡',
        status_preparing: 'قيد التنسيق 🌿',
        status_ready: 'جاهز للتسليم 🌸',
        status_out: 'مع المندوب 🚗',
        status_delivered: 'تم التوصيل 💐',
        status_cancelled: 'ملغي ❌',
        
        // Urgent Deliveries & Occasions
        urgent_orders_title: 'طلبات التوصيل المستعجلة والمقررة اليوم',
        view_all_orders: 'عرض كل الطلبات ←',
        vip_occasions_title: 'مناسبات عملاء VIP القادمة',
        auto_reminder: 'تذكير آلي',
        occasions_sub: 'أرسل اقتراحات وتنسيقات ورد عبر الواتس اب قبل المناسبة!',
        top_bouquets_title: 'أكثر الورد طلباً هذا الأسبوع',
        
        // Orders Tab
        orders_title: 'إدارة الطلبات وتنسيق الورد',
        florist_banner_title: 'لوحة مهام المنسق 🌸',
        florist_only_badge: 'طلباتي فقط',
        florist_banner_desc: 'تظهر لك هنا فقط الطلبات المسندة إليك لتنسيقها وتجهيزها وبدء العمل عليها.',
        back_to_admin: 'العودة للوحة الإدارة (Admin) ←',
        filter_status_label: 'تصفية حسب الحالة:',
        filter_all: 'الكل',
        filter_new: 'جديد',
        filter_prep: 'قيد التنسيق',
        filter_ready: 'جاهز',
        filter_out: 'مع المندوب',
        filter_del: 'تم التوصيل',
        order_search_ph: 'بحث برقم الطلب أو اسم العميل أو الهاتف...',
        btn_add_order: 'طلب جديد',
        
        // Table Columns
        th_order_num: 'رقم الطلب',
        th_cust_phone: 'العميل / هاتف',
        th_rec_addr: 'المستلم وعنوان التوصيل',
        th_items_flowers: 'الأصناف والورد',
        th_delivery_time: 'موعد التسليم',
        th_florist: 'منسق الورد (في المحل) 🌸',
        th_driver: 'المندوب 🚗',
        th_total_payment: 'الإجمالي والسداد',
        th_status: 'حالة الطلب',
        th_quick_actions: 'إجراءات سريعة',
        
        // Flower Colors
        flower_colors_label: 'ألوان الورد 🌸',
        card_gift: '💌 كرت إهداء',
        ref_image: 'صورة ريفرنس 🖼️',
        paid: 'مسدد ✅',
        unpaid: 'غير مسدد ⚠️',
        
        // Bottom Nav
        bottom_nav_home: 'الرئيسية',
        bottom_nav_orders: 'الطلبات',
        bottom_nav_whatsapp: 'واتساب',
        bottom_nav_menu: 'القائمة',
        
        // Creative Tasks
        creative_tasks_title: 'مهام مشاريع نبت الإبداعية 🎨',
        creative_tasks_desc: 'مساحة العمل المشتركة لتوزيع ومتابعة المهام الإبداعية بين أعضاء الفريق.',
        btn_new_creative_task: 'إرسال مهمة إبداعية جديدة 🌸',
        crt_all_tasks: 'جميع المهام',
        crt_pending: 'بانتظار البدء ⏳',
        crt_in_progress: 'قيد التنفيذ 🎨',
        crt_completed: 'المنجزة بنجاح ✅',
        crt_start: 'بدء التنفيذ',
        crt_finish: 'إكمال المهمة ✅',
        crt_done: 'مكتملة بنجاح 🎉',
        
        // Common
        today_is: 'اليوم',
        sar: 'ر.س',
        save: 'حفظ',
        cancel: 'إلغاء',
        delete: 'حذف',
        edit: 'تعديل',
        refresh: 'تحديث',
        search: 'بحث',
        print: 'طباعة',
        send: 'إرسال',
        actions: 'إجراءات',
        close: 'إغلاق',
        notes: 'ملاحظات',
        details: 'التفاصيل',
        due_date: 'موعد التسليم',
        assigned_to: 'المُسند إليه',
        created_by: 'مقدم الطلب',
        
        // Languages
        lang_name: 'العربية',
        lang_switch: 'اللغة'
    },
    en: {
        dir: 'ltr',
        font: "'Tajawal', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        store_sub: 'Flower & Occasions Management',
        system_cloud: 'Nabt Cloud ERP',
        system_status: 'Active & Ready',
        version_label: 'Store Version 1.0.0 • Riyadh',
        
        // Navigation Tabs
        nav_dashboard: 'Dashboard',
        nav_orders: 'Orders & Floral',
        nav_whatsapp: 'WhatsApp Hub',
        nav_invoices: 'Invoices & Finance',
        nav_drivers: 'Drivers & Delivery',
        nav_customers: 'Customers (CRM)',
        nav_expenses: 'Expenses & Profits',
        nav_purchases: 'Purchases & Approvals',
        nav_products: 'Bouquets Catalog',
        nav_employees: 'Florists & Leaves',
        nav_creative_tasks: 'Creative Projects Tasks',
        nav_sync: 'Accounting Sync',
        
        // Badges & Statuses
        badge_connected: 'Connected',
        badge_disconnected: 'Offline',
        badge_unpaid: 'Pending',
        badge_on_duty: 'In Shop',
        badge_on_leave: 'On Leave',
        
        // Header
        admin_new_order: 'New Order as Admin & Dispatch 🌸',
        btn_new_order_short: 'New Order 🌸',
        simulate_inv: 'Simulate Accounting Invoice',
        whatsapp_btn: 'WhatsApp',
        admin_name: 'Manager (Admin)',
        admin_role: 'Full Permissions',
        switch_user_title: 'Switch Current User 👤',
        switch_user_desc: 'Select florist to preview florist tasks only',
        florist_user: 'Florist Account 🌸',
        
        // Dashboard Tab
        dash_title: 'Comprehensive Dashboard',
        accounting_banner_title: 'Cloud Accounting Sync Active & Real-Time',
        accounting_banner_desc: 'Invoices created in Qoyod / Daftra / Odoo / Zoho automatically sync here, updating sales and dispatching alerts to customer & driver.',
        btn_simulate_now: 'Test Receive Invoice Now',
        btn_webhook_link: 'Webhook URL',
        kpi_today_sales: "Today's Sales",
        kpi_today_orders: "Today's Orders",
        kpi_month_sales: 'Monthly Total Sales',
        kpi_month_completed: 'Completed Orders',
        kpi_unpaid_invoices: 'Unpaid Invoices (Receivables)',
        kpi_unpaid_desc: 'Outstanding customer balances',
        kpi_net_profit: 'Estimated Net Profit',
        kpi_after_expenses: 'After operating expenses',
        
        // Orders Tracker
        order_flow_title: 'Live Order Flow & Shop Status Tracker',
        order_flow_sub: 'Real-time updates with automated WhatsApp notifications',
        status_new: 'New Order 🟡',
        status_preparing: 'In Preparation 🌿',
        status_ready: 'Ready for Pickup 🌸',
        status_out: 'Out with Driver 🚗',
        status_delivered: 'Delivered 💐',
        status_cancelled: 'Cancelled ❌',
        
        // Urgent Deliveries & Occasions
        urgent_orders_title: 'Urgent Deliveries Scheduled for Today',
        view_all_orders: 'View All Orders →',
        vip_occasions_title: 'Upcoming VIP Customer Occasions',
        auto_reminder: 'Auto Reminder',
        occasions_sub: 'Send flower bouquet recommendations via WhatsApp before the occasion!',
        top_bouquets_title: 'Top Requested Bouquets This Week',
        
        // Orders Tab
        orders_title: 'Orders & Flower Arrangements',
        florist_banner_title: 'Florist Taskboard 🌸',
        florist_only_badge: 'My Orders Only',
        florist_banner_desc: 'You are viewing only the orders assigned to you to arrange, style and prepare.',
        back_to_admin: 'Return to Admin View →',
        filter_status_label: 'Filter by Status:',
        filter_all: 'All',
        filter_new: 'New',
        filter_prep: 'Preparing',
        filter_ready: 'Ready',
        filter_out: 'Out',
        filter_del: 'Delivered',
        order_search_ph: 'Search by order #, customer name or phone...',
        btn_add_order: 'New Order',
        
        // Table Columns
        th_order_num: 'Order #',
        th_cust_phone: 'Customer / Phone',
        th_rec_addr: 'Recipient & Delivery Address',
        th_items_flowers: 'Bouquets & Flowers',
        th_delivery_time: 'Delivery Time',
        th_florist: 'Florist (In Shop) 🌸',
        th_driver: 'Driver 🚗',
        th_total_payment: 'Total & Payment',
        th_status: 'Order Status',
        th_quick_actions: 'Quick Actions',
        
        // Flower Colors
        flower_colors_label: 'Flower Colors 🌸',
        card_gift: '💌 Greeting Card',
        ref_image: 'Reference Photo 🖼️',
        paid: 'Paid ✅',
        unpaid: 'Unpaid ⚠️',
        
        // Bottom Nav
        bottom_nav_home: 'Home',
        bottom_nav_orders: 'Orders',
        bottom_nav_whatsapp: 'WhatsApp',
        bottom_nav_menu: 'Menu',
        
        // Creative Tasks
        creative_tasks_title: 'Nabt Creative Projects Tasks 🎨',
        creative_tasks_desc: 'Workspace to assign and follow up on creative projects among team members.',
        btn_new_creative_task: 'Send New Creative Task 🌸',
        crt_all_tasks: 'All Tasks',
        crt_pending: 'Pending ⏳',
        crt_in_progress: 'In Progress 🎨',
        crt_completed: 'Completed ✅',
        crt_start: 'Start Working',
        crt_finish: 'Complete Task ✅',
        crt_done: 'Completed 🎉',
        
        // Common
        today_is: 'Today',
        sar: 'SAR',
        save: 'Save',
        cancel: 'Cancel',
        delete: 'Delete',
        edit: 'Edit',
        refresh: 'Refresh',
        search: 'Search',
        print: 'Print',
        send: 'Send',
        actions: 'Actions',
        close: 'Close',
        notes: 'Notes',
        details: 'Details',
        due_date: 'Due Date',
        assigned_to: 'Assigned To',
        created_by: 'Created By',
        
        // Languages
        lang_name: 'English',
        lang_switch: 'Language'
    },
    bn: {
        dir: 'ltr',
        font: "'Tajawal', 'Hind Siliguri', 'Noto Sans Bengali', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        store_sub: 'ফুলের দোকান ও অনুষ্ঠানের ব্যবস্থাপনা',
        system_cloud: 'নাবত ক্লাউড ERP সিস্টেম',
        system_status: 'সক্রিয় ও প্রস্তুত',
        version_label: 'স্টোর সংস্করণ ১.০.০ • রিয়াদ',
        
        // Navigation Tabs
        nav_dashboard: 'ড্যাশবোর্ড',
        nav_orders: 'অর্ডার ও ফুল বিন্যাস',
        nav_whatsapp: 'হোয়াটসঅ্যাপ হাব',
        nav_invoices: 'ইনভয়েস ও হিসাব',
        nav_drivers: 'ডেলিভারি ও ড্রাইভার',
        nav_customers: 'গ্রাহকবৃন্দ (CRM)',
        nav_expenses: 'খরচ ও মুনাফা',
        nav_purchases: 'ক্রয় ও অনুমোদন',
        nav_products: 'ফুলের ক্যাটালগ',
        nav_employees: 'ফ্লোরিস্ট ও ছুটি',
        nav_creative_tasks: 'নাবত ক্রিয়েটিভ প্রজেক্টস',
        nav_sync: 'হিসাব লিঙ্ক (Webhook)',
        
        // Badges & Statuses
        badge_connected: 'সংযুক্ত',
        badge_disconnected: 'সংযোগ বিচ্ছিন্ন',
        badge_unpaid: 'বাকি / অপরিশোধিত',
        badge_on_duty: 'দোকানে উপস্থিত',
        badge_on_leave: 'ছুটিতে',
        
        // Header
        admin_new_order: 'অ্যাডমিন হিসেবে নতুন অর্ডার ও ফ্লোরিস্টকে দায়িত্ব 🌸',
        btn_new_order_short: 'নতুন অর্ডার 🌸',
        simulate_inv: 'ইনভয়েস সিমুলেশন ⚡',
        whatsapp_btn: 'হোয়াটসঅ্যাপ',
        admin_name: 'ম্যানেজার (অ্যাডমিন)',
        admin_role: 'পূর্ণ কর্তৃত্ব',
        switch_user_title: 'ব্যবহারকারী পরিবর্তন 👤',
        switch_user_desc: 'ফ্লোরিস্টের কাজ দেখার জন্য নির্বাচন করুন',
        florist_user: 'ফ্লোরিস্ট অ্যাকাউন্ট 🌸',
        
        // Dashboard Tab
        dash_title: 'সার্বিক কন্ট্রোল প্যানেল',
        accounting_banner_title: 'ক্লাউড অ্যাকাউন্টিং লিঙ্ক সক্রিয় এবং স্বয়ংক্রিয়',
        accounting_banner_desc: 'অ্যাকাউন্টিং সিস্টেমে (কায়োদ / দফাতরা / ওডু) ইনভয়েস তৈরি হলে এখানে তৎক্ষণাৎ যুক্ত হয় এবং গ্রাহক ও ড্রাইভারের কাছে হোয়াটসঅ্যাপ বার্তা যায়।',
        btn_simulate_now: 'ইনভয়েস রিসিভ পরীক্ষা করুন',
        btn_webhook_link: 'ওয়েবহুক লিঙ্ক',
        kpi_today_sales: 'আজকের মোট বিক্রি',
        kpi_today_orders: 'আজকের অর্ডার',
        kpi_month_sales: 'মাসিক মোট বিক্রি',
        kpi_month_completed: 'সম্পন্ন অর্ডার',
        kpi_unpaid_invoices: 'অপরিশোধিত ইনভয়েস (বাকি)',
        kpi_unpaid_desc: 'গ্রাহকদের কাছে বকেয়া',
        kpi_net_profit: 'আনুমানিক নিট লাভ',
        kpi_after_expenses: 'পরিচালন খরচ বাদে',
        
        // Orders Tracker
        order_flow_title: 'দোকানে অর্ডারের অগ্রগতি ও অবস্থা পর্যবেক্ষণ',
        order_flow_sub: 'হোয়াটসঅ্যাপ নোটিফিকেশন সহ লাইভ অটোমেটিক আপডেট',
        status_new: 'নতুন অর্ডার 🟡',
        status_preparing: 'তৈরি হচ্ছে 🌿',
        status_ready: 'ডেলিভারির জন্য প্রস্তুত 🌸',
        status_out: 'ড্রাইভারের কাছে 🚗',
        status_delivered: 'ডেলিভারি সম্পন্ন 💐',
        status_cancelled: 'বাতিল ❌',
        
        // Urgent Deliveries & Occasions
        urgent_orders_title: 'আজকের জরুরি ও নির্ধারিত ডেলিভারি',
        view_all_orders: 'সব অর্ডার দেখুন ←',
        vip_occasions_title: 'ভিআইপি গ্রাহকদের আসন্ন উপলক্ষ্য',
        auto_reminder: 'স্বয়ংক্রিয় রিমাইন্ডার',
        occasions_sub: 'অনুষ্ঠানের আগে গ্রাহককে হোয়াটসঅ্যাপে ফুলের পরামর্শ পাঠান!',
        top_bouquets_title: 'এই সপ্তাহে সর্বাধিক চাহিদাসম্পন্ন ফুল',
        
        // Orders Tab
        orders_title: 'অর্ডার ও ফুল বিন্যাস ব্যবস্থাপনা',
        florist_banner_title: 'ফ্লোরিস্টের কাজের বোর্ড 🌸',
        florist_only_badge: 'শুধু আমার অর্ডার',
        florist_banner_desc: 'এখানে শুধুমাত্র আপনাকে প্রস্তুত করার জন্য দেওয়া অর্ডারগুলো দেখা যাচ্ছে।',
        back_to_admin: 'অ্যাডমিন প্যানেলে ফিরুন ←',
        filter_status_label: 'অবস্থা অনুযায়ী ফিল্টার:',
        filter_all: 'সব',
        filter_new: 'নতুন',
        filter_prep: 'তৈরি হচ্ছে',
        filter_ready: 'প্রস্তুত',
        filter_out: 'ড্রাইভারের কাছে',
        filter_del: 'সম্পন্ন',
        order_search_ph: 'অর্ডার নম্বর, গ্রাহকের নাম বা ফোন দিয়ে খুঁজুন...',
        btn_add_order: 'নতুন অর্ডার',
        
        // Table Columns
        th_order_num: 'অর্ডার নম্বর',
        th_cust_phone: 'গ্রাহক / ফোন',
        th_rec_addr: 'প্রাপক ও ঠিকানা',
        th_items_flowers: 'ফুলের বিবরণ ও আইটেম',
        th_delivery_time: 'ডেলিভারির সময়',
        th_florist: 'ফ্লোরিস্ট (দোকানে) 🌸',
        th_driver: 'ড্রাইভার 🚗',
        th_total_payment: 'মোট ও পেমেন্ট',
        th_status: 'অর্ডারের অবস্থা',
        th_quick_actions: 'পদক্ষেপ',
        
        // Flower Colors
        flower_colors_label: 'ফুলের রং 🌸',
        card_gift: '💌 শুভেচ্ছা কার্ড',
        ref_image: 'রেফারেন্স ছবি 🖼️',
        paid: 'পরিশোধিত ✅',
        unpaid: 'অপরিশোধিত ⚠️',
        
        // Bottom Nav
        bottom_nav_home: 'মূলপাতা',
        bottom_nav_orders: 'অর্ডার',
        bottom_nav_whatsapp: 'হোয়াটসঅ্যাপ',
        bottom_nav_menu: 'মেনু',
        
        // Creative Tasks
        creative_tasks_title: 'নাবত ক্রিয়েটিভ প্রজেক্টস টাস্ক 🎨',
        creative_tasks_desc: 'দলের সদস্যদের মধ্যে কাজ বণ্টন ও ফলোআপ। যে কেউ নতুন টাস্ক পাঠাতে এবং সময়সীমা নির্ধারণ করতে পারেন।',
        btn_new_creative_task: 'নতুন ক্রিয়েটিভ টাস্ক পাঠান 🌸',
        crt_all_tasks: 'সকল টাস্ক',
        crt_pending: 'শুরুর অপেক্ষায় ⏳',
        crt_in_progress: 'চলমান 🎨',
        crt_completed: 'সম্পন্ন ✅',
        crt_start: 'কাজ শুরু করুন',
        crt_finish: 'টাস্ক সম্পন্ন করুন ✅',
        crt_done: 'সফলভাবে সম্পন্ন 🎉',
        
        // Common
        today_is: 'আজ',
        sar: 'রিয়াল',
        save: 'সংরক্ষণ',
        cancel: 'বাতিল',
        delete: 'মুছুন',
        edit: 'সম্পাদনা',
        refresh: 'রিফ্রেশ',
        search: 'অনুসন্ধান',
        print: 'প্রিন্ট',
        send: 'পাঠান',
        actions: 'পদক্ষেপ',
        close: 'বন্ধ করুন',
        notes: 'নোট',
        details: 'বিস্তারিত',
        due_date: 'ডেলিভারির সময়',
        assigned_to: 'দায়িত্বপ্রাপ্ত',
        created_by: 'অনুরোধকারী',
        
        // Languages
        lang_name: 'বাংলা',
        lang_switch: 'ভাষা'
    }
};

let currentLang = localStorage.getItem('nabt_language') || 'ar';
if (currentLang === 'ur') currentLang = 'bn'; // migrate legacy urdu to bengali

function setLanguage(lang) {
    if (!i18nTranslations[lang]) return;
    currentLang = lang;
    localStorage.setItem('nabt_language', lang);
    applyTranslations();
    
    // Close language dropdown if open
    const dropdown = document.getElementById('lang-switch-dropdown');
    if (dropdown) dropdown.classList.add('hidden');
    
    // Refresh current view headers and title
    if (typeof switchTab === 'function') {
        const activeNav = document.querySelector('.nav-item.bg-olive-700');
        const activeTabId = activeNav ? activeNav.id.replace('nav-', '') : 'dashboard';
        switchTab(activeTabId);
    }
    if (typeof loadOrders === 'function') loadOrders();
    if (typeof loadCreativeTasks === 'function') loadCreativeTasks();
    if (typeof loadPurchases === 'function') loadPurchases();
    if (typeof updateUserInterface === 'function') updateUserInterface();
}

function t(key, defaultVal = '') {
    if (i18nTranslations[currentLang] && i18nTranslations[currentLang][key]) {
        return i18nTranslations[currentLang][key];
    }
    if (i18nTranslations['ar'] && i18nTranslations['ar'][key]) {
        return i18nTranslations['ar'][key];
    }
    return defaultVal || key;
}

function applyTranslations() {
    const config = i18nTranslations[currentLang] || i18nTranslations['ar'];
    const html = document.documentElement;
    html.setAttribute('lang', currentLang);
    html.setAttribute('dir', config.dir);
    document.body.style.fontFamily = config.font;

    // Update all elements with data-i18n
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (config[key]) {
            el.textContent = config[key];
        }
    });

    // Update all elements with data-i18n-ph (placeholders)
    document.querySelectorAll('[data-i18n-ph]').forEach(el => {
        const key = el.getAttribute('data-i18n-ph');
        if (config[key]) {
            el.setAttribute('placeholder', config[key]);
        }
    });

    // Update Language Button label
    const langLabel = document.getElementById('current-lang-label');
    if (langLabel) {
        langLabel.textContent = (currentLang === 'ar') ? 'العربية' : (currentLang === 'en' ? 'English' : 'বাংলা');
    }

    // Refresh live date and clock in new language
    if (typeof updateLiveDateTime === 'function') {
        updateLiveDateTime();
    }
}

function toggleLangDropdown() {
    const dropdown = document.getElementById('lang-switch-dropdown');
    if (dropdown) dropdown.classList.toggle('hidden');
}

// Close language dropdown when clicking outside
document.addEventListener('click', (e) => {
    const btn = document.getElementById('current-lang-btn');
    const dropdown = document.getElementById('lang-switch-dropdown');
    if (dropdown && !dropdown.classList.contains('hidden')) {
        if (!dropdown.contains(e.target) && !btn.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    }
});
