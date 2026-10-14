/**
 * Nabt Flowers ERP - Core Frontend Engine
 */

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Local Date and Live Clock Engine
function getLocalDateString(d = new Date()) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

let liveClockInterval = null;
function updateLiveDateTime() {
    const now = new Date();
    const dateEl = document.getElementById('current-date-display');
    const timeEl = document.getElementById('current-time-display');

    const lang = (typeof currentLang !== 'undefined' && currentLang) ? currentLang : 'ar';
    let locale = 'ar-SA';
    if (lang === 'en') locale = 'en-US';
    else if (lang === 'bn') locale = 'bn-BD';

    if (dateEl) {
        const dateOptions = {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        };
        dateEl.textContent = now.toLocaleDateString(locale, dateOptions);
    }

    if (timeEl) {
        const timeOptions = {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        };
        timeEl.textContent = now.toLocaleTimeString(locale, timeOptions);
    }
}

function startLiveClock() {
    if (liveClockInterval) clearInterval(liveClockInterval);
    updateLiveDateTime();
    liveClockInterval = setInterval(updateLiveDateTime, 1000);
}

let allProducts = [];
let allDrivers = [];
let activeOrderFilter = 'all';
let activeInvoiceFilter = 'all';
let currentActiveChatPhone = null;

// User Management & Active Session
let currentUser = null;

function isManagerRole(role) {
    const r = role || (currentUser && currentUser.role);
    return ['general_manager', 'operations_manager', 'branch_manager', 'admin', 'manager'].includes(r);
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    startLiveClock();
    if (typeof applyTranslations === 'function') {
        applyTranslations();
    }
    initIcons();
    initUserProfileMenu();

    // Check login state:
    const isExplicitLoginRoute = window.location.pathname === '/login' || window.location.search.includes('login');
    const savedUser = localStorage.getItem('nabt_current_user');

    if (!savedUser || isExplicitLoginRoute) {
        currentUser = null;
        showLoginScreen();
    } else {
        try {
            currentUser = JSON.parse(savedUser);
            if (!currentUser || !currentUser.id || !currentUser.role) {
                throw new Error("Invalid session");
            }
            hideLoginScreen();
            updateUserInterface();
            loadDashboardData();
            loadProducts();
            loadDrivers();
            checkWhatsAppStatus();
        } catch (e) {
            currentUser = null;
            localStorage.removeItem('nabt_current_user');
            showLoginScreen();
        }
    }
});

function showLoginScreen() {
    const screen = document.getElementById('login-screen');
    if (screen) {
        screen.classList.remove('hidden');
        screen.style.display = 'flex';
    }
    toggleMobileSidebar(false);
    const idInput = document.getElementById('page-login-identifier');
    const pwdInput = document.getElementById('page-login-password');
    if (idInput) idInput.value = '';
    if (pwdInput) pwdInput.value = '';
    const err = document.getElementById('page-login-error');
    if (err) err.classList.add('hidden');
    initIcons();
}

function hideLoginScreen() {
    const screen = document.getElementById('login-screen');
    if (screen) {
        screen.classList.add('hidden');
        screen.style.display = 'none';
    }
}

function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    input.type = input.type === 'password' ? 'text' : 'password';
}

function handleUserLogout() {
    if (!confirm("هل ترغب في تسجيل الخروج من النظام 🌸؟")) return;
    localStorage.removeItem('nabt_current_user');
    currentUser = null;
    showLoginScreen();
    const idInput = document.getElementById('page-login-identifier');
    const pwdInput = document.getElementById('page-login-password');
    if (idInput) idInput.value = '';
    if (pwdInput) pwdInput.value = '';
    const err = document.getElementById('page-login-error');
    if (err) err.classList.add('hidden');
    // Clear UI tables so no data remains
    const tbody = document.getElementById('orders-table-tbody');
    if (tbody) tbody.innerHTML = '';
    const mobileCards = document.getElementById('orders-mobile-cards');
    if (mobileCards) mobileCards.innerHTML = '';
}

async function handlePageLogin(event) {
    if (event) event.preventDefault();
    const identifier = document.getElementById('page-login-identifier')?.value.trim();
    const password = document.getElementById('page-login-password')?.value.trim();
    const err = document.getElementById('page-login-error');
    const errText = document.getElementById('page-login-error-text');
    const btn = document.getElementById('page-login-submit-btn');

    if (!identifier || !password) {
        if (err) {
            if (errText) errText.textContent = "يرجى إدخال اسم المستخدم أو الجوال وكلمة المرور";
            err.classList.remove('hidden');
        }
        return;
    }

    if (err) err.classList.add('hidden');
    if (btn) btn.disabled = true;

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ identifier, password })
        });
        const data = await res.json();

        if (res.ok && data.success) {
            const u = data.user;
            currentUser = {
                role: u.role,
                id: u.id,
                name: u.name,
                username: u.username,
                phone: u.phone
            };
            localStorage.setItem('nabt_current_user', JSON.stringify(currentUser));
            hideLoginScreen();
            updateUserInterface();
            loadOrders();
            loadDashboardData();
            loadProducts();
            loadDrivers();
            checkWhatsAppStatus();
            loadPurchases();
            loadCreativeTasks();
        } else {
            if (err) {
                if (errText) errText.textContent = data.detail || "اسم المستخدم أو كلمة المرور غير صحيحة";
                err.classList.remove('hidden');
            }
        }
    } catch (e) {
        console.error("Login request error:", e);
        if (err) {
            if (errText) errText.textContent = "تعذر الاتصال بالخادم، يرجى المحاولة مرة أخرى";
            err.classList.remove('hidden');
        }
    } finally {
        if (btn) btn.disabled = false;
    }
}

function initIcons() {
    if (typeof lucide !== 'undefined' && lucide.createIcons) {
        try {
            lucide.createIcons();
        } catch (e) {
            console.warn("Lucide createIcons warning:", e);
        }
    }
}

// MOBILE DRAWER TOGGLE
function toggleMobileSidebar(forceState = null) {
    const sidebar = document.getElementById('sidebar-main');
    const overlay = document.getElementById('mobile-sidebar-overlay');
    if (!sidebar) return;

    const isOpen = sidebar.classList.contains('mobile-open');
    const shouldOpen = (forceState !== null) ? forceState : !isOpen;

    if (shouldOpen) {
        sidebar.classList.add('mobile-open');
        if (overlay) overlay.classList.remove('hidden');
    } else {
        sidebar.classList.remove('mobile-open');
        if (overlay) overlay.classList.add('hidden');
    }
}

// TAB NAVIGATION
function switchTab(tabId) {
    // Auto close mobile drawer when user picks a section
    toggleMobileSidebar(false);

    // Florist Protection: Cannot access Invoices or Expenses
    if (currentUser && currentUser.role === 'florist' && (tabId === 'invoices' || tabId === 'expenses')) {
        tabId = 'orders';
    }

    const tabs = ['dashboard', 'orders', 'whatsapp', 'invoices', 'drivers', 'customers', 'expenses', 'products', 'employees', 'purchases', 'creative-tasks'];
    tabs.forEach(t => {
        const view = document.getElementById(`view-${t}`);
        const nav = document.getElementById(`nav-${t}`);
        if (view) view.classList.add('hidden');
        if (nav) {
            nav.classList.remove('bg-olive-700', 'text-cream-50', 'shadow-md', 'shadow-olive-950/40');
            nav.classList.add('text-cream-200/80', 'hover:bg-olive-800', 'hover:text-white');
        }
    });

    const activeView = document.getElementById(`view-${tabId}`);
    const activeNav = document.getElementById(`nav-${tabId}`);
    if (activeView) activeView.classList.remove('hidden');
    if (activeNav) {
        activeNav.classList.add('bg-olive-700', 'text-cream-50', 'shadow-md', 'shadow-olive-950/40');
        activeNav.classList.remove('text-cream-200/80', 'hover:bg-olive-800', 'hover:text-white');
    }

    // Update header title
    const titles = {
        dashboard: { title: (typeof t === 'function' ? t('nav_dashboard', 'لوحة التحكم') : 'لوحة التحكم'), icon: 'layout-dashboard' },
        orders: { title: (typeof t === 'function' ? t('orders_title', 'إدارة الطلبات وتنسيق الورد') : 'إدارة الطلبات وتنسيق الورد'), icon: 'shopping-bag' },
        whatsapp: { title: (typeof t === 'function' ? t('nav_whatsapp', 'مركز محادثات الواتس اب') : 'مركز محادثات الواتس اب'), icon: 'message-circle' },
        invoices: { title: (typeof t === 'function' ? t('nav_invoices', 'الحسابات والفواتير وسندات القبض') : 'الحسابات والفواتير وسندات القبض'), icon: 'receipt' },
        drivers: { title: (typeof t === 'function' ? t('nav_drivers', 'إدارة المناديب والتوصيل') : 'إدارة المناديب والتوصيل'), icon: 'truck' },
        customers: { title: (typeof t === 'function' ? t('nav_customers', 'إدارة العملاء والمناسبات') : 'إدارة العملاء والمناسبات'), icon: 'users' },
        expenses: { title: (typeof t === 'function' ? t('nav_expenses', 'المصروفات والأرباح الصافية') : 'المصروفات والأرباح الصافية'), icon: 'wallet' },
        products: { title: (typeof t === 'function' ? t('nav_products', 'كتالوج الورد والهدايا') : 'كتالوج الورد والهدايا'), icon: 'boxes' },
        employees: { title: (typeof t === 'function' ? t('nav_employees', 'إدارة المنسقين والموظفين والإجازات') : 'إدارة المنسقين والموظفين والإجازات'), icon: 'user-check' },
        purchases: { title: (typeof t === 'function' ? t('nav_purchases', 'طلبات المشتريات والتعميد والموافقات') : 'طلبات المشتريات والتعميد والموافقات'), icon: 'shopping-cart' },
        'creative-tasks': { title: (typeof t === 'function' ? t('nav_creative_tasks', 'مهام مشاريع نبت الإبداعية') : 'مهام مشاريع نبت الإبداعية'), icon: 'sparkles' }
    };

    const header = document.getElementById('current-tab-title');
    if (header && titles[tabId]) {
        header.innerHTML = `<i data-lucide="${titles[tabId].icon}" class="w-5 h-5 text-terracotta-600"></i> ${titles[tabId].title}`;
    }

    // Trigger tab-specific refresh
    if (tabId === 'dashboard') loadDashboardData();
    if (tabId === 'orders') loadOrders();
    if (tabId === 'whatsapp') loadWhatsAppConversations();
    if (tabId === 'invoices') loadInvoices();
    if (tabId === 'drivers') loadDriversView();
    if (tabId === 'customers') loadCustomers();
    if (tabId === 'expenses') loadExpenses();
    if (tabId === 'products') loadProducts();
    if (tabId === 'employees') { loadEmployees(); loadLeaves(); }
    if (tabId === 'purchases') loadPurchases();
    if (tabId === 'creative-tasks') loadCreativeTasks();

    initIcons();
}

// 1. DASHBOARD LOGIC
async function loadDashboardData() {
    try {
        let statsUrl = '/api/dashboard/stats';
        if (currentUser && currentUser.role === 'florist' && currentUser.id) {
            statsUrl += `?florist_id=${currentUser.id}`;
        }
        const res = await fetch(statsUrl);
        const data = await res.json();

        // Cards Population
        if (currentUser && currentUser.role === 'florist') {
            const elToday = document.getElementById('dash-florist-today-orders');
            const elPrep = document.getElementById('dash-florist-preparing-orders');
            const elReady = document.getElementById('dash-florist-ready-orders');
            const elMonth = document.getElementById('dash-florist-month-orders');
            if (elToday) elToday.textContent = data.today_orders_count;
            if (elPrep) elPrep.textContent = data.status_counts.preparing || 0;
            if (elReady) elReady.textContent = (data.status_counts.ready || 0);
            if (elMonth) elMonth.textContent = data.monthly_orders_count;
        } else {
            const elTodaySales = document.getElementById('dash-today-sales');
            const elTodayCount = document.getElementById('dash-today-orders-count');
            const elMonthSales = document.getElementById('dash-month-sales');
            const elMonthCount = document.getElementById('dash-month-orders-count');
            const elUnpaid = document.getElementById('dash-unpaid-invoices');
            const elProfit = document.getElementById('dash-net-profit');

            if (elTodaySales) elTodaySales.textContent = `${data.today_sales.toLocaleString()} ر.س`;
            if (elTodayCount) elTodayCount.textContent = data.today_orders_count;
            if (elMonthSales) elMonthSales.textContent = `${data.monthly_sales.toLocaleString()} ر.س`;
            if (elMonthCount) elMonthCount.textContent = data.monthly_orders_count;
            if (elUnpaid) elUnpaid.textContent = `${data.total_unpaid.toLocaleString()} ر.س`;
            if (elProfit) elProfit.textContent = `${data.net_profit.toLocaleString()} ر.س`;
        }

        // Status counts
        const sc = data.status_counts;
        document.getElementById('status-count-new').textContent = sc.new || 0;
        document.getElementById('status-count-preparing').textContent = sc.preparing || 0;
        document.getElementById('status-count-ready').textContent = sc.ready || 0;
        document.getElementById('status-count-out_for_delivery').textContent = sc.out_for_delivery || 0;
        document.getElementById('status-count-delivered').textContent = sc.delivered || 0;
        document.getElementById('status-count-cancelled').textContent = sc.cancelled || 0;

        const badgeNavOrders = document.getElementById('badge-nav-orders');
        if (badgeNavOrders) {
            badgeNavOrders.textContent = (currentUser && currentUser.role === 'florist')
                ? ((sc.new || 0) + (sc.preparing || 0))
                : ((sc.new || 0) + (sc.preparing || 0) + (sc.out_for_delivery || 0));
            const badgeBottom = document.getElementById('badge-bottom-orders');
            if (badgeBottom) badgeBottom.textContent = badgeNavOrders.textContent;
        }

        // Urgent Orders Table & Mobile Cards
        const tbody = document.getElementById('dash-urgent-orders-tbody');
        const urgentMobile = document.getElementById('dash-urgent-mobile-cards');
        if (tbody) tbody.innerHTML = '';
        if (urgentMobile) urgentMobile.innerHTML = '';

        if (data.urgent_orders.length === 0) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-slate-400 text-xs">لا توجد طلبات معلقة لليوم، كل الطلبات مكتملة 🌸</td></tr>`;
            if (urgentMobile) urgentMobile.innerHTML = `<div class="p-4 bg-white rounded-xl border border-cream-200 text-center text-slate-400 text-xs">لا توجد طلبات معلقة لليوم، كل الطلبات مكتملة 🌸</div>`;
        } else {
            data.urgent_orders.forEach(o => {
                // Desktop row
                if (tbody) {
                    const tr = document.createElement('tr');
                    tr.className = 'hover:bg-slate-50 transition-colors text-xs';
                    tr.innerHTML = `
                        <td class="py-2.5 px-3 font-bold text-slate-800">${o.order_number}</td>
                        <td class="py-2.5 px-3">
                            <strong class="text-slate-800">${o.customer_name}</strong>
                            ${o.recipient_name && o.recipient_name !== o.customer_name ? `<span class="block text-[11px] text-slate-500">لـ: ${o.recipient_name}</span>` : ''}
                        </td>
                        <td class="py-2.5 px-3 font-medium text-slate-600">${o.delivery_time_slot || 'اليوم'}</td>
                        <td class="py-2.5 px-3 font-medium text-slate-700">${o.driver_name || '<span class="text-amber-600">غير معين</span>'}</td>
                        <td class="py-2.5 px-3 font-black text-slate-900">${currentUser && currentUser.role === 'florist' ? '-' : `${o.total_amount} ر.س`}</td>
                        <td class="py-2.5 px-3">${renderStatusBadge(o.status)}</td>
                        <td class="py-2.5 px-3 text-center">
                            <button onclick="advanceOrderStatus(${o.id}, '${o.status}')" class="text-[11px] bg-brand-50 hover:bg-brand-100 text-brand-700 font-bold px-2.5 py-1 rounded-lg border border-brand-200 cursor-pointer">
                                ${getNextStatusLabel(o.status)}
                            </button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                }

                // Mobile card (100% full width, perfect on mobile)
                if (urgentMobile) {
                    const card = document.createElement('div');
                    card.className = 'mobile-card bg-cream-50/70 p-3.5 rounded-2xl border border-cream-200 shadow-xs space-y-2';
                    card.innerHTML = `
                        <div class="flex items-center justify-between border-b border-cream-200/60 pb-2">
                            <span class="font-bold text-xs text-olive-900">${o.order_number}</span>
                            <div>${renderStatusBadge(o.status)}</div>
                        </div>
                        <div class="text-xs">
                            <strong class="text-slate-800 block">${o.customer_name}</strong>
                            ${o.recipient_name && o.recipient_name !== o.customer_name ? `<span class="text-[11px] text-slate-500 block">لـ: ${o.recipient_name}</span>` : ''}
                        </div>
                        <div class="flex items-center justify-between text-xs text-slate-600">
                            <span>موعد التسليم: <strong>${o.delivery_time_slot || 'اليوم'}</strong></span>
                            <span>المندوب: <strong>${o.driver_name || 'غير معين'}</strong></span>
                        </div>
                        ${(!currentUser || currentUser.role !== 'florist') ? `<div class="text-xs font-black text-slate-900">${o.total_amount} ر.س</div>` : ''}
                        <div class="pt-2 border-t border-cream-200/60 flex items-center justify-between">
                            <button onclick="openOrderDetailModal(${o.id})" class="text-xs text-olive-700 hover:underline font-bold flex items-center gap-1">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i> التفاصيل
                            </button>
                            <button onclick="advanceOrderStatus(${o.id}, '${o.status}')" class="text-xs bg-brand-50 hover:bg-brand-100 text-brand-700 font-bold px-3 py-1.5 rounded-lg border border-brand-200 cursor-pointer">
                                ${getNextStatusLabel(o.status)}
                            </button>
                        </div>
                    `;
                    urgentMobile.appendChild(card);
                }
            });
        }

        // Occasions list
        const occList = document.getElementById('dash-occasions-list');
        occList.innerHTML = '';
        if (data.upcoming_occasions.length === 0) {
            occList.innerHTML = `<p class="text-xs text-slate-400">لا توجد مناسبات مسجلة قريبة</p>`;
        } else {
            data.upcoming_occasions.forEach(occ => {
                const div = document.createElement('div');
                div.className = 'p-3 bg-purple-50/50 border border-purple-100 rounded-xl flex items-center justify-between text-xs';
                div.innerHTML = `
                    <div>
                        <strong class="text-slate-800 block">${occ.customer_name}</strong>
                        <span class="text-purple-700 font-semibold">${occ.occasion_type} - ${occ.date}</span>
                        ${occ.notes ? `<p class="text-[11px] text-slate-500 mt-0.5">${occ.notes}</p>` : ''}
                    </div>
                    <button onclick="openWhatsAppChatDirect('${occ.customer_phone}', '${occ.customer_name}', 'أهلاً بك عميلنا العزيز ${occ.customer_name} من نبت للورد 🌸 نقترب من مناسبة (${occ.occasion_type})، يسعدنا تقديم خصم خاص على تشكيلة الورود المميزة!')" class="text-emerald-700 bg-white border border-emerald-300 hover:bg-emerald-50 px-2 py-1 rounded-lg text-[11px] font-bold flex items-center gap-1">
                        <i data-lucide="message-circle" class="w-3 h-3 text-emerald-600"></i>
                        واتساب
                    </button>
                `;
                occList.appendChild(div);
            });
        }

        // Top Products
        const prodList = document.getElementById('dash-top-products-list');
        prodList.innerHTML = '';
        data.top_products.forEach(p => {
            const div = document.createElement('div');
            div.className = 'flex items-center justify-between text-xs py-1.5 border-b border-slate-100 last:border-0';
            div.innerHTML = `
                <span class="text-slate-700 font-medium truncate max-w-[200px]">${p.product_name}</span>
                <span class="text-brand-700 font-bold bg-brand-50 px-2 py-0.5 rounded-full">${p.total_qty} ورد</span>
            `;
            prodList.appendChild(div);
        });

        initIcons();
    } catch (err) {
        console.error("Dashboard stats error:", err);
    }
}

// USER PROFILE MENU & ROLE-BASED VISIBILITY
function toggleUserSwitchDropdown() {
    const dropdown = document.getElementById('user-switch-dropdown');
    if (!dropdown) return;
    dropdown.classList.toggle('hidden');
}

function initUserProfileMenu() {
    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
        const btn = document.getElementById('current-user-btn');
        const dropdown = document.getElementById('user-switch-dropdown');
        if (dropdown && !dropdown.classList.contains('hidden')) {
            if (!dropdown.contains(e.target) && !btn?.contains(e.target)) {
                dropdown.classList.add('hidden');
            }
        }
    });
}

// ========================================================
// AUTHENTICATION & PASSWORD MANAGEMENT
// ========================================================

function openChangePasswordModal() {
    const dropdown = document.getElementById('user-switch-dropdown');
    if (dropdown) dropdown.classList.add('hidden');

    const subtitle = document.getElementById('pwd-modal-user-subtitle');
    if (subtitle) {
        const uname = currentUser.username || (currentUser.id === 1 ? 'yasser' : currentUser.id === 2 ? 'faisal' : currentUser.id === 3 ? 'nader' : currentUser.id === 4 ? 'omar' : 'rico');
        subtitle.textContent = `تغيير كلمة المرور لحساب: ${currentUser.name} (@${uname})`;
    }

    // Reset inputs
    document.getElementById('pwd-current-input').value = '';
    document.getElementById('pwd-new-input').value = '';
    document.getElementById('pwd-confirm-input').value = '';

    const err = document.getElementById('pwd-error-msg');
    const succ = document.getElementById('pwd-success-msg');
    if (err) { err.classList.add('hidden'); err.textContent = ''; }
    if (succ) { succ.classList.add('hidden'); succ.textContent = ''; }

    openModal('modal-change-password');
}

async function handleFormChangePassword(event) {
    event.preventDefault();
    const currPwd = document.getElementById('pwd-current-input').value.trim();
    const newPwd = document.getElementById('pwd-new-input').value.trim();
    const confirmPwd = document.getElementById('pwd-confirm-input').value.trim();

    const err = document.getElementById('pwd-error-msg');
    const succ = document.getElementById('pwd-success-msg');
    if (err) err.classList.add('hidden');
    if (succ) succ.classList.add('hidden');

    if (newPwd !== confirmPwd) {
        if (err) {
            err.textContent = "⚠️ كلمة المرور الجديدة وتأكيدها غير متطابقين!";
            err.classList.remove('hidden');
        }
        return;
    }

    if (newPwd.length < 3) {
        if (err) {
            err.textContent = "⚠️ يجب أن تتكون كلمة المرور من 3 خانات على الأقل";
            err.classList.remove('hidden');
        }
        return;
    }

    try {
        const res = await fetch('/api/auth/change-password', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                employee_id: currentUser.id || 1,
                current_password: currPwd,
                new_password: newPwd
            })
        });

        const data = await res.json();
        if (res.ok && data.success) {
            if (succ) {
                succ.textContent = `✅ ${data.message}`;
                succ.classList.remove('hidden');
            }
            setTimeout(() => {
                closeModal('modal-change-password');
                alert("✨ تم حفظ وتغيير كلمة المرور الجديدة بنجاح!");
            }, 1000);
        } else {
            if (err) {
                err.textContent = `❌ ${data.detail || 'تعذر تغيير كلمة المرور'}`;
                err.classList.remove('hidden');
            }
        }
    } catch (e) {
        console.error("Change password error:", e);
        if (err) {
            err.textContent = "❌ حدث خطأ في الاتصال بالخادم";
            err.classList.remove('hidden');
        }
    }
}

function updateUserInterface() {
    if (!currentUser) return;

    const avatar = document.getElementById('current-user-avatar');
    const nameEl = document.getElementById('current-user-name');
    const roleBadgeEl = document.getElementById('current-user-role-badge');

    const menuAvatar = document.getElementById('menu-user-avatar');
    const menuName = document.getElementById('menu-user-name');
    const menuRole = document.getElementById('menu-user-role');

    const floristBanner = document.getElementById('florist-mode-banner');
    const floristBannerTitle = document.getElementById('florist-banner-title');
    const floristBannerDesc = document.getElementById('florist-banner-desc');

    // Navigation elements to hide/show for florist
    const navInvoices = document.getElementById('nav-invoices');
    const navExpenses = document.getElementById('nav-expenses');

    // Dashboard elements
    const dashAccountingBanner = document.getElementById('dash-accounting-banner');
    const dashAdminCards = document.getElementById('dash-admin-kpi-cards');
    const dashFloristCards = document.getElementById('dash-florist-kpi-cards');
    const dashOrderFlowTitle = document.getElementById('dash-order-flow-title');
    const dashUrgentTableTitle = document.getElementById('dash-urgent-table-title');
    const dashUrgentTableContainer = document.getElementById('dash-urgent-table-container');
    const dashSideWidgets = document.getElementById('dash-side-widgets');

    const isManager = isManagerRole(currentUser.role);

    if (currentUser.role === 'florist') {
        const initial = (currentUser.name || 'م').charAt(0);
        if (avatar) {
            avatar.textContent = initial;
            avatar.className = 'w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-tr from-purple-700 to-pink-600 text-white flex items-center justify-center font-bold text-xs shadow-xs';
        }
        if (nameEl) nameEl.textContent = currentUser.name;
        if (roleBadgeEl) {
            roleBadgeEl.className = 'text-[10px] text-purple-600 font-semibold flex items-center gap-1';
            roleBadgeEl.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-purple-500"></span> يوزر منسق ورد 🌸 (طلباتي فقط)';
        }

        if (menuAvatar) {
            menuAvatar.textContent = initial;
            menuAvatar.className = 'w-9 h-9 rounded-full bg-purple-700 text-white flex items-center justify-center font-bold text-xs shadow-xs';
        }
        if (menuName) menuName.textContent = currentUser.name;
        if (menuRole) menuRole.textContent = 'منسق ورد 🌸 (طلباتي فقط)';

        // Show florist banner
        if (floristBanner) {
            floristBanner.classList.remove('hidden');
            if (floristBannerTitle) floristBannerTitle.textContent = `لوحة مهام المنسق (${currentUser.name}) 🌸`;
            if (floristBannerDesc) floristBannerDesc.textContent = `الطلبات المسندة إليك للبدء بتنسيقها وتجهيزها.`;
        }

        // HIDE Invoices & Expenses from Sidebar Navigation
        if (navInvoices) navInvoices.classList.add('hidden');
        if (navExpenses) navExpenses.classList.add('hidden');

        // DASHBOARD: Hide accounting live sync banner & store financial KPI cards
        if (dashAccountingBanner) dashAccountingBanner.classList.add('hidden');
        if (dashAdminCards) dashAdminCards.classList.add('hidden');
        if (dashFloristCards) dashFloristCards.classList.remove('hidden');

        // Update Dashboard Titles for Florist
        if (dashOrderFlowTitle) dashOrderFlowTitle.textContent = 'متابعة تدفق وحالات طلباتي المسندة 🌸';
        if (dashUrgentTableTitle) dashUrgentTableTitle.textContent = 'طلباتي المستعجلة والمقررة اليوم للتنسيق 🌸';

        // Focus dashboard on florist urgent table (full width)
        if (dashSideWidgets) dashSideWidgets.classList.add('hidden');
        if (dashUrgentTableContainer) {
            dashUrgentTableContainer.classList.remove('lg:col-span-2');
            dashUrgentTableContainer.classList.add('lg:col-span-3');
        }

        // If currently viewing hidden invoices or expenses, redirect immediately to orders
        const viewInvoices = document.getElementById('view-invoices');
        const viewExpenses = document.getElementById('view-expenses');
        if ((viewInvoices && !viewInvoices.classList.contains('hidden')) || (viewExpenses && !viewExpenses.classList.contains('hidden'))) {
            switchTab('orders');
        }

    } else {
        // MANAGERS: ياسر (مدير عام)، فيصل (مدير تشغيلي)، نادر (مدير فرع)
        let initial = 'م';
        let roleBadgeText = 'إدارة النظام • صلاحيات شاملة 🛡️';
        let roleBadgeClass = 'text-[10px] text-slate-700 font-semibold flex items-center gap-1';
        let dotColor = 'bg-slate-500';
        let avatarBg = 'from-slate-800 to-slate-900';
        let menuRoleText = 'إدارة النظام 👑';

        if (currentUser.role === 'general_manager') {
            initial = 'ي';
            roleBadgeText = 'المدير العام • صلاحيات شاملة 👑';
            roleBadgeClass = 'text-[10px] text-amber-700 font-semibold flex items-center gap-1';
            dotColor = 'bg-amber-500';
            avatarBg = 'from-amber-600 to-amber-700';
            menuRoleText = 'المدير العام (صلاحيات شاملة) 👑';
        } else if (currentUser.role === 'operations_manager') {
            initial = 'ف';
            roleBadgeText = 'مدير تشغيلي • صلاحيات شاملة ⚙️';
            roleBadgeClass = 'text-[10px] text-emerald-700 font-semibold flex items-center gap-1';
            dotColor = 'bg-emerald-500';
            avatarBg = 'from-slate-900 to-olive-800';
            menuRoleText = 'مدير تشغيلي (صلاحيات شاملة) ⚙️';
        } else if (currentUser.role === 'branch_manager') {
            initial = 'ن';
            roleBadgeText = 'مدير الفرع • صلاحيات شاملة 🏢';
            roleBadgeClass = 'text-[10px] text-blue-700 font-semibold flex items-center gap-1';
            dotColor = 'bg-blue-500';
            avatarBg = 'from-blue-700 to-indigo-800';
            menuRoleText = 'مدير الفرع (صلاحيات شاملة) 🏢';
        }

        if (avatar) {
            avatar.textContent = initial;
            avatar.className = `w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-tr ${avatarBg} text-white flex items-center justify-center font-bold text-xs shadow-xs`;
        }
        if (nameEl) nameEl.textContent = currentUser.name || 'المدير';
        if (roleBadgeEl) {
            roleBadgeEl.className = roleBadgeClass;
            roleBadgeEl.innerHTML = `<span class="w-1.5 h-1.5 rounded-full ${dotColor}"></span> ${roleBadgeText}`;
        }

        if (menuAvatar) {
            menuAvatar.textContent = initial;
            menuAvatar.className = `w-9 h-9 rounded-full bg-gradient-to-tr ${avatarBg} text-white flex items-center justify-center font-bold text-xs shadow-xs`;
        }
        if (menuName) menuName.textContent = currentUser.name || 'المدير';
        if (menuRole) menuRole.textContent = menuRoleText;

        if (floristBanner) floristBanner.classList.add('hidden');

        // SHOW Invoices & Expenses for Managers
        if (navInvoices) navInvoices.classList.remove('hidden');
        if (navExpenses) navExpenses.classList.remove('hidden');

        // DASHBOARD: Show full admin/manager dashboard
        if (dashAccountingBanner) dashAccountingBanner.classList.remove('hidden');
        if (dashAdminCards) dashAdminCards.classList.remove('hidden');
        if (dashFloristCards) dashFloristCards.classList.add('hidden');

        if (dashOrderFlowTitle) dashOrderFlowTitle.textContent = (typeof t === 'function' ? t('order_flow_title', 'متابعة تدفق وحالات الطلبات في المحل') : 'متابعة تدفق وحالات الطلبات في المحل');
        if (dashUrgentTableTitle) dashUrgentTableTitle.textContent = 'طلبات التوصيل المستعجلة والمقررة اليوم';

        if (dashSideWidgets) dashSideWidgets.classList.remove('hidden');
        if (dashUrgentTableContainer) {
            dashUrgentTableContainer.classList.add('lg:col-span-2');
            dashUrgentTableContainer.classList.remove('lg:col-span-3');
        }
    }
    initIcons();
}

// 2. ORDERS LOGIC
async function loadOrders() {
    try {
        const search = document.getElementById('order-search-input')?.value || '';
        let url = `/api/orders?status=${activeOrderFilter}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        
        // If current user is a florist, fetch only their assigned orders!
        if (currentUser && currentUser.role === 'florist' && currentUser.id) {
            url += `&florist_id=${currentUser.id}`;
        }

        const res = await fetch(url);
        const orders = await res.json();

        const tbody = document.getElementById('orders-table-tbody');
        const mobileContainer = document.getElementById('orders-mobile-cards');
        if (tbody) tbody.innerHTML = '';
        if (mobileContainer) mobileContainer.innerHTML = '';

        if (orders.length === 0) {
            const emptyText = (currentUser && currentUser.role === 'florist')
                ? `لا توجد طلبات مسندة للمنسق (${currentUser.name || ''}) حالياً في هذا الفلتر 🌸`
                : `لا توجد طلبات تطابق الفلتر المحدد`;
            if (tbody) tbody.innerHTML = `<tr><td colspan="10" class="text-center py-10 text-slate-400 text-xs">${emptyText}</td></tr>`;
            if (mobileContainer) mobileContainer.innerHTML = `<div class="p-6 bg-white rounded-2xl border border-cream-200 text-center text-slate-400 text-xs">${emptyText}</div>`;
            return;
        }

        orders.forEach(o => {
            const itemsSummary = o.items ? o.items.map(it => `${it.product_name} (×${it.quantity})`).join(', ') : '-';

            // Shared Action Buttons HTML
            const actionsHtml = `
                <!-- View details eye icon -->
                <button onclick="openOrderDetailModal(${o.id})" title="عرض تفاصيل الطلب والتوقيتات ومسار التنسيق" class="p-1.5 rounded-lg hover:bg-olive-100 text-olive-800 transition-all cursor-pointer">
                    <i data-lucide="eye" class="w-4 h-4"></i>
                </button>

                <!-- FLORIST WORKFLOW BUTTONS -->
                ${currentUser && currentUser.role === 'florist' && o.status === 'new' && o.acceptance_status !== 'accepted' ? `
                    <button onclick="acceptOrderByFlorist(${o.id})" class="text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-3 py-1.5 rounded-xl shadow-sm transition-all cursor-pointer">
                        قبول الطلب ✅
                    </button>
                    <button onclick="rejectOrderByFlorist(${o.id})" class="text-xs bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-300 font-bold px-3 py-1.5 rounded-xl transition-all cursor-pointer" title="اعتذار وتحويل تلقائي للزميل البديل (ريكو)">
                        اعتذار ❌
                    </button>
                ` : ''}

                ${((currentUser && currentUser.role === 'florist') || isManagerRole()) && (o.status === 'preparing' || o.status === 'ready' || !o.completed_image) ? `
                    <button onclick="openFloristCompleteWorkModal(${o.id}, '${o.order_number}')" class="text-xs bg-purple-600 hover:bg-purple-700 text-white font-bold px-2.5 py-1.5 rounded-xl shadow-sm flex items-center gap-1 transition-all cursor-pointer">
                        <i data-lucide="camera" class="w-3.5 h-3.5"></i>
                        <span>${o.completed_image ? 'تحديث الصورة 📸' : 'رفع صورة الورد 📸'}</span>
                    </button>
                ` : ''}

                <!-- ADMIN / MANAGER APPROVAL BUTTON -->
                ${isManagerRole() && o.completed_image && o.approval_status !== 'approved' ? `
                    <button onclick="openManagerApprovalModal(${o.id})" class="text-xs bg-amber-500 hover:bg-amber-600 text-white font-black px-3 py-1.5 rounded-xl shadow-md animate-pulse flex items-center gap-1.5 transition-all cursor-pointer">
                        <i data-lucide="shield-check" class="w-4 h-4"></i>
                        <span>تعميد الطلب 👑</span>
                    </button>
                ` : ''}

                <!-- Advance status button for Managers (Ready -> Out for delivery -> Delivered) -->
                ${isManagerRole() && (o.status !== 'new' || o.acceptance_status === 'accepted') ? `
                    <button onclick="advanceOrderStatus(${o.id}, '${o.status}')" title="ترقية الحالة" class="text-xs bg-terracotta-50 hover:bg-terracotta-100 text-terracotta-700 font-bold px-2.5 py-1.5 rounded-xl border border-terracotta-200 transition-all cursor-pointer">
                        ${getNextStatusLabel(o.status)}
                    </button>
                ` : ''}

                <button onclick="openInvoicePrintModalByOrder(${o.id})" title="عرض وطباعة الفاتورة" class="p-1.5 rounded-lg hover:bg-cream-200 text-olive-700 cursor-pointer">
                    <i data-lucide="printer" class="w-4 h-4"></i>
                </button>
                <button onclick="openWhatsAppChatDirect('${o.customer_phone}', '${o.customer_name}', 'أهلاً بك عميلنا العزيز في نبت 🌸 بخصوص طلبك رقم ${o.order_number}')" title="محادثة واتساب" class="p-1.5 rounded-lg hover:bg-emerald-50 text-emerald-600 cursor-pointer">
                    <i data-lucide="message-circle" class="w-4 h-4"></i>
                </button>
            `;

            // 1. Desktop Table Row
            if (tbody) {
                const tr = document.createElement('tr');
                tr.className = 'hover:bg-slate-50 transition-colors text-xs border-b border-slate-100';
                tr.innerHTML = `
                    <td class="py-3 px-4 font-bold text-slate-900">
                        <button onclick="openOrderDetailModal(${o.id})" class="font-bold text-olive-900 hover:text-terracotta-600 hover:underline flex items-center gap-1 cursor-pointer" title="عرض تفاصيل الطلب والتوقيتات">
                            <span>${o.order_number}</span>
                            <i data-lucide="info" class="w-3 h-3 text-olive-500"></i>
                        </button>
                        ${o.card_message ? `<span class="block text-[10px] text-rose-600 font-medium">💌 كرت إهداء</span>` : ''}
                        ${o.reference_image ? `
                            <button onclick="viewReferenceImageModal('${o.reference_image}', '${o.order_number}')" class="inline-flex items-center gap-1 text-[10px] bg-sky-50 hover:bg-sky-100 text-sky-700 border border-sky-200 px-1.5 py-0.5 rounded font-bold mt-1 transition-all cursor-pointer">
                                <i data-lucide="image" class="w-3 h-3 text-sky-600"></i>
                                <span>صورة ريفرنس 🖼️</span>
                            </button>
                        ` : ''}
                        ${o.completed_image ? `
                            <button onclick="viewReferenceImageModal('${o.completed_image}', '${o.order_number} - صورة العمل المنجز')" class="inline-flex items-center gap-1 text-[10px] bg-purple-100 hover:bg-purple-200 text-purple-900 border border-purple-300 px-1.5 py-0.5 rounded font-bold mt-1 transition-all cursor-pointer">
                                <i data-lucide="camera" class="w-3 h-3 text-purple-700"></i>
                                <span>صورة المنجز 📸</span>
                            </button>
                        ` : ''}
                    </td>
                    <td class="py-3 px-4">
                        <strong class="text-slate-800 text-xs block">${o.customer_name}</strong>
                        <span class="text-slate-500 font-mono text-[11px]">${o.customer_phone}</span>
                    </td>
                    <td class="py-3 px-4">
                        <strong class="text-slate-800 block">${o.recipient_name || o.customer_name}</strong>
                        ${o.recipient_phone ? `<span class="text-slate-600 font-mono text-[11px] block font-semibold">${o.recipient_phone}</span>` : ''}
                        <p class="text-slate-500 truncate max-w-[180px] text-[11px]">${o.recipient_address || 'استلام من المعرض'}</p>
                        ${o.location_url ? `<a href="${o.location_url}" target="_blank" class="text-[10px] text-blue-600 hover:underline flex items-center gap-0.5 mt-0.5"><i data-lucide="map-pin" class="w-3 h-3"></i> خرائط جوجل</a>` : ''}
                    </td>
                    <td class="py-3 px-4 text-slate-600 max-w-[200px]" title="${itemsSummary}">
                        <span class="block truncate">${itemsSummary}</span>
                        ${o.flower_colors ? `<span class="inline-flex items-center gap-1 text-[10px] bg-rose-50 text-rose-700 border border-rose-200 px-1.5 py-0.5 rounded font-semibold mt-1"><i data-lucide="palette" class="w-3 h-3 text-rose-500"></i> ${o.flower_colors}</span>` : ''}
                    </td>
                    <td class="py-3 px-4">
                        <span class="block font-semibold text-slate-800">${o.delivery_date}</span>
                        <span class="text-[11px] text-slate-500">${o.delivery_time_slot || ''}</span>
                    </td>
                    <td class="py-3 px-4">
                        ${o.florist_name 
                            ? `<span class="inline-flex items-center gap-1 font-semibold text-purple-800 bg-purple-50 px-2.5 py-1 rounded-lg border border-purple-200 text-xs"><i data-lucide="flower" class="w-3.5 h-3.5 text-purple-600"></i> ${o.florist_name}</span>`
                            : `<button onclick="promptAssignFlorist(${o.id})" class="text-[11px] text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 px-2 py-0.5 rounded-md font-bold cursor-pointer">تعيين منسق +</button>`
                        }
                    </td>
                    <td class="py-3 px-4">
                        ${o.driver_name 
                            ? `<span class="inline-flex items-center gap-1 font-semibold text-slate-800"><i data-lucide="truck" class="w-3 h-3 text-brand-600"></i> ${o.driver_name}</span>`
                            : `<button onclick="promptAssignDriver(${o.id})" class="text-[11px] text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200 px-2 py-0.5 rounded-md font-bold cursor-pointer">تعيين مندوب +</button>`
                        }
                    </td>
                    <td class="py-3 px-4">
                        ${currentUser && currentUser.role === 'florist' ? '-' : `
                            <span class="font-black text-slate-900 block">${o.total_amount} ر.س</span>
                            ${o.payment_status === 'paid' 
                                ? `<span class="text-[10px] bg-emerald-100 text-emerald-800 font-bold px-1.5 py-0.5 rounded">مسدد ✅</span>` 
                                : `<span class="text-[10px] bg-amber-100 text-amber-800 font-bold px-1.5 py-0.5 rounded">غير مسدد ⚠️</span>`}
                        `}
                    </td>
                    <td class="py-3 px-4">
                        ${renderStatusBadge(o.status)}
                        ${o.acceptance_status === 'auto_forwarded' ? `<span class="block text-[9px] text-amber-700 bg-amber-50 px-1 py-0.5 rounded border border-amber-200 mt-1">🔄 محول تلقائياً</span>` : ''}
                        ${o.approval_status === 'approved' ? `<span class="block text-[9px] text-emerald-700 bg-emerald-50 px-1 py-0.5 rounded border border-emerald-200 mt-1">👑 معتمد من الإدارة</span>` : ''}
                    </td>
                    <td class="py-3 px-4 text-center">
                        <div class="flex items-center justify-center gap-1 flex-wrap">
                            ${actionsHtml}
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            }

            // 2. Mobile Responsive Card (100% Fit, Touch-Friendly, No Horizontal Scroll)
            if (mobileContainer) {
                const card = document.createElement('div');
                card.className = 'mobile-card bg-cream-50/60 p-3.5 rounded-2xl border border-cream-200 shadow-xs space-y-2.5 text-xs';
                card.innerHTML = `
                    <div class="flex items-center justify-between border-b border-cream-200/70 pb-2">
                        <div class="flex items-center gap-2">
                            <button onclick="openOrderDetailModal(${o.id})" class="font-black text-sm text-olive-900 hover:text-terracotta-600 flex items-center gap-1 cursor-pointer">
                                <span>${o.order_number}</span>
                                <i data-lucide="info" class="w-3.5 h-3.5 text-olive-500"></i>
                            </button>
                            ${o.card_message ? `<span class="text-[10px] bg-rose-50 text-rose-700 px-1.5 py-0.5 rounded font-bold border border-rose-200">💌 كرت</span>` : ''}
                        </div>
                        <div>${renderStatusBadge(o.status)}</div>
                    </div>

                    <div class="grid grid-cols-2 gap-2">
                        <div class="bg-white p-2 rounded-xl border border-cream-200/60">
                            <span class="text-[10px] text-olive-700 font-bold block">👤 العميل:</span>
                            <strong class="text-slate-800 text-xs block truncate">${o.customer_name}</strong>
                            <a href="tel:${o.customer_phone}" class="text-[11px] text-olive-800 font-mono mt-0.5 block">${o.customer_phone}</a>
                        </div>
                        <div class="bg-white p-2 rounded-xl border border-cream-200/60">
                            <span class="text-[10px] text-olive-700 font-bold block">📍 المستلم:</span>
                            <strong class="text-slate-800 text-xs block truncate">${o.recipient_name || o.customer_name}</strong>
                            ${o.recipient_phone ? `<a href="tel:${o.recipient_phone}" class="text-[11px] text-olive-800 font-mono mt-0.5 block">${o.recipient_phone}</a>` : ''}
                            <span class="text-[10px] text-slate-500 block truncate">${o.recipient_address || 'استلام من المعرض'}</span>
                        </div>
                    </div>

                    <div class="bg-white p-2.5 rounded-xl border border-cream-200/60">
                        <div class="flex items-start justify-between gap-2">
                            <div class="min-w-0 flex-1">
                                <span class="text-[10px] font-bold text-olive-700 block">💐 الورد والطلب:</span>
                                <p class="text-slate-700 font-medium text-xs mt-0.5 leading-snug">${itemsSummary}</p>
                            </div>
                            ${o.reference_image ? `
                                <button onclick="viewReferenceImageModal('${o.reference_image}', '${o.order_number}')" class="shrink-0 flex items-center gap-1 text-[10px] bg-sky-50 text-sky-700 border border-sky-200 px-2 py-1 rounded-lg font-bold cursor-pointer">
                                    <i data-lucide="image" class="w-3 h-3"></i>
                                    <span>ريفرنس</span>
                                </button>
                            ` : ''}
                            ${o.completed_image ? `
                                <button onclick="viewReferenceImageModal('${o.completed_image}', '${o.order_number} - صورة العمل المنجز')" class="shrink-0 flex items-center gap-1 text-[10px] bg-purple-100 text-purple-900 border border-purple-300 px-2 py-1 rounded-lg font-bold cursor-pointer">
                                    <i data-lucide="camera" class="w-3 h-3 text-purple-700"></i>
                                    <span>المنجز 📸</span>
                                </button>
                            ` : ''}
                        </div>
                        ${o.flower_colors ? `
                            <div class="mt-1.5 flex items-center gap-1 text-[11px] text-rose-800 font-bold bg-rose-50 border border-rose-200/80 px-2 py-0.5 rounded-lg">
                                <i data-lucide="palette" class="w-3 h-3 text-rose-500"></i>
                                <span>الألوان: ${o.flower_colors}</span>
                            </div>
                        ` : ''}
                    </div>

                    <div class="flex items-center justify-between pt-1 border-t border-cream-200/70">
                        <div>
                            <span class="text-[10px] text-slate-400 block">موعد التسليم:</span>
                            <span class="font-bold text-slate-800 text-xs">${o.delivery_date} <span class="text-[10px] font-normal text-slate-500">(${o.delivery_time_slot || 'اليوم'})</span></span>
                        </div>
                        ${(!currentUser || currentUser.role !== 'florist') ? `
                            <div class="text-left">
                                <span class="text-[10px] text-slate-400 block">الإجمالي:</span>
                                <span class="font-black text-sm text-olive-900">${o.total_amount} ر.س</span>
                                ${o.payment_status === 'paid' ? '<span class="text-[9px] text-emerald-700 font-bold">مسدد ✅</span>' : '<span class="text-[9px] text-amber-700 font-bold">غير مسدد ⚠️</span>'}
                            </div>
                        ` : ''}
                    </div>

                    <div class="flex flex-wrap items-center gap-1.5 pt-1">
                        ${o.florist_name ? `<span class="text-[11px] bg-purple-50 text-purple-800 px-2 py-0.5 rounded-lg border border-purple-200 font-semibold flex items-center gap-1"><i data-lucide="flower" class="w-3 h-3 text-purple-600"></i> ${o.florist_name}</span>` : `<button onclick="promptAssignFlorist(${o.id})" class="text-[10px] text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded font-bold cursor-pointer">تعيين منسق +</button>`}
                        ${o.driver_name ? `<span class="text-[11px] bg-slate-100 text-slate-800 px-2 py-0.5 rounded-lg border border-slate-200 font-semibold flex items-center gap-1"><i data-lucide="truck" class="w-3 h-3 text-brand-600"></i> ${o.driver_name}</span>` : `<button onclick="promptAssignDriver(${o.id})" class="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded font-bold cursor-pointer">تعيين مندوب +</button>`}
                        ${o.acceptance_status === 'auto_forwarded' ? `<span class="text-[9px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">🔄 محول تلقائياً</span>` : ''}
                        ${o.approval_status === 'approved' ? `<span class="text-[9px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">👑 معتمد</span>` : ''}
                    </div>

                    <div class="pt-2 border-t border-cream-200/70 flex flex-wrap items-center justify-between gap-1.5">
                        <div class="flex items-center gap-1 flex-wrap">
                            ${actionsHtml}
                        </div>
                    </div>
                `;
                mobileContainer.appendChild(card);
            }
        });

        initIcons();
    } catch (err) {
        console.error("Load orders error:", err);
    }
}

function setOrderFilter(status) {
    activeOrderFilter = status;
    document.querySelectorAll('.order-filter-btn').forEach(btn => {
        if (btn.getAttribute('data-status') === status) {
            btn.className = 'order-filter-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-olive-700 text-cream-50';
        } else {
            btn.className = 'order-filter-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-cream-100 text-olive-800 hover:bg-cream-200';
        }
    });
    loadOrders();
}

function filterOrdersByStatus(status) {
    switchTab('orders');
    setOrderFilter(status);
}

let searchTimer = null;
function debounceOrdersSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
        loadOrders();
    }, 300);
}

function renderStatusBadge(status) {
    const map = {
        'new': '<span class="badge-status bg-amber-100 text-amber-800">طلب جديد 🟡</span>',
        'preparing': '<span class="badge-status bg-blue-100 text-blue-800">قيد التنسيق 🌿</span>',
        'ready': '<span class="badge-status bg-purple-100 text-purple-800">جاهز للتسليم 🌸</span>',
        'out_for_delivery': '<span class="badge-status bg-indigo-100 text-indigo-800">مع المندوب 🚗</span>',
        'delivered': '<span class="badge-status bg-emerald-100 text-emerald-800">تم التوصيل 💐</span>',
        'cancelled': '<span class="badge-status bg-rose-100 text-rose-800">ملغي ❌</span>',
    };
    return map[status] || `<span class="badge-status bg-slate-100 text-slate-700">${status}</span>`;
}

function getNextStatusLabel(curr) {
    const next = {
        'new': 'بدء التنسيق 🌿',
        'preparing': 'جاهز للتسليم 🌸',
        'ready': 'إسناد للمندوب 🚗',
        'out_for_delivery': 'تأكيد التوصيل 💐',
        'delivered': 'مكتمل ✅',
        'cancelled': 'إعادة تنشيط'
    };
    return next[curr] || 'تحديث';
}

async function advanceOrderStatus(orderId, currentStatus) {
    const progression = {
        'new': 'preparing',
        'preparing': 'ready',
        'ready': 'out_for_delivery',
        'out_for_delivery': 'delivered'
    };

    const nextStatus = progression[currentStatus];
    if (!nextStatus) {
        alert("هذا الطلب وصل لنهاية مراحله بالفعل");
        return;
    }

    try {
        const res = await fetch(`/api/orders/${orderId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: nextStatus })
        });
        const data = await res.json();
        if (data.success) {
            loadDashboardData();
            loadOrders();
        }
    } catch (err) {
        console.error("Status update error:", err);
    }
}

// ========================================================
// WORKFLOW HANDLERS (ACCEPT, REJECT/FORWARD, PHOTO, APPROVE)
// ========================================================

async function acceptOrderByFlorist(orderId) {
    if (!confirm("هل تؤكد قبول هذا الطلب وبدء العمل على تنسيقه الآن 🌿؟")) return;
    try {
        const res = await fetch(`/api/orders/${orderId}/accept`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                florist_id: currentUser.id,
                florist_name: currentUser.name
            })
        });
        const data = await res.json();
        if (data.success) {
            alert("🌸 تم قبول الطلب وبدأ التنسيق! بالتوفيق يا فنان.");
            loadOrders();
            loadDashboardData();
        } else {
            alert(data.detail || "حدث خطأ أثناء قبول الطلب");
        }
    } catch (e) {
        console.error(e);
    }
}

async function rejectOrderByFlorist(orderId) {
    const reason = prompt("يرجى ذكر سبب الاعتذار عن استلام الطلب ليتم تحويله للزميل البديل وإشعار إدارة نبت (ياسر / فيصل / نادر):", "المنسق مشغول بطلبات حالية");
    if (!reason) return;

    try {
        const res = await fetch(`/api/orders/${orderId}/reject`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                florist_id: currentUser.id,
                florist_name: currentUser.name,
                reason: reason
            })
        });
        const data = await res.json();
        if (data.success) {
            alert(`🚨 تم الاعتذار عن الطلب.\n${data.message}`);
            loadOrders();
            loadDashboardData();
        } else {
            alert(data.detail || "حدث خطأ أثناء معالجة الطلب");
        }
    } catch (e) {
        console.error(e);
    }
}

function openFloristCompleteWorkModal(orderId, orderNum) {
    document.getElementById('complete-modal-order-id').value = orderId;
    document.getElementById('complete-modal-order-num').textContent = orderNum || `#${orderId}`;
    const fileInput = document.getElementById('complete-file-input');
    if (fileInput) fileInput.value = '';
    const urlInput = document.getElementById('complete-image-url');
    if (urlInput) urlInput.value = '';
    
    const previewBox = document.getElementById('complete-preview-box');
    if (previewBox) previewBox.classList.add('hidden');
    const previewImg = document.getElementById('complete-preview-img');
    if (previewImg) previewImg.src = '';
    
    const statusBox = document.getElementById('complete-upload-status');
    if (statusBox) {
        statusBox.className = 'hidden';
        statusBox.textContent = '';
    }

    const submitBtn = document.getElementById('complete-submit-btn');
    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<i data-lucide="check-circle" class="w-4 h-4"></i><span>إرسال الصورة للتعميد</span>`;
    }

    openModal('modal-florist-complete-work');
}

function compressImageFile(file, maxWidth = 1280, quality = 0.85) {
    return new Promise((resolve) => {
        if (!file || !file.type || !file.type.startsWith('image/')) {
            resolve(file);
            return;
        }

        const img = new Image();
        const reader = new FileReader();

        reader.onload = function(e) {
            img.onload = function() {
                let width = img.width;
                let height = img.height;

                if (width > maxWidth || height > maxWidth) {
                    if (width > height) {
                        height = Math.round((height * maxWidth) / width);
                        width = maxWidth;
                    } else {
                        width = Math.round((width * maxWidth) / height);
                        height = maxWidth;
                    }
                }

                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);

                canvas.toBlob((blob) => {
                    if (blob) {
                        const compressedFile = new File([blob], file.name.replace(/\.[^/.]+$/, ".jpg"), {
                            type: 'image/jpeg',
                            lastModified: Date.now()
                        });
                        resolve(compressedFile);
                    } else {
                        resolve(file);
                    }
                }, 'image/jpeg', quality);
            };
            img.onerror = () => resolve(file);
            img.src = e.target.result;
        };
        reader.onerror = () => resolve(file);
        reader.readAsDataURL(file);
    });
}

let activeCompletedPhotoUploadPromise = null;

async function previewCompletedPhoto(event) {
    const file = event.target.files ? event.target.files[0] : null;
    if (!file) return;

    const previewImg = document.getElementById('complete-preview-img');
    const previewBox = document.getElementById('complete-preview-box');
    const statusBox = document.getElementById('complete-upload-status');
    const submitBtn = document.getElementById('complete-submit-btn');

    if (previewImg) {
        try {
            previewImg.src = URL.createObjectURL(file);
            if (previewBox) previewBox.classList.remove('hidden');
        } catch (e) {
            console.error(e);
        }
    }

    if (statusBox) {
        statusBox.className = 'text-xs p-2.5 rounded-xl border bg-amber-50 text-amber-900 border-amber-200 font-bold flex items-center gap-2';
        statusBox.innerHTML = `<span class="inline-block w-3.5 h-3.5 border-2 border-amber-600 border-t-transparent rounded-full animate-spin"></span> جاري ضغط ورفع الصورة للسيرفر...`;
    }
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="inline-block w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span> <span>جاري الرفع...</span>`;
    }

    activeCompletedPhotoUploadPromise = (async () => {
        try {
            const compressed = await compressImageFile(file);
            const formData = new FormData();
            formData.append('file', compressed);

            const res = await fetch('/api/orders/upload-completed', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();

            if (res.ok && data.success && data.image_url) {
                document.getElementById('complete-image-url').value = data.image_url;
                if (statusBox) {
                    statusBox.className = 'text-xs p-2.5 rounded-xl border bg-emerald-50 text-emerald-800 border-emerald-200 font-bold flex items-center gap-2';
                    statusBox.innerHTML = `✓ تم رفع الصورة بنجاح على السيستم (${data.filename}) 🌸`;
                }
                return data.image_url;
            } else {
                throw new Error(data.detail || "تعذر الرفع");
            }
        } catch (err) {
            console.error("Upload error, using fallback preview:", err);
            const reader = new FileReader();
            return new Promise((resolve) => {
                reader.onload = (e) => {
                    document.getElementById('complete-image-url').value = e.target.result;
                    if (statusBox) {
                        statusBox.className = 'text-xs p-2.5 rounded-xl border bg-purple-50 text-purple-900 border-purple-200 font-bold';
                        statusBox.textContent = `جاهزة للإرسال والتعميد ✅`;
                    }
                    resolve(e.target.result);
                };
                reader.readAsDataURL(file);
            });
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<i data-lucide="check-circle" class="w-4 h-4"></i><span>إرسال الصورة للتعميد</span>`;
                initIcons();
            }
        }
    })();
}

async function handleFloristSubmitCompletedWork(event) {
    event.preventDefault();
    const orderId = document.getElementById('complete-modal-order-id').value;
    const submitBtn = document.getElementById('complete-submit-btn');

    if (activeCompletedPhotoUploadPromise) {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<span class="inline-block w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span> <span>جاري إكمال الرفع...</span>`;
        }
        await activeCompletedPhotoUploadPromise;
    }

    const fileInput = document.getElementById('complete-file-input');
    let imageUrl = document.getElementById('complete-image-url')?.value;

    // Fallback: if imageUrl is still empty but file is chosen, upload now
    if (!imageUrl && fileInput && fileInput.files && fileInput.files[0]) {
        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = `<span class="inline-block w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span> <span>جاري الرفع الآن...</span>`;
            }
            const compressed = await compressImageFile(fileInput.files[0]);
            const formData = new FormData();
            formData.append('file', compressed);
            const res = await fetch('/api/orders/upload-completed', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.success && data.image_url) {
                imageUrl = data.image_url;
                document.getElementById('complete-image-url').value = imageUrl;
            }
        } catch (e) {
            console.error("Direct upload attempt error:", e);
        }
    }

    if (!imageUrl) {
        imageUrl = document.getElementById('complete-preview-img')?.src;
    }

    if (!imageUrl || imageUrl.length < 5) {
        alert("يرجى اختيار صورة الورد المنجز أولاً");
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i data-lucide="check-circle" class="w-4 h-4"></i><span>إرسال الصورة للتعميد</span>`;
            initIcons();
        }
        return;
    }

    try {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<span class="inline-block w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span> <span>جاري الحفظ في السيستم...</span>`;
        }

        const res = await fetch(`/api/orders/${orderId}/complete-work`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                completed_image: imageUrl,
                florist_id: currentUser ? currentUser.id : null,
                florist_name: currentUser ? (currentUser.name || currentUser.username) : "المنسق"
            })
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-florist-complete-work');
            closeModal('modal-order-detail');
            alert("📸 تم رفع صورة الورد وحفظها بنجاح في السيستم!\nتم إرسال إشعار للمسؤولين (ياسر، فيصل، نادر) لاعتماد وتعَميد الطلب ✨");
            loadOrders();
            loadDashboardData();
        } else {
            alert(data.detail || "تعذر حفظ الإجراء");
        }
    } catch (e) {
        console.error(e);
        alert("حدث خطأ أثناء الاتصال بالخادم لحفظ صورة العمل المنجز");
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i data-lucide="check-circle" class="w-4 h-4"></i><span>إرسال الصورة للتعميد</span>`;
            initIcons();
        }
    }
}

async function openManagerApprovalModal(orderId) {
    try {
        const res = await fetch(`/api/orders/${orderId}`);
        const ord = await res.json();

        document.getElementById('approval-modal-order-id').value = ord.id;
        document.getElementById('approval-modal-order-num').textContent = `#${ord.order_number}`;
        document.getElementById('approval-florist-name').textContent = ord.florist_name || 'غير محدد';
        document.getElementById('approval-flower-colors').textContent = ord.flower_colors || 'طبيعي مختلط';
        document.getElementById('approval-notes-input').value = '';

        // Completed image
        document.getElementById('approval-completed-img').src = ord.completed_image || '';

        // Reference image
        const refContainer = document.getElementById('approval-ref-container');
        const noRefMsg = document.getElementById('approval-no-ref-msg');
        if (ord.reference_image) {
            document.getElementById('approval-reference-img').src = ord.reference_image;
            refContainer.classList.remove('hidden');
            noRefMsg.classList.add('hidden');
        } else {
            refContainer.classList.add('hidden');
            noRefMsg.classList.remove('hidden');
        }

        openModal('modal-manager-approval');
    } catch (e) {
        console.error("Open manager approval error:", e);
    }
}

async function submitOrderApprovalDecision(action) {
    const orderId = document.getElementById('approval-modal-order-id').value;
    const notes = document.getElementById('approval-notes-input').value;
    const approverName = currentUser.name || "ياسر (المدير العام)";

    if (action === 'request_revision' && !notes.trim()) {
        alert("يرجى كتابة ملاحظات التعديل للمنسق");
        return;
    }

    try {
        const res = await fetch(`/api/orders/${orderId}/approve`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                approved_by: approverName,
                action: action,
                notes: notes
            })
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-manager-approval');
            if (action === 'approve') {
                alert(`👑 تم تعميد الورد بنجاح بواسطة (${approverName})!\nحالة الطلب الآن: جاهز للتسليم (Ready) 🌸\nيمكنك الآن إسناد الطلب للمندوب.`);
            } else {
                alert(`⚠️ تم إرسال طلب التعديل للمنسق.`);
            }
            loadOrders();
            loadDashboardData();
        } else {
            alert(data.detail || "تعذر تنفيذ القرار");
        }
    } catch (e) {
        console.error(e);
    }
}

// Store Pickup vs Delivery Mode Handler
function setOrderDeliveryMode(mode) {
    const btnPickup = document.getElementById('btn-delivery-mode-pickup');
    const btnDelivery = document.getElementById('btn-delivery-mode-delivery');
    const addrInput = document.getElementById('order-rec-address');
    const locInput = document.getElementById('order-rec-location');
    const feeInput = document.getElementById('order-delivery-fee');
    const driverSelect = document.getElementById('order-driver-select');

    if (mode === 'pickup') {
        if (btnPickup) {
            btnPickup.className = 'px-3.5 py-1.5 rounded-xl text-xs font-bold border transition-all flex items-center gap-1.5 cursor-pointer bg-amber-600 text-white border-amber-700 shadow-sm';
        }
        if (btnDelivery) {
            btnDelivery.className = 'px-3.5 py-1.5 rounded-xl text-xs font-bold border transition-all flex items-center gap-1.5 cursor-pointer bg-white text-slate-700 hover:bg-cream-50 border-slate-200';
        }
        if (addrInput) {
            addrInput.value = 'استلام من المحل (معرض نبت للورد)';
        }
        if (locInput) {
            locInput.value = '';
            locInput.placeholder = 'استلام مباشر من المعرض 🏪';
        }
        if (feeInput) {
            feeInput.value = '0';
            calculateOrderModalTotals();
        }
        if (driverSelect) {
            driverSelect.value = '';
        }
    } else {
        if (btnPickup) {
            btnPickup.className = 'px-3.5 py-1.5 rounded-xl text-xs font-bold border transition-all flex items-center gap-1.5 cursor-pointer bg-white text-slate-700 hover:bg-amber-50 border-slate-200';
        }
        if (btnDelivery) {
            btnDelivery.className = 'px-3.5 py-1.5 rounded-xl text-xs font-bold border transition-all flex items-center gap-1.5 cursor-pointer bg-olive-700 text-white border-olive-800 shadow-sm';
        }
        if (addrInput && addrInput.value.includes('استلام من المحل')) {
            addrInput.value = '';
            addrInput.placeholder = 'مثال: الرياض - حي الملقا - شارع وادي حنيفة - فيلا 12';
        }
        if (locInput) {
            locInput.placeholder = 'https://maps.google.com/?q=...';
        }
        if (feeInput && (feeInput.value === '0' || feeInput.value === '')) {
            feeInput.value = '35';
            calculateOrderModalTotals();
        }
    }
}

// 3. NEW ORDER MODAL & CREATION
async function openNewOrderModal() {
    const today = getLocalDateString();
    document.getElementById('order-delivery-date').value = today;
    setOrderDeliveryMode('delivery');

    // Reset items
    const rows = document.getElementById('order-items-rows');
    rows.innerHTML = '';
    addOrderItemRow(); // add first row

    // Populate drivers in select
    const driverSelect = document.getElementById('order-driver-select');
    driverSelect.innerHTML = `<option value="">-- اختياري: تعيين لاحقاً --</option>`;
    allDrivers.forEach(d => {
        driverSelect.innerHTML += `<option value="${d.id}">${d.name} (${d.vehicle})</option>`;
    });

    // Populate available florists present in shop filtered by delivery date
    await refreshOrderModalFlorists();
    const dateInput = document.getElementById('order-delivery-date');
    if (dateInput) {
        dateInput.onchange = refreshOrderModalFlorists;
    }

    calculateOrderModalTotals();
    removeReferenceImage();
    const colorsInput = document.getElementById('order-flower-colors-input');
    if (colorsInput) colorsInput.value = '';

    const feeInput = document.getElementById('order-delivery-fee');
    if (feeInput) feeInput.value = '35';

    const timeSlotInput = document.getElementById('order-time-slot');
    if (timeSlotInput) timeSlotInput.value = '';

    calculateOrderModalTotals();
    openModal('modal-new-order');
}

async function refreshOrderModalFlorists() {
    const floristSelect = document.getElementById('order-florist-select');
    if (!floristSelect) return;
    const dateInput = document.getElementById('order-delivery-date');
    const selectedDate = dateInput ? dateInput.value : '';

    floristSelect.innerHTML = `<option value="">🤖 توجيه تلقائي ذكي (للمنسق المتواجد بالمحل والأقل ضغطاً بتاريخ التسليم - موصى به)</option>`;
    try {
        const res = await fetch(`/api/employees/available-florists${selectedDate ? '?delivery_date=' + encodeURIComponent(selectedDate) : ''}`);
        const florists = await res.json();
        florists.forEach(f => {
            if (f.is_available_on_date) {
                floristSelect.innerHTML += `<option value="${f.id}">🌿 ${f.name} (${f.specialty || 'منسق'} - طلبات جارية: ${f.current_workload}) [متاح للعمل ✅]</option>`;
            } else {
                floristSelect.innerHTML += `<option value="${f.id}" disabled class="bg-slate-100 text-slate-400">⏸️ ${f.name} (غير متاح: ${f.unavailability_reason}) [مستبعد ❌]</option>`;
            }
        });
    } catch (e) {
        console.error("Failed to load available florists:", e);
    }
}

function toggleColorBadge(colorName) {
    const input = document.getElementById('order-flower-colors-input');
    if (!input) return;
    let val = input.value.trim();
    if (!val) {
        input.value = colorName;
    } else {
        if (val.includes(colorName)) {
            val = val.replace(` + ${colorName}`, '').replace(`${colorName} + `, '').replace(colorName, '').trim();
            input.value = val;
        } else {
            input.value = `${val} + ${colorName}`;
        }
    }
}

async function handleReferenceImageUpload(event) {
    const rawFile = event.target.files[0];
    if (!rawFile) return;

    // Show immediate local preview
    const previewImg = document.getElementById('order-ref-preview-img');
    const previewContainer = document.getElementById('order-ref-preview-container');
    if (previewImg) previewImg.src = URL.createObjectURL(rawFile);
    if (previewContainer) previewContainer.classList.remove('hidden');

    try {
        // Compress high-res mobile photo to lightweight JPEG (~200KB)
        const file = await compressImageFile(rawFile, 1280, 0.82);

        // Upload to server endpoint
        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch('/api/orders/upload-reference', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('order-ref-image-url').value = data.image_url;
        }
    } catch (err) {
        console.error("Upload reference photo error:", err);
    }
}

function removeReferenceImage() {
    const fileInput = document.getElementById('order-ref-image-file');
    if (fileInput) fileInput.value = '';
    const urlInput = document.getElementById('order-ref-image-url');
    if (urlInput) urlInput.value = '';
    const previewImg = document.getElementById('order-ref-preview-img');
    if (previewImg) previewImg.src = '';
    const container = document.getElementById('order-ref-preview-container');
    if (container) container.classList.add('hidden');
}

function viewReferenceImageModal(imgUrl, orderNum) {
    if (!imgUrl) return;
    const numEl = document.getElementById('ref-modal-order-number');
    if (numEl) numEl.textContent = orderNum || '';
    const imgEl = document.getElementById('ref-modal-img');
    if (imgEl) imgEl.src = imgUrl;
    const linkEl = document.getElementById('ref-modal-open-link');
    if (linkEl) linkEl.href = imgUrl;
    openModal('modal-view-reference-image');
}

function formatAppDateTime(isoString) {
    if (!isoString) return null;
    try {
        const d = new Date(isoString.replace(' ', 'T'));
        if (isNaN(d.getTime())) return isoString;
        return d.toLocaleString('ar-SA', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    } catch (e) {
        return isoString;
    }
}

function calculateDurationText(startIso, endIso) {
    if (!startIso || !endIso) return null;
    try {
        const s = new Date(startIso.replace(' ', 'T')).getTime();
        const e = new Date(endIso.replace(' ', 'T')).getTime();
        if (isNaN(s) || isNaN(e) || e < s) return null;
        const diffMs = e - s;
        const diffMinutes = Math.floor(diffMs / 60000);
        if (diffMinutes < 60) {
            return `${diffMinutes} دقيقة`;
        }
        const hours = Math.floor(diffMinutes / 60);
        const mins = diffMinutes % 60;
        return `${hours} ساعة و ${mins} دقيقة`;
    } catch (e) {
        return null;
    }
}

async function openOrderDetailModal(orderId) {
    try {
        const res = await fetch(`/api/orders/${orderId}`);
        if (!res.ok) {
            alert("تعذر جلب تفاصيل الطلب");
            return;
        }
        const ord = await res.json();

        // 1. Header info
        document.getElementById('detail-order-number-badge').textContent = `#${ord.order_number}`;

        // 2. Timeline timestamps
        const receivedFormatted = formatAppDateTime(ord.received_at || ord.created_at);
        document.getElementById('detail-time-received').textContent = receivedFormatted || 'غير محدد';

        const prepStartFormatted = formatAppDateTime(ord.preparing_started_at);
        const prepEl = document.getElementById('detail-time-preparing');
        if (prepStartFormatted) {
            prepEl.textContent = prepStartFormatted;
            prepEl.className = 'mt-1 font-mono text-xs font-bold text-blue-900 bg-blue-100 px-2 py-1 rounded-md border border-blue-300';
        } else {
            prepEl.textContent = '⏳ بانتظار استلام المنسق';
            prepEl.className = 'mt-1 font-mono text-xs font-bold text-slate-500 bg-slate-100 px-2 py-1 rounded-md border border-slate-200';
        }

        const preparedFormatted = formatAppDateTime(ord.prepared_at);
        const readyEl = document.getElementById('detail-time-prepared');
        if (preparedFormatted) {
            readyEl.textContent = preparedFormatted;
            readyEl.className = 'mt-1 font-mono text-xs font-bold text-purple-900 bg-purple-100 px-2 py-1 rounded-md border border-purple-300';
        } else if (ord.status === 'preparing') {
            readyEl.textContent = '🌿 جاري التنسيق حالياً';
            readyEl.className = 'mt-1 font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-1 rounded-md border border-blue-200 animate-pulse';
        } else {
            readyEl.textContent = 'لم ينته بعد';
            readyEl.className = 'mt-1 font-mono text-xs font-bold text-slate-500 bg-slate-100 px-2 py-1 rounded-md border border-slate-200';
        }

        const deliveredFormatted = formatAppDateTime(ord.delivered_at);
        const delivEl = document.getElementById('detail-time-delivered');
        if (deliveredFormatted) {
            delivEl.textContent = deliveredFormatted;
            delivEl.className = 'mt-1 font-mono text-xs font-bold text-emerald-900 bg-emerald-100 px-2 py-1 rounded-md border border-emerald-300';
        } else {
            delivEl.textContent = ord.status === 'out_for_delivery' ? '🚗 مع المندوب بالطريق' : 'لم يسلّم بعد';
            delivEl.className = 'mt-1 font-mono text-xs font-bold text-slate-500 bg-slate-100 px-2 py-1 rounded-md border border-slate-200';
        }

        // Preparation duration calculation
        const durationBox = document.getElementById('detail-duration-box');
        const durationText = document.getElementById('detail-duration-text');
        if (ord.preparing_started_at && ord.prepared_at) {
            const dur = calculateDurationText(ord.preparing_started_at, ord.prepared_at);
            if (dur) {
                durationText.textContent = dur;
                durationBox.classList.remove('hidden');
            } else {
                durationBox.classList.add('hidden');
            }
        } else if (ord.preparing_started_at && !ord.prepared_at) {
            const durLive = calculateDurationText(ord.preparing_started_at, new Date().toISOString());
            if (durLive) {
                durationText.textContent = `${durLive} (مستمر حالياً)`;
                durationBox.classList.remove('hidden');
            } else {
                durationBox.classList.add('hidden');
            }
        } else {
            durationBox.classList.add('hidden');
        }

        // 3. Customer & logistics
        document.getElementById('detail-cust-name').textContent = ord.customer_name || '-';
        document.getElementById('detail-cust-phone').textContent = ord.customer_phone || '-';
        document.getElementById('detail-rec-name').textContent = ord.recipient_name || ord.customer_name || '-';
        document.getElementById('detail-rec-phone').textContent = ord.recipient_phone || ord.customer_phone || '-';
        document.getElementById('detail-rec-address').textContent = ord.recipient_address || 'استلام بالمعرض';
        document.getElementById('detail-delivery-slot').textContent = `${ord.delivery_date} (${ord.delivery_time_slot || 'غير محدد'})`;

        document.getElementById('detail-florist-name').textContent = ord.florist_name || 'لم يتم الإسناد بعد';
        document.getElementById('detail-driver-name').textContent = ord.driver_name || 'لم يتم التعيين بعد';
        document.getElementById('detail-status-badge').innerHTML = renderStatusBadge(ord.status);
        document.getElementById('detail-flower-colors').textContent = ord.flower_colors || 'حسب التنسيق العام للورد';

        // 4. Items table
        const itemsTbody = document.getElementById('detail-items-tbody');
        itemsTbody.innerHTML = '';
        if (ord.items && ord.items.length > 0) {
            ord.items.forEach(it => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="py-2.5 px-3 font-bold text-slate-800">${it.product_name}</td>
                    <td class="py-2.5 px-3 text-center font-bold text-slate-700">${it.quantity}</td>
                    <td class="py-2.5 px-3 font-mono">${it.unit_price.toFixed(2)} ر.س</td>
                    <td class="py-2.5 px-3 text-left font-black text-slate-900 font-mono">${it.total_price.toFixed(2)} ر.س</td>
                `;
                itemsTbody.appendChild(tr);
            });
        } else {
            itemsTbody.innerHTML = `<tr><td colspan="4" class="text-center py-4 text-slate-400">لا توجد بنود مسجلة</td></tr>`;
        }

        // 5. Card message & reference
        const cardBox = document.getElementById('detail-card-box');
        const cardMsg = document.getElementById('detail-card-message');
        if (ord.card_message) {
            cardMsg.textContent = `« ${ord.card_message} »`;
            cardBox.classList.remove('hidden');
        } else {
            cardMsg.textContent = '« لا يوجد كرت إهداء »';
        }

        const refBox = document.getElementById('detail-ref-box');
        const refBtn = document.getElementById('detail-ref-btn');
        if (ord.reference_image) {
            refBox.classList.remove('hidden');
            refBtn.onclick = () => viewReferenceImageModal(ord.reference_image, ord.order_number);
        } else {
            refBox.classList.add('hidden');
        }

        const compBox = document.getElementById('detail-completed-photo-box');
        const compBtn = document.getElementById('detail-completed-btn');
        const compUploadBtn = document.getElementById('detail-upload-completed-btn');
        const compStatusBadge = document.getElementById('detail-approval-status-badge');
        if (compBox) {
            compBox.classList.remove('hidden');
            if (ord.completed_image) {
                if (compBtn) {
                    compBtn.classList.remove('hidden');
                    compBtn.onclick = () => viewReferenceImageModal(ord.completed_image, `${ord.order_number} - صورة الورد المنجز`);
                }
                if (compUploadBtn) {
                    compUploadBtn.textContent = 'تغيير الصورة 📸';
                    compUploadBtn.onclick = () => openFloristCompleteWorkModal(ord.id, ord.order_number);
                }
                if (compStatusBadge) {
                    if (ord.approval_status === 'approved') {
                        compStatusBadge.textContent = `معتمد من (${ord.approved_by || 'الإدارة'}) ✅`;
                        compStatusBadge.className = 'text-[10px] text-emerald-700 font-bold';
                    } else if (ord.approval_status === 'revision_requested') {
                        compStatusBadge.textContent = 'مطلوب تعديل ⚠️';
                        compStatusBadge.className = 'text-[10px] text-rose-700 font-bold';
                    } else {
                        compStatusBadge.textContent = 'بانتظار التعميد ⏳';
                        compStatusBadge.className = 'text-[10px] text-amber-700 font-bold';
                    }
                }
            } else {
                if (compBtn) compBtn.classList.add('hidden');
                if (compUploadBtn) {
                    compUploadBtn.textContent = 'رفع صورة الورد الآن 📸';
                    compUploadBtn.onclick = () => openFloristCompleteWorkModal(ord.id, ord.order_number);
                }
                if (compStatusBadge) {
                    compStatusBadge.textContent = 'لم تُرفع بعد';
                    compStatusBadge.className = 'text-[10px] text-slate-400 font-medium';
                }
            }
        }

        // 6. Financial summary
        document.getElementById('detail-subtotal-val').textContent = `${(ord.subtotal || 0).toFixed(2)} ر.س`;
        document.getElementById('detail-tax-val').textContent = `${(ord.tax || 0).toFixed(2)} ر.س`;
        document.getElementById('detail-total-val').textContent = `${(ord.total_amount || 0).toFixed(2)} ر.س`;

        const payBadge = document.getElementById('detail-payment-badge');
        if (ord.payment_status === 'paid') {
            payBadge.innerHTML = `<span class="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold px-3 py-1 rounded-xl text-xs">مسدد بالكامل ✅</span>`;
        } else {
            payBadge.innerHTML = `<span class="bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold px-3 py-1 rounded-xl text-xs">غير مسدد (آجل) ⚠️</span>`;
        }

        openModal('modal-order-detail');
    } catch (err) {
        console.error("Open order detail error:", err);
    }
}

function addOrderItemRow(defaultName = '', defaultPrice = '', defaultQty = 1) {
    const container = document.getElementById('order-items-rows');
    const rowId = `item-row-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    const div = document.createElement('div');
    div.id = rowId;
    div.className = 'grid grid-cols-12 gap-2 items-center bg-slate-50 p-2.5 rounded-2xl border border-slate-200 transition-all hover:border-brand-300';

    div.innerHTML = `
        <div class="col-span-7">
            <input type="text" value="${defaultName}" oninput="calculateOrderModalTotals()" placeholder="اكتب تفاصيل الورد هنا... مثلاً: ورد جوري أحمر 30 وردة مع تغليف أسود وشريطة بيضاء" class="item-name-input w-full text-xs px-3.5 py-2.5 bg-white border border-slate-200 rounded-xl focus:outline-none focus:border-brand-500 font-medium">
        </div>
        <div class="col-span-2">
            <input type="number" value="${defaultQty}" min="1" oninput="calculateOrderModalTotals()" class="item-qty-input w-full text-xs px-2 py-2.5 bg-white border border-slate-200 rounded-xl text-center font-bold focus:outline-none focus:border-brand-500" placeholder="1">
        </div>
        <div class="col-span-2">
            <input type="number" step="0.01" value="${defaultPrice}" oninput="calculateOrderModalTotals()" class="item-price-input w-full text-xs px-3 py-2.5 bg-white border border-slate-200 rounded-xl text-left font-bold focus:outline-none focus:border-brand-500" placeholder="السعر شامل">
        </div>
        <div class="col-span-1 text-center">
            <button type="button" onclick="removeOrderItemRow('${rowId}')" title="حذف هذا الصنف" class="text-slate-400 hover:text-rose-600 p-2 transition-all cursor-pointer">
                <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>
        </div>
    `;
    container.appendChild(div);
    initIcons();
}

function removeOrderItemRow(rowId) {
    const row = document.getElementById(rowId);
    if (row) {
        row.remove();
        const remaining = document.querySelectorAll('#order-items-rows > div');
        if (remaining.length === 0) {
            addOrderItemRow();
        }
        calculateOrderModalTotals();
    }
}

function quickFillBouquet(name, price) {
    const rows = document.querySelectorAll('#order-items-rows > div');
    let targetRow = null;

    // Check if the last row is empty
    if (rows.length > 0) {
        const lastRow = rows[rows.length - 1];
        const lastInput = lastRow.querySelector('.item-name-input');
        if (lastInput && !lastInput.value.trim()) {
            targetRow = lastRow;
        }
    }

    if (targetRow) {
        targetRow.querySelector('.item-name-input').value = name;
        targetRow.querySelector('.item-price-input').value = price;
        calculateOrderModalTotals();
    } else {
        addOrderItemRow(name, price, 1);
        calculateOrderModalTotals();
    }
}

function calculateOrderModalTotals() {
    let itemsGross = 0;
    const rows = document.querySelectorAll('#order-items-rows > div');
    rows.forEach(r => {
        const qty = parseFloat(r.querySelector('.item-qty-input')?.value || 1);
        const price = parseFloat(r.querySelector('.item-price-input')?.value || 0);
        itemsGross += (qty * price);
    });

    const deliveryFee = parseFloat(document.getElementById('order-delivery-fee')?.value || 0);
    const discount = parseFloat(document.getElementById('order-discount')?.value || 0);

    // Total is tax inclusive
    const totalInclusive = Math.max(0, itemsGross + deliveryFee - discount);
    // Base amount before VAT: Total / 1.15
    const subtotalBeforeTax = totalInclusive / 1.15;
    const taxAmount = totalInclusive - subtotalBeforeTax;

    const subtotalEl = document.getElementById('modal-order-subtotal-preview');
    if (subtotalEl) subtotalEl.textContent = `${subtotalBeforeTax.toFixed(2)} ر.س`;

    const taxEl = document.getElementById('modal-order-tax-preview');
    if (taxEl) taxEl.textContent = `${taxAmount.toFixed(2)} ر.س`;

    const totalEl = document.getElementById('modal-order-total-preview');
    if (totalEl) totalEl.textContent = `${totalInclusive.toFixed(2)} ر.س`;
}

async function handleCreateOrder(event) {
    event.preventDefault();

    const items = [];
    const rows = document.querySelectorAll('#order-items-rows > div');
    rows.forEach(r => {
        const nameInput = r.querySelector('.item-name-input');
        const name = nameInput ? nameInput.value.trim() : '';
        const qty = parseInt(r.querySelector('.item-qty-input')?.value || 1);
        const price = parseFloat(r.querySelector('.item-price-input')?.value || 0);

        if (name && price > 0) {
            items.push({
                product_id: null,
                product_name: name,
                quantity: qty,
                unit_price: price
            });
        }
    });

    if (items.length === 0) {
        alert("يرجى كتابة تفاصيل الورد وتحديد سعرها");
        return;
    }

    const floristVal = document.getElementById('order-florist-select')?.value;

    const payload = {
        customer_name: document.getElementById('order-cust-name').value,
        customer_phone: document.getElementById('order-cust-phone').value,
        recipient_name: document.getElementById('order-rec-name').value || null,
        recipient_phone: document.getElementById('order-rec-phone').value || null,
        recipient_address: document.getElementById('order-rec-address').value || null,
        location_url: document.getElementById('order-rec-location').value || null,
        card_message: document.getElementById('order-card-message').value || null,
        reference_image: document.getElementById('order-ref-image-url')?.value || null,
        flower_colors: document.getElementById('order-flower-colors-input')?.value.trim() || null,
        delivery_date: document.getElementById('order-delivery-date').value,
        delivery_time_slot: document.getElementById('order-time-slot').value,
        driver_id: document.getElementById('order-driver-select').value ? parseInt(document.getElementById('order-driver-select').value) : null,
        florist_id: floristVal ? parseInt(floristVal) : null,
        created_by: "المدير (Admin)",
        delivery_fee: parseFloat(document.getElementById('order-delivery-fee').value || 0),
        discount: parseFloat(document.getElementById('order-discount').value || 0),
        payment_status: document.getElementById('order-payment-status').value,
        payment_method: document.getElementById('order-payment-method').value,
        notes: document.getElementById('order-notes').value || null,
        items: items
    };

    try {
        const res = await fetch('/api/orders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (result.success) {
            closeModal('modal-new-order');
            loadDashboardData();
            loadOrders();
            loadInvoices();
            switchTab('orders');

            let alertMsg = `✓ تم إنشاء الطلب بنجاح برقم: ${result.order_number}`;
            if (result.assigned_florist) {
                alertMsg += `\nتم إرسال مهمة التنسيق للمنسق (${result.assigned_florist.name}) عبر الواتساب بنجاح 🌸`;
            }
            alert(alertMsg);
        } else {
            alert(result.detail || "حدث خطأ أثناء حفظ الطلب");
        }
    } catch (err) {
        console.error("Order creation failed:", err);
    }
}

// 4. WHATSAPP ENGINE & CHAT
async function checkWhatsAppStatus() {
    try {
        const res = await fetch('/api/whatsapp/status');
        const data = await res.json();
        const pill = document.getElementById('wa-connection-pill');
        if (pill) {
            if (data.status === 'connected') {
                pill.className = 'text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full flex items-center gap-1';
                pill.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> متصل (${data.phone})`;
            } else {
                pill.className = 'text-xs bg-amber-500/20 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded-full flex items-center gap-1';
                pill.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span> غير متصل`;
            }
        }
    } catch (err) {
        console.error("WhatsApp status check error:", err);
    }
}

let currentWaPairingCode = "";

function switchWaConnectMethod(method) {
    const codeView = document.getElementById('wa-method-code');
    const qrView = document.getElementById('wa-method-qr');
    const btnCode = document.getElementById('tab-btn-wa-code');
    const btnQr = document.getElementById('tab-btn-wa-qr');

    if (method === 'code') {
        codeView.classList.remove('hidden');
        qrView.classList.add('hidden');
        btnCode.className = 'flex-1 py-2 rounded-xl transition-all bg-white text-brand-700 shadow-sm flex items-center justify-center gap-1.5';
        btnQr.className = 'flex-1 py-2 rounded-xl transition-all text-slate-500 hover:text-slate-700 flex items-center justify-center gap-1.5';
    } else {
        codeView.classList.add('hidden');
        qrView.classList.remove('hidden');
        btnQr.className = 'flex-1 py-2 rounded-xl transition-all bg-white text-brand-700 shadow-sm flex items-center justify-center gap-1.5';
        btnCode.className = 'flex-1 py-2 rounded-xl transition-all text-slate-500 hover:text-slate-700 flex items-center justify-center gap-1.5';
    }
}

async function requestWaPairingCode() {
    const input = document.getElementById('wa-pairing-phone-input');
    const phone = input.value.trim() || "0501234567";
    const display = document.getElementById('wa-generated-code-display');
    
    display.textContent = "جاري التوليد...";
    try {
        const res = await fetch('/api/whatsapp/pairing-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone: phone })
        });
        const data = await res.json();
        if (data.success) {
            currentWaPairingCode = data.pairing_code;
            display.textContent = data.pairing_code;
        } else {
            display.textContent = "خطأ في التوليد";
        }
    } catch (err) {
        console.error("Pairing code error:", err);
        display.textContent = "خطأ بالاتصال";
    }
}

function copyPairingCode() {
    if (!currentWaPairingCode) return;
    navigator.clipboard.writeText(currentWaPairingCode).then(() => {
        alert("تم نسخ كود الاقتران بنجاح: " + currentWaPairingCode);
    }).catch(() => {
        alert("الكود: " + currentWaPairingCode);
    });
}

async function confirmWaCodeConnection() {
    const phone = document.getElementById('wa-pairing-phone-input').value.trim() || "0501234567";
    try {
        await fetch('/api/whatsapp/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone: phone })
        });
        closeModal('modal-whatsapp-qr');
        checkWhatsAppStatus();
        alert("🎉 تم ربط واتساب نبت بنجاح! السيستم جاهز الآن للرد التلقائي وإرسال إشعارات الطلبات.");
    } catch (err) {
        console.error("Connect error:", err);
    }
}

async function openWhatsAppModal() {
    try {
        const res = await fetch('/api/whatsapp/qr');
        const data = await res.json();
        document.getElementById('wa-qr-img').src = data.qr_image;
        openModal('modal-whatsapp-qr');
        switchWaConnectMethod('code');
        // Auto-generate code if empty
        if (!currentWaPairingCode) {
            requestWaPairingCode();
        }
    } catch (err) {
        console.error("Error fetching QR:", err);
    }
}

async function simulateWhatsAppScan() {
    try {
        await fetch('/api/whatsapp/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone: "+966501234567" })
        });
        closeModal('modal-whatsapp-qr');
        checkWhatsAppStatus();
        alert("تم ربط واتساب نبت بنجاح عبر QR! السيستم جاهز الآن للإرسال التلقائي والردود.");
    } catch (err) {
        console.error("Connect error:", err);
    }
}

async function loadWhatsAppConversations() {
    try {
        const res = await fetch('/api/whatsapp/conversations');
        const conversations = await res.json();
        const list = document.getElementById('wa-conversations-list');
        list.innerHTML = '';

        if (conversations.length === 0) {
            list.innerHTML = `<p class="p-4 text-xs text-slate-400 text-center">لا توجد محادثات سابقة</p>`;
            return;
        }

        conversations.forEach((c, idx) => {
            const div = document.createElement('div');
            div.onclick = () => selectWhatsAppConversation(c.phone, c.name);
            div.className = `p-3.5 hover:bg-slate-100 cursor-pointer transition-colors flex items-center gap-3 ${idx === 0 && !currentActiveChatPhone ? 'bg-slate-100' : ''}`;
            div.innerHTML = `
                <div class="w-10 h-10 rounded-full bg-brand-100 text-brand-800 font-bold flex items-center justify-center text-xs flex-shrink-0">
                    ${c.name.charAt(0)}
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex justify-between items-center mb-0.5">
                        <strong class="text-xs text-slate-800 truncate block">${c.name}</strong>
                        <span class="text-[10px] text-slate-400 font-mono">${c.timestamp ? c.timestamp.split(' ')[1] || '' : ''}</span>
                    </div>
                    <p class="text-[11px] text-slate-500 truncate">${c.last_message}</p>
                </div>
            `;
            list.appendChild(div);
        });

        // Auto select first conversation
        if (!currentActiveChatPhone && conversations.length > 0) {
            selectWhatsAppConversation(conversations[0].phone, conversations[0].name);
        }
    } catch (err) {
        console.error("Load conversations error:", err);
    }
}

async function selectWhatsAppConversation(phone, name) {
    currentActiveChatPhone = phone;
    document.getElementById('chat-active-name').textContent = name;
    document.getElementById('chat-active-phone').textContent = phone;
    document.getElementById('chat-active-avatar').textContent = name.charAt(0);

    // Direct wa link
    let cleanPhone = phone.replace(/[^0-9]/g, '');
    if (cleanPhone.startsWith('05')) cleanPhone = '966' + cleanPhone.slice(1);
    document.getElementById('chat-direct-wa-link').href = `https://wa.me/${cleanPhone}`;

    try {
        const res = await fetch(`/api/whatsapp/conversations/${phone}`);
        const messages = await res.json();
        const container = document.getElementById('chat-messages-container');
        container.innerHTML = '';

        messages.forEach(m => {
            const isOutbound = m.direction === 'outbound';
            const msgDiv = document.createElement('div');
            msgDiv.className = `flex ${isOutbound ? 'justify-end' : 'justify-start'}`;
            msgDiv.innerHTML = `
                <div class="max-w-[75%] p-3 rounded-2xl text-xs ${isOutbound ? 'bg-emerald-600 text-white rounded-br-none shadow-sm' : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-sm'}">
                    <p class="whitespace-pre-line">${m.content}</p>
                    <div class="flex justify-end items-center gap-1 mt-1 text-[10px] ${isOutbound ? 'text-emerald-200' : 'text-slate-400'}">
                        <span>${m.created_at ? m.created_at.split(' ')[1] || '' : ''}</span>
                        ${isOutbound ? `<i data-lucide="check-check" class="w-3 h-3 text-emerald-200"></i>` : ''}
                    </div>
                </div>
            `;
            container.appendChild(msgDiv);
        });

        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
        initIcons();
    } catch (err) {
        console.error("Load chat messages error:", err);
    }
}

function insertQuickReply(text) {
    const input = document.getElementById('chat-input-text');
    input.value = text;
    input.focus();
}

async function handleSendChatMessage(event) {
    event.preventDefault();
    const input = document.getElementById('chat-input-text');
    const msg = input.value.trim();
    if (!msg || !currentActiveChatPhone) return;

    try {
        const res = await fetch('/api/whatsapp/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phone: currentActiveChatPhone,
                message: msg,
                customer_name: document.getElementById('chat-active-name').textContent
            })
        });
        const data = await res.json();
        if (data.success) {
            input.value = '';
            selectWhatsAppConversation(currentActiveChatPhone, document.getElementById('chat-active-name').textContent);
            loadWhatsAppConversations();
        }
    } catch (err) {
        console.error("Send message error:", err);
    }
}

function openWhatsAppChatDirect(phone, name, initialMsg = '') {
    switchTab('whatsapp');
    selectWhatsAppConversation(phone, name);
    if (initialMsg) {
        insertQuickReply(initialMsg);
    }
}

// 5. INVOICES & ACCOUNTING
async function loadInvoices() {
    try {
        let url = `/api/invoices?status=${activeInvoiceFilter}`;
        const res = await fetch(url);
        const invoices = await res.json();

        // Calculate sums
        let totalSum = 0;
        let paidSum = 0;
        let unpaidSum = 0;
        invoices.forEach(inv => {
            totalSum += inv.total_amount;
            paidSum += inv.paid_amount;
            unpaidSum += inv.remaining_amount;
        });

        document.getElementById('inv-total-sum').textContent = `${totalSum.toFixed(2)} ر.س`;
        document.getElementById('inv-paid-sum').textContent = `${paidSum.toFixed(2)} ر.س`;
        document.getElementById('inv-unpaid-sum').textContent = `${unpaidSum.toFixed(2)} ر.س`;

        const tbody = document.getElementById('invoices-table-tbody');
        tbody.innerHTML = '';

        if (invoices.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center py-8 text-slate-400 text-xs">لا توجد فواتير مطابقة</td></tr>`;
            return;
        }

        invoices.forEach(inv => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-50 transition-colors text-xs border-b border-slate-100';

            const statusBadge = inv.status === 'paid'
                ? `<span class="badge-status bg-emerald-100 text-emerald-800">مسددة بالكامل ✅</span>`
                : inv.status === 'partial'
                ? `<span class="badge-status bg-blue-100 text-blue-800">مسددة جزئياً ⏳</span>`
                : `<span class="badge-status bg-amber-100 text-amber-800">غير مسددة ⚠️</span>`;

            tr.innerHTML = `
                <td class="py-3 px-4 font-bold font-mono text-slate-900">${inv.invoice_number}</td>
                <td class="py-3 px-4 text-slate-700 font-semibold">${inv.order_number || '-'}</td>
                <td class="py-3 px-4">
                    <strong class="text-slate-800 block">${inv.customer_name}</strong>
                    <span class="text-slate-500 font-mono text-[11px]">${inv.customer_phone || ''}</span>
                </td>
                <td class="py-3 px-4 text-slate-600">${inv.issue_date}</td>
                <td class="py-3 px-4 font-black text-slate-900">${inv.total_amount.toFixed(2)} ر.س</td>
                <td class="py-3 px-4 font-bold text-emerald-700">${inv.paid_amount.toFixed(2)} ر.س</td>
                <td class="py-3 px-4 font-black text-amber-700">${inv.remaining_amount.toFixed(2)} ر.س</td>
                <td class="py-3 px-4">${statusBadge}</td>
                <td class="py-3 px-4 text-center">
                    <div class="flex items-center justify-center gap-1.5">
                        ${inv.remaining_amount > 0 ? `
                            <button onclick="openRecordPaymentModal(${inv.id}, '${inv.invoice_number}', '${inv.customer_name}', ${inv.remaining_amount})" class="text-[11px] bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-2.5 py-1 rounded-lg shadow-sm">
                                قبض دفعة +
                            </button>
                        ` : ''}
                        <button onclick="openInvoicePrintModal(${inv.id})" class="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-700" title="طباعة الفاتورة">
                            <i data-lucide="printer" class="w-3.5 h-3.5"></i>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        initIcons();
    } catch (err) {
        console.error("Load invoices error:", err);
    }
}

function setInvoiceFilter(status) {
    activeInvoiceFilter = status;
    document.querySelectorAll('.inv-filter-btn').forEach(btn => {
        if (btn.getAttribute('data-status') === status) {
            btn.className = 'inv-filter-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-brand-600 text-white';
        } else {
            btn.className = 'inv-filter-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 text-slate-600 hover:bg-slate-200';
        }
    });
    loadInvoices();
}

function openRecordPaymentModal(invoiceId, invNum, custName, remaining) {
    document.getElementById('pay-invoice-id').value = invoiceId;
    document.getElementById('pay-inv-number').textContent = invNum;
    document.getElementById('pay-cust-name').textContent = custName;
    document.getElementById('pay-remaining-amount').textContent = `${remaining.toFixed(2)} ر.س`;
    document.getElementById('pay-amount-input').value = remaining.toFixed(2);
    document.getElementById('pay-amount-input').max = remaining;

    openModal('modal-record-payment');
}

async function handleRecordPaymentSubmit(event) {
    event.preventDefault();
    const invoiceId = parseInt(document.getElementById('pay-invoice-id').value);
    const amount = parseFloat(document.getElementById('pay-amount-input').value);
    const method = document.getElementById('pay-method-select').value;
    const ref = document.getElementById('pay-ref-input').value;

    try {
        const res = await fetch('/api/invoices/pay', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                invoice_id: invoiceId,
                amount: amount,
                payment_method: method,
                reference_number: ref
            })
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-record-payment');
            loadInvoices();
            loadDashboardData();
            alert(`تم تسجيل سند القبض رقم: ${data.payment_number}\nالمبلغ المتبقي: ${data.new_remaining} ر.س\nتم إرسال إشعار السند للعميل على الواتس اب 🌸`);
        }
    } catch (err) {
        console.error("Payment error:", err);
    }
}

async function openInvoicePrintModal(invoiceId) {
    try {
        const res = await fetch(`/api/invoices/${invoiceId}`);
        const inv = await res.json();

        // 1. Header Information
        let invNum = inv.invoice_number || '01517';
        if (invNum.startsWith('INV-')) {
            invNum = invNum.replace('INV-', '');
        }
        const numEl = document.getElementById('print-inv-num');
        if (numEl) numEl.textContent = invNum;

        const dateEl = document.getElementById('print-inv-date');
        if (dateEl) {
            let d = inv.issue_date || (inv.created_at ? inv.created_at.split('T')[0] : '2026-10-11');
            if (d && d.includes('-')) {
                const parts = d.split('-');
                if (parts.length === 3) d = `${parts[2]}/${parts[1]}/${parts[0]}`;
            }
            dateEl.textContent = d;
        }

        const headTotalEl = document.getElementById('print-header-total');
        if (headTotalEl) headTotalEl.textContent = (inv.total_amount || 0).toFixed(2);

        // 2. Customer & Recipient Details (للمدير والمنسق)
        const custNameEl = document.getElementById('print-cust-name');
        if (custNameEl) custNameEl.textContent = inv.customer_name || '-';

        const custPhoneEl = document.getElementById('print-cust-phone');
        if (custPhoneEl) custPhoneEl.textContent = inv.customer_phone || '-';

        const recNameEl = document.getElementById('print-rec-name');
        if (recNameEl) recNameEl.textContent = inv.recipient_name || inv.customer_name || '-';

        const recPhoneEl = document.getElementById('print-rec-phone');
        if (recPhoneEl) recPhoneEl.textContent = inv.recipient_phone || inv.customer_phone || '-';

        const recAddrEl = document.getElementById('print-rec-address');
        if (recAddrEl) recAddrEl.textContent = inv.recipient_address || 'استلام بالمعرض';

        // 3. Card Message Box
        const cardBox = document.getElementById('print-card-box');
        const cardText = document.getElementById('print-card-text');
        if (inv.card_message && cardBox && cardText) {
            cardBox.classList.remove('hidden');
            cardText.textContent = `« ${inv.card_message} »`;
        } else if (cardBox) {
            cardBox.classList.add('hidden');
        }

        // 4. Items Table (Net Unit Price & Subtotals matching the official PDF)
        const tbody = document.getElementById('print-items-tbody');
        tbody.innerHTML = '';
        let calculatedNetSubtotal = 0;

        if (inv.items && inv.items.length > 0) {
            inv.items.forEach((it, idx) => {
                const netUnit = it.unit_price / 1.15;
                const netItemTotal = netUnit * it.quantity;
                calculatedNetSubtotal += netItemTotal;

                const tr = document.createElement('tr');
                tr.className = (idx % 2 === 1) ? 'bg-[#f7f9f5] border-b border-slate-100' : 'bg-white border-b border-slate-100';
                tr.innerHTML = `
                    <td class="py-2.5 px-3 font-semibold text-slate-800 text-left">${it.product_name}</td>
                    <td class="py-2.5 px-3 text-center font-mono text-slate-700">${netUnit.toFixed(2)}</td>
                    <td class="py-2.5 px-3 text-center font-bold text-slate-800">${it.quantity}</td>
                    <td class="py-2.5 px-3 text-right font-black font-mono text-slate-900">${netItemTotal.toFixed(2)}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        // If order has delivery fee, render delivery fee as an item line (e.g., توصيل - Delivery - D 30.43)
        if (inv.delivery_fee && inv.delivery_fee > 0) {
            const netDelivery = inv.delivery_fee / 1.15;
            calculatedNetSubtotal += netDelivery;
            const tr = document.createElement('tr');
            tr.className = 'border-b border-slate-100 bg-[#f7f9f5]';
            tr.innerHTML = `
                <td class="py-2.5 px-3 font-semibold text-slate-800 text-left">توصيل - Delivery - D</td>
                <td class="py-2.5 px-3 text-center font-mono text-slate-700">${netDelivery.toFixed(2)}</td>
                <td class="py-2.5 px-3 text-center font-bold text-slate-800">1</td>
                <td class="py-2.5 px-3 text-right font-black font-mono text-slate-900">${netDelivery.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        }

        // 5. Calculations for Summary Box
        const discountAmount = inv.discount || 0.0;
        const netBaseTotal = inv.subtotal ? inv.subtotal : calculatedNetSubtotal;
        const vatAmount = inv.tax_amount ? inv.tax_amount : (netBaseTotal * 0.15);
        const grandTotal = inv.total_amount || (netBaseTotal + vatAmount - discountAmount);
        const paidAmount = inv.paid_amount || (inv.status === 'paid' ? grandTotal : 0.0);
        const remainingAmount = Math.max(0, grandTotal - paidAmount);

        document.getElementById('print-subtotal').textContent = netBaseTotal.toFixed(2);
        document.getElementById('print-discount').textContent = discountAmount > 0 ? `-${discountAmount.toFixed(2)}` : `-0.00`;
        document.getElementById('print-tax').textContent = vatAmount.toFixed(2);
        document.getElementById('print-grand-total').textContent = grandTotal.toFixed(2);
        document.getElementById('print-paid-amt').textContent = `-${paidAmount.toFixed(2)}`;
        document.getElementById('print-remaining-amt').textContent = remainingAmount.toFixed(2);

        // 6. QR Code
        const qrEl = document.getElementById('print-zatca-qr');
        if (qrEl) qrEl.src = inv.qr_image || '';

        openModal('modal-invoice-detail');
    } catch (err) {
        console.error("Print invoice error:", err);
    }
}

async function openInvoicePrintModalByOrder(orderId) {
    try {
        const res = await fetch(`/api/orders/${orderId}`);
        const ord = await res.json();
        if (ord.invoice_id) {
            openInvoicePrintModal(ord.invoice_id);
        } else {
            alert("لا توجد فاتورة مرتبطة بهذا الطلب");
        }
    } catch (err) {
        console.error(err);
    }
}

// 6. DRIVERS LOGISTICS
async function loadDrivers() {
    try {
        const res = await fetch('/api/drivers');
        allDrivers = await res.json();
    } catch (err) {
        console.error("Load drivers list error:", err);
    }
}

async function loadDriversView() {
    await loadDrivers();
    const grid = document.getElementById('drivers-cards-grid');
    grid.innerHTML = '';

    const canManageDrivers = isManagerRole();
    const addDriverBtn = document.getElementById('btn-add-driver');
    if (addDriverBtn) {
        if (canManageDrivers) {
            addDriverBtn.classList.remove('hidden');
        } else {
            addDriverBtn.classList.add('hidden');
        }
    }

    allDrivers.forEach(d => {
        const card = document.createElement('div');
        card.className = 'bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm space-y-4';

        const statusLabel = d.status === 'available'
            ? `<span class="badge-status bg-emerald-100 text-emerald-800">متاح للتوصيل ✅</span>`
            : d.status === 'on_delivery'
            ? `<span class="badge-status bg-indigo-100 text-indigo-800">في مشوار توصيل 🚗</span>`
            : `<span class="badge-status bg-slate-100 text-slate-700">خارج الدوام</span>`;

        card.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-11 h-11 rounded-2xl bg-indigo-50 text-indigo-700 flex items-center justify-center font-bold">
                        <i data-lucide="truck" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <h4 class="font-bold text-slate-800 text-sm">${d.name}</h4>
                        <span class="text-xs text-slate-400 font-mono">${d.phone}</span>
                    </div>
                </div>
                ${statusLabel}
            </div>

            <p class="text-xs text-slate-500 bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                <i data-lucide="shield-check" class="w-3.5 h-3.5 inline text-brand-600 ml-1"></i>
                ${d.vehicle}
            </p>

            <div class="grid grid-cols-2 gap-2 text-center text-xs">
                <div class="p-2.5 bg-slate-50 rounded-xl">
                    <span class="text-slate-400 block text-[11px]">طلبات حالية</span>
                    <strong class="text-base text-slate-800 font-black">${d.current_active_orders || 0}</strong>
                </div>
                <div class="p-2.5 bg-emerald-50 rounded-xl">
                    <span class="text-emerald-700 block text-[11px]">تم توصيلها</span>
                    <strong class="text-base text-emerald-800 font-black">${d.total_delivered}</strong>
                </div>
            </div>

            <div class="pt-2 border-t border-slate-100 flex items-center justify-between">
                <span class="text-xs text-slate-500 font-medium">العمولة: <strong>${d.commission_per_order} ر.س / طلب</strong></span>
                <div class="flex items-center gap-1.5">
                    <button onclick="openWhatsAppChatDirect('${d.phone}', '${d.name}', 'مرحباً ${d.name} 🌸 جاهز لتوصيل طلبات نبت اليوم؟')" class="text-xs bg-emerald-50 text-emerald-700 hover:bg-emerald-100 px-3 py-1.5 rounded-xl font-bold flex items-center gap-1 border border-emerald-200 cursor-pointer">
                        <i data-lucide="message-circle" class="w-3.5 h-3.5"></i>
                        محادثة
                    </button>
                    ${canManageDrivers ? `
                    <button onclick="confirmDeleteDriver(${d.id}, '${d.name.replace(/'/g, "\\'")}', ${d.current_active_orders || 0})" title="حذف المندوب من النظام" class="text-xs bg-rose-50 text-rose-700 hover:bg-rose-100 px-2.5 py-1.5 rounded-xl font-bold flex items-center gap-1 border border-rose-200 cursor-pointer transition-all">
                        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                        حذف
                    </button>
                    ` : ''}
                </div>
            </div>
        `;
        grid.appendChild(card);
    });

    initIcons();
}

function openNewDriverModal() {
    if (!isManagerRole()) {
        alert("عذراً! صلاحية إضافة المناديب محصورة على المديرين فقط (نادر، فيصل، ياسر).");
        return;
    }
    openModal('modal-new-driver');
}

async function handleCreateDriver(event) {
    event.preventDefault();
    if (!isManagerRole()) {
        alert("عذراً! صلاحية إضافة المناديب محصورة على المديرين فقط (نادر، فيصل، ياسر).");
        return;
    }
    const payload = {
        name: document.getElementById('driver-name-input').value.trim(),
        phone: document.getElementById('driver-phone-input').value.trim(),
        vehicle: document.getElementById('driver-vehicle-input').value.trim(),
        commission_per_order: parseFloat(document.getElementById('driver-commission-input').value || 25)
    };

    try {
        const res = await fetch('/api/drivers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-new-driver');
            await loadDriversView();
            await loadDrivers();
            alert("تمت إضافة المندوب بنجاح");
        } else {
            alert(data.detail || "حدث خطأ");
        }
    } catch (err) {
        console.error(err);
    }
}

async function confirmDeleteDriver(driverId, driverName, activeOrders) {
    if (!isManagerRole()) {
        alert("عذراً! صلاحية حذف المناديب محصورة على المديرين فقط (نادر، فيصل، ياسر).");
        return;
    }

    if (activeOrders > 0) {
        alert(`تنبيه: لا يمكن حذف المندوب (${driverName}) حالياً لأن لديه (${activeOrders}) طلبات جارية قيد التوصيل!\nيرجى إعادة إسناد الطلبات لمندوب آخر أو إنهاؤها أولاً.`);
        return;
    }

    if (!confirm(`هل أنت متأكد من حذف المندوب "${driverName}" نهائياً من السيستم؟`)) {
        return;
    }

    try {
        const res = await fetch(`/api/drivers/${driverId}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (res.ok && data.success) {
            alert(data.message || `تم حذف المندوب ${driverName} بنجاح`);
            await loadDriversView();
            await loadDrivers();
        } else {
            alert(data.detail || "تعذر حذف المندوب");
        }
    } catch (err) {
        console.error("Delete driver error:", err);
        alert("حدث خطأ أثناء محاولة حذف المندوب");
    }
}

async function promptAssignDriver(orderId) {
    if (allDrivers.length === 0) await loadDrivers();
    let promptMsg = "اختر رقم المندوب المراد إسناد الطلب له:\n";
    allDrivers.forEach((d, idx) => {
        promptMsg += `${idx + 1}. ${d.name} (${d.phone})\n`;
    });
    const choice = prompt(promptMsg);
    if (!choice) return;

    const selectedIndex = parseInt(choice) - 1;
    if (selectedIndex >= 0 && selectedIndex < allDrivers.length) {
        const driver = allDrivers[selectedIndex];
        try {
            const res = await fetch(`/api/orders/${orderId}/assign-driver`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ driver_id: driver.id })
            });
            const data = await res.json();
            if (data.success) {
                loadOrders();
                loadDashboardData();
                alert(`✓ تم إسناد الطلب للمندوب: ${driver.name}`);
            }
        } catch (err) {
            console.error(err);
        }
    }
}

async function promptAssignFlorist(orderId) {
    try {
        const ordRes = await fetch(`/api/orders/${orderId}`);
        const ord = await ordRes.json();
        const delivDate = ord.delivery_date || '';

        const res = await fetch(`/api/employees/available-florists${delivDate ? '?delivery_date=' + encodeURIComponent(delivDate) : ''}`);
        const availableFlorists = await res.json();
        
        if (availableFlorists.length === 0) {
            alert("⚠️ تنبيه: لا يوجد منسقين مسجلين في النظام!");
            return;
        }

        const eligibleFlorists = availableFlorists.filter(f => f.is_available_on_date);
        if (eligibleFlorists.length === 0) {
            alert(`⚠️ تنبيه: لا يوجد منسقين متاحين للعمل بتاريخ التسليم (${delivDate})! جميع المنسقين في إجازة أو راحة أسبوعية.`);
            return;
        }

        let promptMsg = `🌸 اختر المنسق المتاح لتجهيز هذا الطلب (تاريخ التسليم: ${delivDate}):\n`;
        eligibleFlorists.forEach((f, idx) => {
            promptMsg += `${idx + 1}. ${f.name} (طلباته الحالية: ${f.current_workload} - راحته الأسبوعية: يوم ${f.weekly_off_day || 'الثلاثاء'})\n`;
        });
        const choice = prompt(promptMsg);
        if (!choice) return;

        const selectedIndex = parseInt(choice) - 1;
        if (selectedIndex >= 0 && selectedIndex < eligibleFlorists.length) {
            const florist = eligibleFlorists[selectedIndex];
            const assignRes = await fetch(`/api/orders/${orderId}/assign-florist`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ florist_id: florist.id })
            });
            const data = await assignRes.json();
            if (data.success) {
                loadOrders();
                alert(`✓ تم إسناد تجهيز الطلب للمنسق: ${florist.name}`);
            } else {
                alert(data.detail || "حدث خطأ");
            }
        }
    } catch (err) {
        console.error(err);
    }
}

// 7. CUSTOMERS CRM
async function loadCustomers() {
    try {
        const res = await fetch('/api/customers');
        const customers = await res.json();
        const tbody = document.getElementById('customers-table-tbody');
        tbody.innerHTML = '';

        customers.forEach(c => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-50 transition-colors text-xs border-b border-slate-100';

            let occasionsBadges = '-';
            if (c.special_occasions && c.special_occasions.length > 0) {
                occasionsBadges = c.special_occasions.map(occ => `<span class="inline-block bg-purple-100 text-purple-800 text-[10px] font-bold px-2 py-0.5 rounded-full ml-1 mb-1">${occ.type} (${occ.date})</span>`).join(' ');
            }

            tr.innerHTML = `
                <td class="py-3 px-4">
                    <strong class="text-slate-800 text-sm block">${c.name}</strong>
                    ${c.notes ? `<p class="text-[11px] text-brand-700">${c.notes}</p>` : ''}
                </td>
                <td class="py-3 px-4 font-mono font-medium text-slate-600">${c.phone}</td>
                <td class="py-3 px-4 text-slate-500 max-w-[200px] truncate">${c.address || '-'}</td>
                <td class="py-3 px-4 font-bold text-slate-800">${c.orders_count || 0} طلبات</td>
                <td class="py-3 px-4 font-black text-brand-700">${c.total_spent.toFixed(2)} ر.س</td>
                <td class="py-3 px-4">${occasionsBadges}</td>
                <td class="py-3 px-4 text-center">
                    <button onclick="openWhatsAppChatDirect('${c.phone}', '${c.name}', 'أهلاً بك عميلنا العزيز ${c.name} في نبت للورد 🌸')" class="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 px-3 py-1.5 rounded-xl font-bold flex items-center gap-1 mx-auto">
                        <i data-lucide="message-circle" class="w-3.5 h-3.5"></i>
                        شات واتس اب
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        initIcons();
    } catch (err) {
        console.error("Load customers error:", err);
    }
}

// 8. EXPENSES & P&L
async function loadExpenses() {
    try {
        const res = await fetch('/api/expenses');
        const data = await res.json();
        const tbody = document.getElementById('expenses-table-tbody');
        tbody.innerHTML = '';

        data.expenses.forEach(ex => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-50 transition-colors text-xs border-b border-slate-100';
            tr.innerHTML = `
                <td class="py-3 px-4 font-bold text-slate-800">${ex.title}</td>
                <td class="py-3 px-4">
                    <span class="bg-rose-50 text-rose-700 font-semibold px-2 py-0.5 rounded-md border border-rose-100">${ex.category}</span>
                </td>
                <td class="py-3 px-4 font-black text-rose-700 text-sm">${ex.amount.toFixed(2)} ر.س</td>
                <td class="py-3 px-4 text-slate-500">${ex.expense_date}</td>
                <td class="py-3 px-4 text-slate-700">${ex.vendor_name || '-'}</td>
                <td class="py-3 px-4 text-slate-600">${ex.payment_method}</td>
            `;
            tbody.appendChild(tr);
        });

        // Category breakdown
        const list = document.getElementById('expenses-breakdown-list');
        list.innerHTML = '';
        data.category_summary.forEach(cat => {
            const div = document.createElement('div');
            div.className = 'flex items-center justify-between text-xs py-1.5 border-b border-slate-100';
            div.innerHTML = `
                <span class="text-slate-700 font-medium">${cat.category}</span>
                <strong class="text-rose-700 font-bold">${cat.total.toFixed(2)} ر.س</strong>
            `;
            list.appendChild(div);
        });

        initIcons();
    } catch (err) {
        console.error("Load expenses error:", err);
    }
}

function openNewExpenseModal() {
    openModal('modal-new-expense');
}

async function handleCreateExpense(event) {
    event.preventDefault();
    const payload = {
        title: document.getElementById('exp-title-input').value,
        category: document.getElementById('exp-category-select').value,
        amount: parseFloat(document.getElementById('exp-amount-input').value),
        vendor_name: document.getElementById('exp-vendor-input').value || null
    };

    try {
        const res = await fetch('/api/expenses', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-new-expense');
            loadExpenses();
            loadDashboardData();
            alert("تم تسجيل المصروف بنجاح وتحديث حسابات الأرباح");
        }
    } catch (err) {
        console.error(err);
    }
}

// 9. PRODUCTS CATALOG
async function loadProducts() {
    try {
        const res = await fetch('/api/products');
        allProducts = await res.json();

        const grid = document.getElementById('products-grid');
        if (!grid) return;
        grid.innerHTML = '';

        allProducts.forEach(p => {
            const card = document.createElement('div');
            card.className = 'bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden flex flex-col group';
            card.innerHTML = `
                <div class="h-44 bg-slate-100 overflow-hidden relative">
                    <img src="${p.image_url}" alt="${p.name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300">
                    <span class="absolute top-2.5 right-2.5 bg-slate-900/80 backdrop-blur-sm text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                        ${p.category}
                    </span>
                </div>
                <div class="p-4 flex-1 flex flex-col justify-between space-y-3">
                    <div>
                        <h4 class="font-bold text-slate-800 text-sm line-clamp-1">${p.name}</h4>
                        <p class="text-xs text-slate-500 mt-1 line-clamp-2">${p.description || ''}</p>
                    </div>

                    <div class="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
                        <div>
                            <span class="text-[10px] text-slate-400 block">سعر البيع</span>
                            <span class="font-black text-brand-700 text-base">${p.price} ر.س</span>
                        </div>
                        <div class="text-left">
                            <span class="text-[10px] text-slate-400 block">المخزون المتوفر</span>
                            <span class="font-bold text-slate-700">${p.stock} قطعة</span>
                        </div>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });

        initIcons();
    } catch (err) {
        console.error("Load products error:", err);
    }
}

// GENERAL MODAL HELPERS
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
        initIcons();
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
        modal.style.removeProperty('display');
    }
}

// 10. ACCOUNTING WEBHOOK & SIMULATION LOGIC
function openAccountingSyncModal() {
    openModal('modal-accounting-sync');
}

function copyToClipboard(inputId) {
    const input = document.getElementById(inputId);
    input.select();
    navigator.clipboard.writeText(input.value);
    alert("تم نسخ رابط الاستقبال بنجاح! يمكنك الآن لصقه في برنامج الحسابات.");
}

async function triggerSimulateAccountingInvoice() {
    try {
        const res = await fetch('/api/sync/simulate', { method: 'POST' });
        const data = await res.json();
        
        if (data.success) {
            // Refresh data immediately across all tabs
            loadDashboardData();
            loadOrders();
            loadInvoices();
            loadWhatsAppConversations();
            
            // Show toast notification
            showInvoiceArrivalToast(data.invoice_number, data.payment_status);
        }
    } catch (err) {
        console.error("Simulation error:", err);
    }
}

function showInvoiceArrivalToast(invoiceNumber, paymentStatus) {
    const isPaid = paymentStatus === 'paid';
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-6 left-6 z-50 bg-slate-900 text-white p-4 rounded-2xl shadow-2xl border border-emerald-500/40 flex items-center gap-3 animate-bounce';
    toast.innerHTML = `
        <div class="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center flex-shrink-0 text-xl">
            ⚡
        </div>
        <div class="text-right">
            <h5 class="text-xs font-black text-emerald-400 flex items-center gap-1">
                استقبال فاتورة جديدة من نظام الحسابات!
            </h5>
            <p class="text-[11px] text-slate-300 mt-0.5">
                فاتورة رقم <strong class="text-white">${invoiceNumber}</strong> (${isPaid ? 'مسددة ✅' : 'غير مسددة ⚠️'}).
            </p>
            <span class="text-[10px] text-emerald-300 block">✓ تم تحديث المبيعات وحفظ الفاتورة</span>
        </div>
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

// 11. SMART BOT & GATEWAY HANDLERS
function openSimulateBotModal() {
    openModal('modal-simulate-bot');
}

async function sendSimulatedCustomerQuery(queryText) {
    closeModal('modal-simulate-bot');
    
    // Pick the phone of the currently active customer or default
    const testPhone = currentActiveChatPhone || "0505112233";
    const testName = document.getElementById('chat-active-name')?.textContent || "سارة عبد العزيز";

    try {
        const res = await fetch('/api/whatsapp/simulate-customer-message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phone: testPhone,
                message: queryText,
                customer_name: testName
            })
        });
        const data = await res.json();
        if (data.success) {
            // Reload conversations and select this chat
            await loadWhatsAppConversations();
            selectWhatsAppConversation(testPhone, testName);
        }
    } catch (err) {
        console.error("Bot simulation error:", err);
    }
}

function handleCustomSimulatedQuery(event) {
    event.preventDefault();
    const input = document.getElementById('sim-custom-query-input');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    sendSimulatedCustomerQuery(text);
}

async function toggleBotStatus() {
    const btn = document.getElementById('bot-toggle-btn');
    const isCurrentlyActive = btn.textContent.includes('نشط');
    const newStatus = !isCurrentlyActive;

    try {
        await fetch('/api/whatsapp/toggle-bot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: newStatus })
        });

        if (newStatus) {
            btn.className = 'text-[11px] font-black bg-purple-600 hover:bg-purple-700 text-white px-2.5 py-0.5 rounded-lg shadow-sm';
            btn.textContent = 'نشط ويرد آلياً ✅';
        } else {
            btn.className = 'text-[11px] font-black bg-slate-400 hover:bg-slate-500 text-white px-2.5 py-0.5 rounded-lg shadow-sm';
            btn.textContent = 'متوقف مؤقتاً ⏸️';
        }
    } catch (err) {
        console.error(err);
    }
}

async function openGatewaySettingsModal() {
    try {
        const res = await fetch('/api/whatsapp/bot-settings');
        const settings = await res.json();
        document.getElementById('gateway-instance-input').value = settings.ultramsg_instance_id || '';
        document.getElementById('gateway-token-input').value = settings.ultramsg_token || '';
        openModal('modal-gateway-settings');
    } catch (err) {
        console.error(err);
    }
}

async function handleSaveGatewaySettings(event) {
    event.preventDefault();
    const instanceId = document.getElementById('gateway-instance-input').value.trim();
    const token = document.getElementById('gateway-token-input').value.trim();

    try {
        const res = await fetch('/api/whatsapp/bot-settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                bot_enabled: true,
                ultramsg_instance_id: instanceId,
                ultramsg_token: token
            })
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-gateway-settings');
            alert("تم حفظ بيانات ربط الواتساب بنجاح! السيستم جاهز الآن للإرسال والتحدث عبر رقمك المباشر.");
        }
    } catch (err) {
        console.error(err);
    }
}

// 12. EMPLOYEES & LEAVES MANAGEMENT LOGIC
let activeEmployeeRoleFilter = 'all';

async function loadEmployees(role = null) {
    if (role !== null) activeEmployeeRoleFilter = role;
    try {
        const res = await fetch(`/api/employees?role=${activeEmployeeRoleFilter}`);
        const employees = await res.json();

        // Calculate stats
        let total = employees.length;
        let onduty = 0;
        let onleave = 0;
        employees.forEach(e => {
            if (e.status === 'on_duty') onduty++;
            if (e.status === 'on_leave') onleave++;
        });

        const statTotal = document.getElementById('emp-stat-total');
        if (statTotal) statTotal.textContent = total;
        const statOnduty = document.getElementById('emp-stat-onduty');
        if (statOnduty) statOnduty.textContent = onduty;
        const statOnleave = document.getElementById('emp-stat-onleave');
        if (statOnleave) statOnleave.textContent = onleave;

        const badgeLeaves = document.getElementById('badge-nav-leaves');
        if (badgeLeaves) badgeLeaves.textContent = `${onduty} في المحل`;

        const grid = document.getElementById('employees-cards-grid');
        if (!grid) return;
        grid.innerHTML = '';

        if (employees.length === 0) {
            grid.innerHTML = `<div class="col-span-full py-8 text-center text-slate-400 text-xs">لا يوجد موظفين مسجلين في هذا القسم</div>`;
            return;
        }

        employees.forEach(e => {
            const card = document.createElement('div');
            card.className = `p-5 rounded-2xl border transition-all space-y-4 ${e.status === 'on_leave' ? 'bg-purple-50/30 border-purple-200' : 'bg-white border-slate-200/80 shadow-sm'}`;

            const roleBadges = {
                'florist': '<span class="text-[10px] bg-purple-100 text-purple-800 font-bold px-2 py-0.5 rounded-full">منسق ورد 🌸</span>',
                'driver': '<span class="text-[10px] bg-indigo-100 text-indigo-800 font-bold px-2 py-0.5 rounded-full">مندوب توصيل 🚗</span>',
                'cashier': '<span class="text-[10px] bg-blue-100 text-blue-800 font-bold px-2 py-0.5 rounded-full">كاشير ومحاسب 🧾</span>',
                'manager': '<span class="text-[10px] bg-amber-100 text-amber-800 font-bold px-2 py-0.5 rounded-full">إدارة وإشراف 👑</span>'
            };

            const statusBadges = {
                'on_duty': '<span class="badge-status bg-emerald-100 text-emerald-800">في المحل 🟢</span>',
                'on_leave': '<span class="badge-status bg-purple-100 text-purple-800 font-bold">في إجازة 🏖️</span>',
                'off_duty': '<span class="badge-status bg-slate-100 text-slate-700">خارج الدوام ⏸️</span>'
            };

            card.innerHTML = `
                <div class="flex items-start justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-11 h-11 rounded-2xl ${e.status === 'on_leave' ? 'bg-purple-100 text-purple-700' : 'bg-brand-50 text-brand-700'} flex items-center justify-center font-bold text-base">
                            ${e.name.charAt(0)}
                        </div>
                        <div>
                            <div class="flex items-center gap-1.5 flex-wrap">
                                <h4 class="font-bold text-slate-800 text-sm">${e.name}</h4>
                                ${e.username ? `<span class="text-[10px] bg-slate-100 text-slate-700 font-mono font-bold px-1.5 py-0.5 rounded-md border border-slate-200">@${e.username}</span>` : ''}
                            </div>
                            <span class="text-xs text-slate-400 font-mono">${e.phone}</span>
                        </div>
                    </div>
                    <div class="text-left space-y-1">
                        <div>${roleBadges[e.role] || e.role}</div>
                        <div>${statusBadges[e.status] || e.status}</div>
                    </div>
                </div>

                <div class="p-2.5 bg-slate-50 rounded-xl text-xs space-y-1.5 text-slate-600 border border-slate-100">
                    <div class="flex justify-between">
                        <span class="text-slate-400 text-[11px]">التخصص والمهام:</span>
                        <strong class="text-slate-700">${e.specialty || 'تنسيق عام'}</strong>
                    </div>
                    <div class="flex justify-between border-t border-slate-200/60 pt-1">
                        <span class="text-slate-400 text-[11px]">الراحة الأسبوعية:</span>
                        <span class="inline-flex items-center gap-1 bg-amber-50 text-amber-800 border border-amber-200 px-2 py-0.5 rounded-md font-bold text-[11px]">
                            <i data-lucide="coffee" class="w-3 h-3 text-amber-600"></i>
                            <span>يوم ${e.weekly_off_day || 'الثلاثاء'}</span>
                        </span>
                    </div>
                    ${e.role === 'florist' ? `
                    <div class="flex justify-between border-t border-slate-200/60 pt-1">
                        <span class="text-slate-400 text-[11px]">الطلبات قيد التجهيز:</span>
                        <strong class="${e.current_preparing_orders > 0 ? 'text-brand-700 font-black' : 'text-slate-600'}">${e.current_preparing_orders || 0} طلب</strong>
                    </div>
                    ` : ''}
                </div>

                ${e.is_today_weekly_off ? `
                    <div class="p-2 bg-amber-100/70 border border-amber-200 rounded-xl text-[11px] text-amber-900 flex items-center gap-1.5 font-bold">
                        <i data-lucide="coffee" class="w-3.5 h-3.5 text-amber-700 flex-shrink-0"></i>
                        <span>اليوم راحة أسبوعية (يوم ${e.weekly_off_day}) - مستبعد من استلام الطلبات ☕</span>
                    </div>
                ` : ''}

                ${e.current_leave_info ? `
                    <div class="p-2 bg-purple-100/60 border border-purple-200 rounded-xl text-[11px] text-purple-900 flex items-center gap-1.5 font-semibold">
                        <i data-lucide="sun" class="w-3.5 h-3.5 text-purple-600 flex-shrink-0"></i>
                        <span>${e.current_leave_info} (مستبعد من استلام الطلبات)</span>
                    </div>
                ` : ''}

                <!-- Quick Action Buttons -->
                <div class="pt-2 border-t border-slate-100 flex items-center justify-between gap-1.5 text-xs">
                    ${isLeaveManager() ? `
                        ${e.status === 'on_leave' ? `
                            <button onclick="updateEmployeeStatus(${e.id}, 'on_duty')" class="flex-1 text-[11px] bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 py-1.5 rounded-xl font-bold transition-all">
                                إعادة للعمل 🟢
                            </button>
                        ` : `
                            <button onclick="updateEmployeeStatus(${e.id}, 'on_leave')" class="flex-1 text-[11px] bg-purple-50 hover:bg-purple-100 text-purple-800 border border-purple-200 py-1.5 rounded-xl font-bold transition-all">
                                تحويل لإجازة 🏖️
                            </button>
                        `}
                        <button onclick="openEditWeeklyOffModal(${e.id}, '${e.name.replace(/'/g, "\\'")}', '${e.weekly_off_day || 'الثلاثاء'}')" title="تعديل يوم الراحة الأسبوعية (نادر/فيصل/ياسر)" class="p-1.5 bg-amber-50 hover:bg-amber-100 border border-amber-200 text-amber-800 rounded-xl flex items-center gap-1 font-bold text-[11px]">
                            <i data-lucide="coffee" class="w-3.5 h-3.5"></i>
                            <span class="hidden sm:inline">الراحة</span>
                        </button>
                        <button onclick="openRecordLeaveModalFor(${e.id})" title="تسجيل إجازة" class="p-1.5 bg-purple-50 hover:bg-purple-100 border border-purple-200 text-purple-700 rounded-xl">
                            <i data-lucide="calendar" class="w-3.5 h-3.5"></i>
                        </button>
                        ${!['yasser', 'faisal', 'nader'].includes((e.username || '').toLowerCase()) && ![1, 2, 3].includes(e.id) ? `
                        <button onclick="handleDeleteEmployee(${e.id}, '${e.name.replace(/'/g, "\\'")}')" title="حذف الموظف من النظام (نادر/فيصل/ياسر)" class="p-1.5 bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-700 rounded-xl transition-all cursor-pointer">
                            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                        </button>
                        ` : ''}
                    ` : `
                        <div class="flex-1 text-[11px] text-slate-400 py-1 text-center font-semibold">
                            صلاحيات الإدارة لنادر وفيصل وياسر
                        </div>
                    `}
                    <button onclick="openWhatsAppChatDirect('${e.phone}', '${e.name}', 'مرحباً ${e.name} 🌸')" title="محادثة واتساب" class="p-1.5 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-emerald-700 rounded-xl">
                        <i data-lucide="message-circle" class="w-3.5 h-3.5"></i>
                    </button>
                </div>
            `;
            grid.appendChild(card);
        });

        initIcons();
    } catch (err) {
        console.error("Load employees error:", err);
    }
}

function filterEmployees(role) {
    activeEmployeeRoleFilter = role;
    document.querySelectorAll('.emp-filter-btn').forEach(btn => {
        if (btn.getAttribute('data-role') === role) {
            btn.className = 'emp-filter-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-brand-600 text-white';
        } else {
            btn.className = 'emp-filter-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 text-slate-600 hover:bg-slate-200';
        }
    });
    loadEmployees(role);
}

function isLeaveManager() {
    if (!currentUser) return false;
    const uname = (currentUser.username || currentUser.name || '').toLowerCase();
    const role = (currentUser.role || '').toLowerCase();
    const isNamedManager = uname.includes('nader') || uname.includes('نادر') || 
                           uname.includes('faisal') || uname.includes('فيصل') || 
                           uname.includes('yasser') || uname.includes('ياسر');
    const isRoleManager = ['general_manager', 'operations_manager', 'branch_manager', 'admin', 'manager'].includes(role);
    return isNamedManager || isRoleManager;
}

async function updateEmployeeStatus(empId, newStatus) {
    if (!isLeaveManager()) {
        alert("عذراً! صلاحية تعديل حالة دوام الموظفين محصورة على المسؤولين (مدير الفرع نادر أو الإدارة العامة).");
        return;
    }
    try {
        const res = await fetch(`/api/employees/${empId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        const data = await res.json();
        if (data.success) {
            loadEmployees();
            loadLeaves();
        }
    } catch (err) {
        console.error(err);
    }
}

async function loadLeaves() {
    try {
        const res = await fetch('/api/employees/leaves');
        const leaves = await res.json();
        const tbody = document.getElementById('leaves-table-tbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (leaves.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="py-6 text-center text-slate-400 text-xs">لا توجد إجازات مسجلة حالياً</td></tr>`;
            return;
        }

        leaves.forEach(l => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-50 transition-colors text-xs border-b border-slate-100';

            const today = new Date().toISOString().split('T')[0];
            const isActiveToday = l.start_date <= today && l.end_date >= today;

            tr.innerHTML = `
                <td class="py-3 px-3">
                    <strong class="text-slate-800 block">${l.employee_name}</strong>
                    <span class="text-slate-400 font-mono text-[11px]">${l.employee_phone}</span>
                </td>
                <td class="py-3 px-3 text-slate-600">${l.employee_role === 'florist' ? 'منسق ورد 🌸' : l.employee_role}</td>
                <td class="py-3 px-3">
                    <span class="inline-flex items-center gap-1 bg-amber-50 text-amber-800 border border-amber-200 px-2 py-0.5 rounded-md font-bold text-[11px]">
                        <i data-lucide="coffee" class="w-3 h-3 text-amber-600"></i>
                        <span>يوم ${l.weekly_off_day || 'الثلاثاء'}</span>
                    </span>
                </td>
                <td class="py-3 px-3">
                    <span class="inline-block bg-purple-100 text-purple-800 font-bold px-2 py-0.5 rounded-md text-[11px]">${l.leave_type}</span>
                    ${isActiveToday ? '<span class="inline-block bg-emerald-100 text-emerald-800 font-bold px-1.5 py-0.5 rounded text-[10px] mr-1">سارية الآن</span>' : ''}
                </td>
                <td class="py-3 px-3 font-semibold text-slate-800">${l.start_date}</td>
                <td class="py-3 px-3 font-semibold text-slate-800">${l.end_date}</td>
                <td class="py-3 px-3 text-slate-500 max-w-[200px] truncate">${l.reason || '-'}</td>
                <td class="py-3 px-3 text-center">
                    ${isLeaveManager() ? `
                        <div class="flex items-center justify-center gap-1.5">
                            <button onclick="openEditLeaveModal(${l.id}, '${l.employee_name}', '${l.leave_type}', '${l.start_date}', '${l.end_date}', '${(l.reason || '').replace(/'/g, "\\'")}')" class="text-[11px] text-amber-700 hover:text-amber-900 font-bold bg-amber-50 hover:bg-amber-100 border border-amber-200 px-2.5 py-1 rounded-lg transition-all flex items-center gap-1">
                                <i data-lucide="edit-3" class="w-3 h-3"></i> تعديل
                            </button>
                            <button onclick="cancelLeave(${l.id})" class="text-[11px] text-rose-600 hover:text-rose-800 font-bold bg-rose-50 hover:bg-rose-100 border border-rose-200 px-2.5 py-1 rounded-lg transition-all flex items-center gap-1">
                                <i data-lucide="trash-2" class="w-3 h-3"></i> إلغاء
                            </button>
                        </div>
                    ` : `
                        <span class="text-slate-400 text-[10px] italic">خاص بالمدير نادر</span>
                    `}
                </td>
            `;
            tbody.appendChild(tr);
        });

        initIcons();
    } catch (err) {
        console.error("Load leaves error:", err);
    }
}

function openEditLeaveModal(leaveId, empName, leaveType, startDate, endDate, reason) {
    if (!isLeaveManager()) {
        alert("عذراً! تعديل الإجازات محصور على المسؤولين (المدير نادر أو الإدارة العامة).");
        return;
    }
    document.getElementById('edit-leave-id').value = leaveId;
    document.getElementById('edit-leave-emp-name').value = empName;
    document.getElementById('edit-leave-type-select').value = leaveType;
    document.getElementById('edit-leave-start-date').value = startDate;
    document.getElementById('edit-leave-end-date').value = endDate;
    document.getElementById('edit-leave-reason-input').value = reason || '';
    openModal('modal-edit-leave');
}

async function handleUpdateLeave(event) {
    event.preventDefault();
    if (!isLeaveManager()) {
        alert("عذراً! صلاحية تعديل الإجازات محصورة على المسؤولين (المدير نادر أو الإدارة).");
        return;
    }

    const leaveId = document.getElementById('edit-leave-id').value;
    const payload = {
        leave_type: document.getElementById('edit-leave-type-select').value,
        start_date: document.getElementById('edit-leave-start-date').value,
        end_date: document.getElementById('edit-leave-end-date').value,
        reason: document.getElementById('edit-leave-reason-input').value.trim(),
        modified_by_username: currentUser ? currentUser.username : "nader",
        modified_by_role: currentUser ? currentUser.role : "branch_manager"
    };

    try {
        const res = await fetch(`/api/employees/leaves/${leaveId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-edit-leave');
            loadEmployees();
            loadLeaves();
            alert(`✓ ${data.message}`);
        } else {
            alert(data.detail || "حدث خطأ أثناء تعديل الإجازة");
        }
    } catch (err) {
        console.error(err);
    }
}

function openEditWeeklyOffModal(empId, empName, currentOffDay) {
    if (!isLeaveManager()) {
        alert("عذراً! تعديل يوم الراحة الأسبوعية محصور على المسؤولين (المدير نادر أو الإدارة العامة).");
        return;
    }
    const idEl = document.getElementById('weekly-off-emp-id');
    const nameEl = document.getElementById('weekly-off-emp-name');
    const dayEl = document.getElementById('weekly-off-day-select');
    if (idEl) idEl.value = empId;
    if (nameEl) nameEl.value = empName;
    if (dayEl) dayEl.value = currentOffDay || 'الثلاثاء';
    openModal('modal-edit-weekly-off');
}

async function handleUpdateWeeklyOff(event) {
    event.preventDefault();
    if (!isLeaveManager()) {
        alert("عذراً! تعديل يوم الراحة الأسبوعية محصور على المسؤولين (المدير نادر أو الإدارة العامة).");
        return;
    }

    const empId = document.getElementById('weekly-off-emp-id')?.value;
    const offDay = document.getElementById('weekly-off-day-select')?.value;
    if (!empId || !offDay) return;

    const payload = {
        weekly_off_day: offDay,
        modified_by_username: currentUser ? (currentUser.username || currentUser.name || "nader") : "nader",
        modified_by_role: currentUser ? (currentUser.role || "branch_manager") : "branch_manager"
    };

    try {
        const res = await fetch(`/api/employees/${empId}/weekly-off`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-edit-weekly-off');
            await loadEmployees();
            await loadLeaves();
            alert(`✓ ${data.message}`);
        } else {
            alert(data.detail || "حدث خطأ أثناء حفظ يوم الراحة الأسبوعية");
        }
    } catch (err) {
        console.error(err);
        alert("حدث خطأ في الاتصال بالخادم أثناء حفظ يوم الراحة الأسبوعية");
    }
}

function openNewEmployeeModal() {
    if (!isLeaveManager()) {
        alert("عذراً! إضافة الموظفين محصورة على المسؤولين (نادر، فيصل، ياسر).");
        return;
    }
    const pwdInput = document.getElementById('emp-password-input');
    if (pwdInput && !pwdInput.value) pwdInput.value = '123456';
    openModal('modal-new-employee');
}

async function handleCreateEmployee(event) {
    event.preventDefault();
    if (!isLeaveManager()) {
        alert("عذراً! إضافة الموظفين محصورة على المسؤولين (نادر، فيصل، ياسر).");
        return;
    }

    const name = document.getElementById('emp-name-input').value.trim();
    const phone = document.getElementById('emp-phone-input').value.trim();
    const username = (document.getElementById('emp-username-input')?.value || '').trim();
    const password = (document.getElementById('emp-password-input')?.value || '123456').trim();
    const role = document.getElementById('emp-role-select').value;
    const weekly_off_day = document.getElementById('emp-weekly-off-select')?.value || 'الثلاثاء';
    const specialty = document.getElementById('emp-specialty-input').value.trim();
    const status = document.getElementById('emp-status-select').value;

    const payload = {
        name,
        phone,
        role,
        username,
        password,
        weekly_off_day,
        specialty,
        status,
        requester_username: currentUser ? (currentUser.username || currentUser.name || '') : '',
        requester_role: currentUser ? (currentUser.role || '') : ''
    };

    try {
        const res = await fetch('/api/employees', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-new-employee');
            document.getElementById('emp-name-input').value = '';
            document.getElementById('emp-phone-input').value = '';
            if (document.getElementById('emp-username-input')) document.getElementById('emp-username-input').value = '';
            if (document.getElementById('emp-password-input')) document.getElementById('emp-password-input').value = '123456';
            if (document.getElementById('emp-specialty-input')) document.getElementById('emp-specialty-input').value = '';

            loadEmployees();
            alert(`✓ تم إنشاء حساب الموظف (${payload.name}) بنجاح!\n\n• اسم المستخدم لتسجيل الدخول: ${data.username}\n• كلمة المرور: ${data.password}\n\nيمكن للموظف الآن الدخول للنظام فوراً بهذه البيانات.`);
        } else {
            alert(data.detail || "حدث خطأ أثناء حفظ الموظف");
        }
    } catch (err) {
        console.error(err);
        alert("حدث خطأ أثناء الاتصال بالخادم");
    }
}

async function handleDeleteEmployee(empId, empName) {
    if (!isLeaveManager()) {
        alert("عذراً! صلاحية حذف الموظفين محصورة على مسؤولي النظام (نادر، فيصل، ياسر).");
        return;
    }
    if (!confirm(`هل أنت متأكد من رغبتك في حذف الموظف (${empName}) نهائياً من النظام؟\nلن يتمكن من تسجيل الدخول بعد الحذف.`)) {
        return;
    }

    try {
        const u = currentUser ? (currentUser.username || currentUser.name || '') : '';
        const r = currentUser ? (currentUser.role || '') : '';
        const res = await fetch(`/api/employees/${empId}?requester_username=${encodeURIComponent(u)}&requester_role=${encodeURIComponent(r)}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
            alert(`✓ ${data.message || 'تم حذف الموظف بنجاح'}`);
            loadEmployees();
            loadLeaves();
        } else {
            alert(data.detail || "حدث خطأ أثناء حذف الموظف");
        }
    } catch (err) {
        console.error(err);
        alert("تعذر الاتصال بالخادم لحذف الموظف");
    }
}

async function openRecordLeaveModal() {
    if (!isLeaveManager()) {
        alert("عذراً! تسجيل الإجازات محصور على المسؤولين (مدير الفرع نادر أو الإدارة العامة).");
        return;
    }
    await populateLeaveEmployeeSelect();
    const today = new Date().toISOString().split('T')[0];
    const nextWeek = new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0];
    document.getElementById('leave-start-date').value = today;
    document.getElementById('leave-end-date').value = nextWeek;
    openModal('modal-record-leave');
}

async function openRecordLeaveModalFor(employeeId) {
    if (!isLeaveManager()) {
        alert("عذراً! تسجيل الإجازات محصور على المسؤولين (مدير الفرع نادر أو الإدارة العامة).");
        return;
    }
    await openRecordLeaveModal();
    document.getElementById('leave-emp-select').value = employeeId;
}

async function populateLeaveEmployeeSelect() {
    try {
        const res = await fetch('/api/employees');
        const employees = await res.json();
        const select = document.getElementById('leave-emp-select');
        select.innerHTML = '<option value="">-- اختر الموظف --</option>';
        employees.forEach(e => {
            select.innerHTML += `<option value="${e.id}">${e.name} (${e.role === 'florist' ? 'منسق ورد' : e.role}) - راحة أسبوعية: [${e.weekly_off_day || 'الثلاثاء'}] - حالته: ${e.status === 'on_duty' ? 'في المحل 🟢' : 'في إجازة 🏖️'}</option>`;
        });
    } catch (err) {
        console.error(err);
    }
}

async function handleCreateLeave(event) {
    event.preventDefault();
    if (!isLeaveManager()) {
        alert("عذراً! تسجيل الإجازات محصور على المسؤولين (المدير نادر أو الإدارة العامة).");
        return;
    }

    const empId = parseInt(document.getElementById('leave-emp-select').value);
    const leaveType = document.getElementById('leave-type-select').value;
    const startDate = document.getElementById('leave-start-date').value;
    const endDate = document.getElementById('leave-end-date').value;
    const reason = document.getElementById('leave-reason-input').value.trim();

    if (!empId) {
        alert("يرجى اختيار الموظف أولاً");
        return;
    }

    try {
        const res = await fetch('/api/employees/leaves', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                employee_id: empId,
                leave_type: leaveType,
                start_date: startDate,
                end_date: endDate,
                reason: reason,
                created_by_username: currentUser ? currentUser.username : "nader",
                created_by_role: currentUser ? currentUser.role : "branch_manager"
            })
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-record-leave');
            loadEmployees();
            loadLeaves();
            alert(`✓ ${data.message}`);
        } else {
            alert(data.detail || "حدث خطأ");
        }
    } catch (err) {
        console.error(err);
    }
}

async function cancelLeave(leaveId) {
    if (!isLeaveManager()) {
        alert("عذراً! صلاحية إلغاء الإجازات محصورة على المسؤولين (المدير نادر أو الإدارة العامة).");
        return;
    }
    if (!confirm("هل أنت متأكد من إلغاء الإجازة وإعادة الموظف لحالة العمل (في المحل)؟")) return;
    try {
        const u = currentUser ? currentUser.username : "nader";
        const r = currentUser ? currentUser.role : "branch_manager";
        const res = await fetch(`/api/employees/leaves/${leaveId}?user_name=${encodeURIComponent(u)}&user_role=${encodeURIComponent(r)}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            loadEmployees();
            loadLeaves();
            alert("✓ تم إلغاء الإجازة وعاد الموظف إلى حالة العمل في المحل.");
        } else {
            alert(data.detail || "تعذر إلغاء الإجازة");
        }
    } catch (err) {
        console.error(err);
    }
}

// ==========================================
// 12. PURCHASES & APPROVALS WORKFLOW
// ==========================================
let allPurchases = [];
let activePurchaseFilter = 'all';

async function loadPurchases() {
    try {
        let url = `/api/purchases?status=${activePurchaseFilter}`;
        const res = await fetch(url);
        const data = await res.json();
        
        allPurchases = data.requests || [];
        const stats = data.stats || {};

        // Update KPI Cards
        const totalEl = document.getElementById('purchase-stat-total');
        const pendingEndorseEl = document.getElementById('purchase-stat-pending-endorsement');
        const pendingGmEl = document.getElementById('purchase-stat-pending-gm');
        const approvedEl = document.getElementById('purchase-stat-approved');
        const approvedTotalEl = document.getElementById('purchase-stat-approved-total');
        const navBadge = document.getElementById('badge-nav-purchases');
        const countInd = document.getElementById('purchases-count-indicator');

        if (totalEl) totalEl.textContent = stats.total_count || 0;
        if (pendingEndorseEl) pendingEndorseEl.textContent = stats.pending_endorsement || 0;
        if (pendingGmEl) pendingGmEl.textContent = stats.pending_gm || 0;
        if (approvedEl) approvedEl.textContent = stats.approved_count || 0;
        if (approvedTotalEl) approvedTotalEl.textContent = `${(stats.approved_total_amount || 0).toFixed(2)} ر.س`;

        const pendingTotal = (stats.pending_endorsement || 0) + (stats.pending_gm || 0);
        if (navBadge) {
            navBadge.textContent = pendingTotal;
            if (pendingTotal > 0) {
                navBadge.className = 'text-xs bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full font-bold animate-pulse';
            } else {
                navBadge.className = 'text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full font-bold';
            }
        }
        if (countInd) countInd.textContent = `عرض ${allPurchases.length} طلب`;

        renderPurchasesTable();
        renderPurchasesMobileCards();
        initIcons();
    } catch (err) {
        console.error("Failed to load purchases:", err);
    }
}

function filterPurchasesByStatus(status) {
    activePurchaseFilter = status;
    document.querySelectorAll('.purchase-filter-btn').forEach(b => {
        if (b.dataset.status === status) {
            b.className = 'purchase-filter-btn px-3 py-1.5 rounded-xl text-xs font-bold bg-olive-900 text-white transition-all';
        } else {
            b.className = 'purchase-filter-btn px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-100 text-slate-600 hover:bg-slate-200 transition-all';
        }
    });
    loadPurchases();
}

function renderPurchasesTable() {
    const tbody = document.getElementById('purchases-table-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (allPurchases.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center py-10 text-slate-400">لا توجد طلبات مشتريات مسجلة</td></tr>`;
        return;
    }

    allPurchases.forEach(req => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-50 transition-colors border-b border-slate-100';

        // Badges
        let statusBadge = '';
        if (req.status === 'pending_review') {
            statusBadge = `<span class="px-2.5 py-1 rounded-full text-[10px] font-black bg-amber-100 text-amber-800 border border-amber-200 flex items-center gap-1 w-fit"><span class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping"></span> بانتظار التعميد ⏳</span>`;
        } else if (req.status === 'endorsed') {
            statusBadge = `<span class="px-2.5 py-1 rounded-full text-[10px] font-black bg-blue-100 text-blue-800 border border-blue-200 flex items-center gap-1 w-fit"><span class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span> معمّد (بانتظار ياسر) 👑</span>`;
        } else if (req.status === 'approved') {
            statusBadge = `<span class="px-2.5 py-1 rounded-full text-[10px] font-black bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1 w-fit">✓ معتمد للصرف</span>`;
        } else if (req.status === 'rejected') {
            statusBadge = `<span class="px-2.5 py-1 rounded-full text-[10px] font-black bg-rose-100 text-rose-800 border border-rose-200 flex items-center gap-1 w-fit">✕ مرفوض</span>`;
        }

        // Timeline description
        let lifecycleText = `<span class="text-slate-400">بانتظار المراجعة</span>`;
        if (req.status === 'endorsed' && req.endorsed_by_name) {
            lifecycleText = `<span class="text-blue-700 font-semibold">عمّده: ${req.endorsed_by_name}</span>`;
        } else if (req.status === 'approved' && req.approved_by_name) {
            lifecycleText = `<span class="text-emerald-700 font-bold">اعتمد: ${req.approved_by_name}</span>`;
            if (req.endorsed_by_name) {
                lifecycleText += `<span class="block text-[9px] text-slate-400">بعد تعميد ${req.endorsed_by_name}</span>`;
            }
        } else if (req.status === 'rejected' && req.rejected_by_name) {
            lifecycleText = `<span class="text-rose-700 font-semibold">رفضه: ${req.rejected_by_name}</span>`;
        }

        // Action Buttons based on User Permission
        let actionButtons = `
            <button onclick="openPurchaseActionModal(${req.id}, 'view')" title="عرض التفاصيل" class="p-1.5 rounded-lg hover:bg-slate-100 text-slate-600 transition-all cursor-pointer">
                <i data-lucide="eye" class="w-4 h-4"></i>
            </button>
        `;

        // Can Endorse: Branch Manager (Nader), Ops Manager (Faisal), GM (Yasser), or Admin
        const canEndorse = (currentUser.role === 'branch_manager' || currentUser.role === 'operations_manager' || currentUser.role === 'general_manager' || currentUser.role === 'admin') && req.status === 'pending_review';
        if (canEndorse) {
            actionButtons += `
                <button onclick="openPurchaseActionModal(${req.id}, 'endorse')" class="bg-amber-600 hover:bg-amber-700 text-white text-[11px] font-bold px-2.5 py-1 rounded-lg shadow-sm flex items-center gap-1 transition-all cursor-pointer">
                    <i data-lucide="pen-tool" class="w-3 h-3"></i>
                    <span>تعميد ✍️</span>
                </button>
            `;
        }

        // Can Approve: General Manager (Yasser) or Admin
        const canApprove = (currentUser.role === 'general_manager' || currentUser.role === 'admin') && req.status !== 'approved' && req.status !== 'rejected';
        if (canApprove) {
            actionButtons += `
                <button onclick="openPurchaseActionModal(${req.id}, 'approve')" class="bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold px-2.5 py-1 rounded-lg shadow-sm flex items-center gap-1 transition-all cursor-pointer">
                    <i data-lucide="check-check" class="w-3 h-3"></i>
                    <span>اعتماد 👑✅</span>
                </button>
            `;
        }

        // Urgency badge
        let urgencyBadge = '';
        if (req.urgency === 'عاجل جداً اليوم' || req.urgency === 'urgent') {
            urgencyBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-rose-100 text-rose-700 border border-rose-200 inline-flex items-center gap-1">عاجل جداً اليوم ⚡</span>`;
        } else {
            urgencyBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200 inline-flex items-center gap-1">عادي غداً</span>`;
        }

        tr.innerHTML = `
            <td class="py-3 px-3 font-mono font-bold text-slate-900">${req.request_number}</td>
            <td class="py-3 px-3 font-bold text-slate-800">${req.item_name}</td>
            <td class="py-3 px-3 font-bold text-slate-700">${req.quantity || '-'}</td>
            <td class="py-3 px-3">${urgencyBadge}</td>
            <td class="py-3 px-3">
                <span class="font-bold text-purple-900 block">${req.requested_by_name}</span>
                <span class="text-[10px] text-slate-400">${req.created_at ? req.created_at.split('T')[0] : ''}</span>
            </td>
            <td class="py-3 px-3">${statusBadge}</td>
            <td class="py-3 px-3">${lifecycleText}</td>
            <td class="py-3 px-3 text-center">
                <div class="flex items-center justify-center gap-1.5">${actionButtons}</div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderPurchasesMobileCards() {
    const container = document.getElementById('purchases-mobile-cards');
    if (!container) return;
    container.innerHTML = '';

    if (allPurchases.length === 0) {
        container.innerHTML = `<div class="text-center py-8 text-slate-400">لا توجد طلبات مشتريات مسجلة</div>`;
        return;
    }

    allPurchases.forEach(req => {
        const card = document.createElement('div');
        card.className = 'p-4 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3';

        let statusBadge = '';
        if (req.status === 'pending_review') {
            statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-100 text-amber-800 border border-amber-200">بانتظار التعميد ⏳</span>`;
        } else if (req.status === 'endorsed') {
            statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-blue-100 text-blue-800 border border-blue-200">معمّد (بانتظار ياسر) 👑</span>`;
        } else if (req.status === 'approved') {
            statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-emerald-100 text-emerald-800 border border-emerald-200">✓ معتمد للصرف</span>`;
        } else if (req.status === 'rejected') {
            statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-rose-100 text-rose-800 border border-rose-200">✕ مرفوض</span>`;
        }

        let urgencyBadge = '';
        if (req.urgency === 'عاجل جداً اليوم' || req.urgency === 'urgent') {
            urgencyBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-rose-100 text-rose-700 border border-rose-200">عاجل جداً اليوم ⚡</span>`;
        } else {
            urgencyBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">عادي غداً</span>`;
        }

        const canEndorse = (currentUser.role === 'branch_manager' || currentUser.role === 'operations_manager' || currentUser.role === 'general_manager' || currentUser.role === 'admin') && req.status === 'pending_review';
        const canApprove = (currentUser.role === 'general_manager' || currentUser.role === 'admin') && req.status !== 'approved' && req.status !== 'rejected';

        card.innerHTML = `
            <div class="flex items-center justify-between">
                <span class="font-mono text-xs font-black text-slate-800">${req.request_number}</span>
                ${statusBadge}
            </div>
            <div>
                <h5 class="font-bold text-slate-900 text-sm">${req.item_name}</h5>
                <div class="flex items-center gap-2 mt-1 text-xs text-slate-500">
                    <span>الكمية: <strong class="text-slate-800">${req.quantity || '-'}</strong></span>
                    <span>•</span>
                    <span>الأهمية: ${urgencyBadge}</span>
                </div>
            </div>
            <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between text-[11px]">
                <span class="text-slate-500">مقدم الطلب: <strong class="text-purple-800">${req.requested_by_name}</strong></span>
                <span class="text-slate-400">${req.created_at ? req.created_at.split('T')[0] : ''}</span>
            </div>
            <div class="flex items-center justify-end gap-2 pt-1 border-t border-slate-100">
                <button onclick="openPurchaseActionModal(${req.id}, 'view')" class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold px-3 py-1.5 rounded-xl cursor-pointer">
                    التفاصيل 🔍
                </button>
                ${canEndorse ? `
                    <button onclick="openPurchaseActionModal(${req.id}, 'endorse')" class="text-xs bg-amber-600 hover:bg-amber-700 text-white font-bold px-3 py-1.5 rounded-xl cursor-pointer">
                        تعميد ✍️
                    </button>
                ` : ''}
                ${canApprove ? `
                    <button onclick="openPurchaseActionModal(${req.id}, 'approve')" class="text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-3 py-1.5 rounded-xl cursor-pointer">
                        اعتماد نهائي 👑✅
                    </button>
                ` : ''}
            </div>
        `;
        container.appendChild(card);
    });
}

function openNewPurchaseModal() {
    const itemInput = document.getElementById('purchase-item-name');
    if (itemInput) itemInput.value = '';
    const qtyInput = document.getElementById('purchase-quantity');
    if (qtyInput) qtyInput.value = '';
    const reasonInput = document.getElementById('purchase-reason');
    if (reasonInput) reasonInput.value = '';
    const urgencySelect = document.getElementById('purchase-urgency');
    if (urgencySelect) urgencySelect.selectedIndex = 0;

    openModal('modal-new-purchase');
}

async function handleCreatePurchase(event) {
    if (event) event.preventDefault();

    const itemName = document.getElementById('purchase-item-name')?.value.trim();
    const quantity = document.getElementById('purchase-quantity')?.value.trim() || '-';
    const urgency = document.getElementById('purchase-urgency')?.value || 'عاجل جداً اليوم';
    const reason = document.getElementById('purchase-reason')?.value.trim() || '';

    if (!itemName) {
        alert("يرجى إدخال اسم الصنف أو الغرض المطلوب شراؤه");
        return;
    }

    const payload = {
        item_name: itemName,
        category: "مشتريات عامة",
        quantity: quantity,
        estimated_amount: 0.0,
        urgency: urgency,
        reason: reason,
        requested_by_name: currentUser ? currentUser.name : "موظف المحل",
        requested_by_role: currentUser ? currentUser.role : "staff",
        requested_by_id: currentUser ? currentUser.id : null
    };

    try {
        const res = await fetch('/api/purchases', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-new-purchase');
            loadPurchases();
            alert(`✓ ${data.message}`);
        } else {
            alert(data.detail || "حدث خطأ أثناء حفظ طلب الشراء");
        }
    } catch (err) {
        console.error("Create purchase error:", err);
        alert("تعذر الاتصال بالخادم");
    }
}

function openPurchaseActionModal(requestId, defaultAction = 'view') {
    const req = allPurchases.find(p => p.id === requestId);
    if (!req) return;

    document.getElementById('action-modal-request-id').value = req.id;
    document.getElementById('action-modal-req-number').textContent = req.request_number;
    document.getElementById('action-modal-item-name').textContent = req.item_name;
    document.getElementById('action-modal-quantity').textContent = req.quantity || '-';
    const amountEl = document.getElementById('action-modal-amount');
    if (amountEl) {
        amountEl.textContent = `${parseFloat(req.estimated_amount || 0).toFixed(2)} ر.س`;
    }
    document.getElementById('action-modal-requester').textContent = req.requested_by_name;

    const urgencyEl = document.getElementById('action-modal-urgency-badge');
    if (urgencyEl) {
        if (req.urgency === 'عاجل جداً اليوم' || req.urgency === 'urgent') {
            urgencyEl.textContent = 'عاجل جداً اليوم ⚡';
            urgencyEl.className = 'px-2 py-0.5 rounded-full text-[10px] font-black bg-rose-100 text-rose-700 border border-rose-200';
        } else {
            urgencyEl.textContent = 'عادي غداً';
            urgencyEl.className = 'px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200';
        }
    }

    const reasonBox = document.getElementById('action-modal-reason-box');
    const reasonText = document.getElementById('action-modal-reason');
    if (req.reason) {
        reasonBox.classList.remove('hidden');
        reasonText.textContent = req.reason;
    } else {
        reasonBox.classList.add('hidden');
    }

    // Timeline updates
    document.getElementById('timeline-requester-text').textContent = req.requested_by_name;
    document.getElementById('timeline-created-at').textContent = req.created_at ? req.created_at.replace('T', ' ') : '-';

    const endStatusEl = document.getElementById('timeline-endorsement-status');
    const endNotesEl = document.getElementById('timeline-endorsement-notes');
    const step2Icon = document.getElementById('timeline-step-2-icon');
    if (req.endorsed_by_name) {
        endStatusEl.innerHTML = `<span class="text-blue-700 font-bold">تم التعميد بواسطة: ${req.endorsed_by_name}</span> (${req.endorsed_at ? req.endorsed_at.replace('T', ' ') : ''})`;
        endNotesEl.textContent = req.endorsement_notes ? `ملاحظات: ${req.endorsement_notes}` : '';
        step2Icon.className = 'w-5 h-5 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs shrink-0';
    } else {
        endStatusEl.textContent = 'بانتظار مراجعة وتعميد مدير الفرع (نادر) أو مدير التشغيل (فيصل)';
        endNotesEl.textContent = '';
        step2Icon.className = 'w-5 h-5 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center font-bold text-xs shrink-0';
    }

    const gmStatusEl = document.getElementById('timeline-gm-status');
    const gmNotesEl = document.getElementById('timeline-gm-notes');
    const step3Icon = document.getElementById('timeline-step-3-icon');
    if (req.approved_by_name) {
        gmStatusEl.innerHTML = `<span class="text-emerald-700 font-bold">تم الاعتماد النهائي للصرف بواسطة: ${req.approved_by_name} ✅</span> (${req.approved_at ? req.approved_at.replace('T', ' ') : ''})`;
        gmNotesEl.textContent = req.gm_notes ? `ملاحظات المدير العام: ${req.gm_notes}` : '';
        step3Icon.className = 'w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs shrink-0';
    } else if (req.status === 'rejected') {
        gmStatusEl.innerHTML = `<span class="text-rose-700 font-bold">تم رفض الطلب بواسطة: ${req.rejected_by_name || 'الإدارة'}</span>`;
        gmNotesEl.textContent = req.rejection_reason ? `سبب الرفض: ${req.rejection_reason}` : '';
        step3Icon.className = 'w-5 h-5 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center font-bold text-xs shrink-0';
    } else {
        gmStatusEl.textContent = 'بانتظار موافقة المدير العام (ياسر) النهائية للصرف';
        gmNotesEl.textContent = '';
        step3Icon.className = 'w-5 h-5 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center font-bold text-xs shrink-0';
    }

    // Clear notes input
    document.getElementById('action-modal-notes-input').value = '';

    // Action Controls visibility based on User Role & Status
    const btnEndorse = document.getElementById('btn-action-endorse');
    const btnApprove = document.getElementById('btn-action-approve');
    const gmExpenseOption = document.getElementById('gm-expense-record-option');

    const canEndorse = (currentUser.role === 'branch_manager' || currentUser.role === 'operations_manager' || currentUser.role === 'general_manager' || currentUser.role === 'admin') && req.status === 'pending_review';
    const canApprove = (currentUser.role === 'general_manager' || currentUser.role === 'admin') && req.status !== 'approved' && req.status !== 'rejected';

    if (canEndorse) {
        btnEndorse.classList.remove('hidden');
    } else {
        btnEndorse.classList.add('hidden');
    }

    if (canApprove) {
        btnApprove.classList.remove('hidden');
        gmExpenseOption.classList.remove('hidden');
    } else {
        btnApprove.classList.add('hidden');
        gmExpenseOption.classList.add('hidden');
    }

    openModal('modal-purchase-action');
}

async function submitPurchaseActionDecision(decision) {
    const requestId = document.getElementById('action-modal-request-id')?.value;
    const notes = document.getElementById('action-modal-notes-input')?.value.trim();

    if (!requestId) return;

    if (decision === 'reject') {
        const reason = notes || prompt("يرجى كتابة سبب رفض طلب الشراء:");
        if (!reason) return;

        try {
            const res = await fetch(`/api/purchases/${requestId}/reject`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    rejected_by_name: currentUser ? currentUser.name : "الإدارة",
                    rejection_reason: reason
                })
            });
            const data = await res.json();
            if (data.success) {
                closeModal('modal-purchase-action');
                loadPurchases();
                alert(`✓ ${data.message}`);
            }
        } catch (e) {
            console.error(e);
        }
        return;
    }

    if (decision === 'endorse') {
        try {
            const res = await fetch(`/api/purchases/${requestId}/endorse`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    endorsed_by_name: currentUser ? currentUser.name : "المدير",
                    endorsed_by_role: currentUser ? currentUser.role : "manager",
                    endorsed_by_id: currentUser ? currentUser.id : null,
                    endorsement_notes: notes || "تم التعميد والموافقة المبدئية"
                })
            });
            const data = await res.json();
            if (data.success) {
                closeModal('modal-purchase-action');
                loadPurchases();
                alert(`✓ ${data.message}`);
            } else {
                alert(data.detail || "حدث خطأ");
            }
        } catch (e) {
            console.error(e);
        }
        return;
    }

    if (decision === 'approve') {
        const recordExpense = document.getElementById('action-record-expense-checkbox')?.checked || false;
        try {
            const res = await fetch(`/api/purchases/${requestId}/approve`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    approved_by_name: currentUser ? currentUser.name : "ياسر (المدير العام)",
                    approved_by_id: currentUser ? currentUser.id : null,
                    gm_notes: notes || "معتمد نهائياً للصرف",
                    record_expense: recordExpense,
                    payment_method: "cash"
                })
            });
            const data = await res.json();
            if (data.success) {
                closeModal('modal-purchase-action');
                loadPurchases();
                if (recordExpense && typeof loadExpenses === 'function') {
                    loadExpenses();
                }
                alert(`✓ ${data.message}`);
            } else {
                alert(data.detail || "حدث خطأ");
            }
        } catch (e) {
            console.error(e);
        }
        return;
    }
}

// ==========================================
// 14. NABT CREATIVE PROJECTS TASKS (مهام مشاريع نبت الإبداعية)
// ==========================================
let activeCreativeTaskFilter = 'all';
let allCreativeTasks = [];

async function loadCreativeTasks() {
    try {
        let url = '/api/creative-tasks';
        if (activeCreativeTaskFilter && activeCreativeTaskFilter !== 'all') {
            url += `?status=${activeCreativeTaskFilter}`;
        }
        const res = await fetch(url);
        const data = await res.json();
        allCreativeTasks = data.tasks || [];
        const stats = data.stats || { total: 0, pending: 0, in_progress: 0, completed: 0 };

        // Update KPI counters
        const statTotal = document.getElementById('crt-stat-total');
        if (statTotal) statTotal.textContent = stats.total;
        const statPending = document.getElementById('crt-stat-pending');
        if (statPending) statPending.textContent = stats.pending;
        const statInprogress = document.getElementById('crt-stat-inprogress');
        if (statInprogress) statInprogress.textContent = stats.in_progress;
        const statCompleted = document.getElementById('crt-stat-completed');
        if (statCompleted) statCompleted.textContent = stats.completed;

        // Update Nav Badge
        const navBadge = document.getElementById('badge-nav-creative-tasks');
        if (navBadge) {
            const activeCount = (stats.pending || 0) + (stats.in_progress || 0);
            navBadge.textContent = activeCount;
        }

        const tbody = document.getElementById('creative-tasks-table-tbody');
        const grid = document.getElementById('creative-tasks-grid');
        const emptyState = document.getElementById('creative-tasks-empty');

        if (tbody) tbody.innerHTML = '';
        if (grid) grid.innerHTML = '';

        if (allCreativeTasks.length === 0) {
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        } else {
            if (emptyState) emptyState.classList.add('hidden');
        }

        allCreativeTasks.forEach(task => {
            let statusBadge = '';
            if (task.status === 'pending') {
                statusBadge = '<span class="text-[11px] font-bold bg-amber-50 text-amber-800 border border-amber-200 px-2.5 py-0.5 rounded-full inline-flex items-center gap-1"><span>⏳</span><span>بانتظار البدء</span></span>';
            } else if (task.status === 'in_progress') {
                statusBadge = '<span class="text-[11px] font-bold bg-purple-50 text-purple-800 border border-purple-200 px-2.5 py-0.5 rounded-full inline-flex items-center gap-1"><span>🎨</span><span>قيد التنفيذ</span></span>';
            } else if (task.status === 'completed') {
                statusBadge = '<span class="text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 px-2.5 py-0.5 rounded-full inline-flex items-center gap-1"><span>✅</span><span>مكتملة بنجاح</span></span>';
            } else {
                statusBadge = '<span class="text-[11px] font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded-full">ملغية ❌</span>';
            }

            // WhatsApp Message Generator
            const timePart = task.due_time ? ` (${task.due_time})` : '';
            const waText = `🎨 مهمة جديدة ضمن مشاريع نبت الإبداعية\nمرحباً ${task.assigned_to_name} ✨\nتفاصيل الطلب: ${task.details}\nموعد التسليم: ${task.due_date}${timePart}\nمن: ${task.created_by_name} 🌸`;
            let cleanPhone = (task.assigned_to_phone || task.assignee_phone || '').replace('+', '').replace(/\s+/g, '');
            if (cleanPhone.startsWith('05')) cleanPhone = '966' + cleanPhone.substring(1);
            const waUrl = cleanPhone ? `https://wa.me/${cleanPhone}?text=${encodeURIComponent(waText)}` : '';

            // 1. Render Table Row (Desktop)
            if (tbody) {
                const tr = document.createElement('tr');
                tr.className = 'hover:bg-slate-50/80 transition-colors text-xs border-b border-slate-100';

                let actionBtns = '';
                if (task.status === 'pending') {
                    actionBtns = `
                        <button onclick="updateCreativeTaskStatus(${task.id}, 'in_progress')" class="bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 py-1 px-2.5 rounded-lg text-xs font-bold transition-all inline-flex items-center gap-1 cursor-pointer">
                            <i data-lucide="play" class="w-3.5 h-3.5"></i>
                            <span>بدء التنفيذ</span>
                        </button>
                    `;
                } else if (task.status === 'in_progress') {
                    actionBtns = `
                        <button onclick="updateCreativeTaskStatus(${task.id}, 'completed')" class="bg-emerald-600 hover:bg-emerald-700 text-white py-1 px-3 rounded-lg text-xs font-bold transition-all inline-flex items-center gap-1 shadow-xs cursor-pointer">
                            <i data-lucide="check" class="w-3.5 h-3.5"></i>
                            <span>إكمال المهمة ✅</span>
                        </button>
                    `;
                } else {
                    actionBtns = `
                        <span class="text-[11px] text-emerald-700 font-bold bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-lg inline-block">
                            منجزة 🌸
                        </span>
                    `;
                }

                tr.innerHTML = `
                    <td class="py-3.5 px-3 font-mono font-black text-purple-700">#${task.task_number}</td>
                    <td class="py-3.5 px-3">
                        <strong class="text-slate-800 block text-xs">${escapeHtml(task.assigned_to_name)}</strong>
                        <span class="text-[10px] text-slate-400 font-mono">${escapeHtml(task.assigned_to_phone || '')}</span>
                    </td>
                    <td class="py-3.5 px-3 max-w-[320px]">
                        <p class="text-slate-800 font-bold text-xs leading-relaxed whitespace-pre-line">${escapeHtml(task.details)}</p>
                        ${task.notes ? `<span class="text-[10px] text-slate-400 block mt-0.5">ملاحظة: ${escapeHtml(task.notes)}</span>` : ''}
                    </td>
                    <td class="py-3.5 px-3">
                        <span class="font-bold text-slate-800 block">${task.due_date}</span>
                        ${task.due_time ? `<span class="text-[10px] text-terracotta-700 font-semibold">${escapeHtml(task.due_time)}</span>` : ''}
                    </td>
                    <td class="py-3.5 px-3 text-slate-600 font-medium">${escapeHtml(task.created_by_name || 'الفريق')}</td>
                    <td class="py-3.5 px-3">${statusBadge}</td>
                    <td class="py-3.5 px-3 text-center">
                        <div class="inline-flex items-center gap-1.5">${actionBtns}</div>
                    </td>
                    <td class="py-3.5 px-3 text-center">
                        <div class="inline-flex items-center gap-1">
                            ${waUrl ? `
                                <button onclick="window.open('${waUrl}', '_blank')" title="إرسال عبر الواتساب" class="p-1.5 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-emerald-700 rounded-lg transition-all cursor-pointer">
                                    <i data-lucide="message-circle" class="w-4 h-4"></i>
                                </button>
                            ` : ''}
                            <button onclick="deleteCreativeTask(${task.id})" title="حذف المهمة" class="p-1.5 bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-600 rounded-lg transition-all cursor-pointer">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            }

            // 2. Render Card (Mobile)
            if (grid) {
                const card = document.createElement('div');
                card.className = 'bg-white rounded-2xl border border-slate-200/90 shadow-sm p-4 space-y-3';

                card.innerHTML = `
                    <div class="flex items-center justify-between">
                        <span class="font-mono text-xs font-black text-purple-700 bg-purple-50 px-2 py-0.5 rounded-md border border-purple-200/80">#${task.task_number}</span>
                        ${statusBadge}
                    </div>

                    <div>
                        <h4 class="text-xs font-bold text-slate-900 leading-relaxed whitespace-pre-line bg-slate-50 p-2.5 rounded-xl border border-slate-100">${escapeHtml(task.details)}</h4>
                        ${task.notes ? `<p class="text-[11px] text-slate-500 mt-1 italic">ملاحظة: ${escapeHtml(task.notes)}</p>` : ''}
                    </div>

                    <div class="grid grid-cols-2 gap-2 text-[11px] bg-cream-50/60 p-2 rounded-xl border border-cream-200/60">
                        <div>
                            <span class="text-slate-400 block text-[10px]">المُسند إليه:</span>
                            <strong class="text-slate-800 font-bold flex items-center gap-1 mt-0.5">
                                <i data-lucide="user" class="w-3 h-3 text-purple-600"></i>
                                <span>${escapeHtml(task.assigned_to_name)}</span>
                            </strong>
                        </div>
                        <div>
                            <span class="text-slate-400 block text-[10px]">مرسل الطلب:</span>
                            <span class="text-slate-700 font-semibold block mt-0.5">${escapeHtml(task.created_by_name || 'الفريق')}</span>
                        </div>
                    </div>

                    <div class="flex items-center justify-between text-[11px] text-slate-600">
                        <span class="flex items-center gap-1 font-bold text-terracotta-700">
                            <i data-lucide="calendar" class="w-3.5 h-3.5"></i>
                            <span>موعد التسليم: ${task.due_date}</span>
                        </span>
                        ${task.due_time ? `<span class="bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md text-[10px] font-semibold">${escapeHtml(task.due_time)}</span>` : ''}
                    </div>

                    <div class="pt-2.5 border-t border-slate-100 flex items-center justify-between gap-1.5 text-xs">
                        <div class="flex items-center gap-1.5 flex-1">
                            ${task.status === 'pending' ? `
                                <button onclick="updateCreativeTaskStatus(${task.id}, 'in_progress')" class="flex-1 bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 py-1.5 px-2 rounded-xl text-[11px] font-bold transition-all flex items-center justify-center gap-1 cursor-pointer">
                                    <i data-lucide="play" class="w-3 h-3"></i>
                                    <span>بدء التنفيذ</span>
                                </button>
                            ` : ''}
                            ${task.status === 'in_progress' ? `
                                <button onclick="updateCreativeTaskStatus(${task.id}, 'completed')" class="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white py-1.5 px-2 rounded-xl text-[11px] font-bold transition-all flex items-center justify-center gap-1 shadow-xs cursor-pointer">
                                    <i data-lucide="check" class="w-3.5 h-3.5"></i>
                                    <span>إكمال المهمة ✅</span>
                                </button>
                            ` : ''}
                            ${task.status === 'completed' ? `
                                <span class="flex-1 text-[11px] text-emerald-700 font-bold bg-emerald-50 border border-emerald-200 py-1.5 text-center rounded-xl">
                                    مكتملة بنجاح 🎉
                                </span>
                            ` : ''}
                        </div>

                        ${waUrl ? `
                            <button onclick="window.open('${waUrl}', '_blank')" title="إرسال عبر الواتساب" class="p-2 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-emerald-700 rounded-xl transition-all cursor-pointer">
                                <i data-lucide="message-circle" class="w-4 h-4"></i>
                            </button>
                        ` : ''}

                        <button onclick="deleteCreativeTask(${task.id})" title="حذف المهمة" class="p-2 bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-600 rounded-xl transition-all cursor-pointer">
                            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                        </button>
                    </div>
                `;
                grid.appendChild(card);
            }
        });

        initIcons();
    } catch (err) {
        console.error("Failed to load creative tasks:", err);
    }
}

function filterCreativeTasks(status) {
    activeCreativeTaskFilter = status;
    document.querySelectorAll('.crt-filter-btn').forEach(btn => {
        if (btn.getAttribute('data-status') === status) {
            btn.className = 'crt-filter-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-purple-700 text-white shadow-xs';
        } else {
            btn.className = 'crt-filter-btn px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 text-slate-600 hover:bg-slate-200';
        }
    });
    loadCreativeTasks();
}

async function openNewCreativeTaskModal() {
    openModal('modal-new-creative-task');

    // Default due date = tomorrow
    const dateInput = document.getElementById('crt-due-date-input');
    if (dateInput) {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        dateInput.value = getLocalDateString(tomorrow);
    }
    const detailsInput = document.getElementById('crt-details-input');
    if (detailsInput) detailsInput.value = '';
    const timeInput = document.getElementById('crt-due-time-input');
    if (timeInput) timeInput.value = '';
    const notesInput = document.getElementById('crt-notes-input');
    if (notesInput) notesInput.value = '';

    initIcons();

    const select = document.getElementById('crt-assigned-to-select');
    if (select) {
        select.innerHTML = '<option value="">جاري تحميل أعضاء الفريق...</option>';
        try {
            const res = await fetch('/api/employees');
            const employees = await res.json();
            if (Array.isArray(employees) && employees.length > 0) {
                select.innerHTML = '<option value="">-- اختر الموظف المُسند إليه الطلب --</option>';
                employees.forEach(e => {
                    select.innerHTML += `<option value="${e.id}">${e.name} (${e.specialty || e.role})</option>`;
                });
            } else {
                select.innerHTML = `
                    <option value="">-- اختر الموظف المُسند إليه الطلب --</option>
                    <option value="1">ياسر (المدير العام)</option>
                    <option value="2">فيصل (مدير تشغيلي)</option>
                    <option value="3">نادر (مدير فرع)</option>
                    <option value="4">عمر (منسق ورد)</option>
                    <option value="5">ريكو (منسق ورد)</option>
                `;
            }
        } catch (e) {
            console.error("Failed to load employees for task modal:", e);
            select.innerHTML = `
                <option value="">-- اختر الموظف المُسند إليه الطلب --</option>
                <option value="1">ياسر (المدير العام)</option>
                <option value="2">فيصل (مدير تشغيلي)</option>
                <option value="3">نادر (مدير فرع)</option>
                <option value="4">عمر (منسق ورد)</option>
                <option value="5">ريكو (منسق ورد)</option>
            `;
        }
    }
}

async function handleCreateCreativeTask(event) {
    event.preventDefault();
    const assignedToId = parseInt(document.getElementById('crt-assigned-to-select').value);
    const details = document.getElementById('crt-details-input').value.trim();
    const dueDate = document.getElementById('crt-due-date-input').value;
    const dueTime = document.getElementById('crt-due-time-input').value.trim();
    const notes = document.getElementById('crt-notes-input').value.trim();

    if (!assignedToId) {
        alert("يرجى اختيار الموظف المُسند إليه الطلب.");
        return;
    }
    if (!details) {
        alert("يرجى كتابة تفاصيل الطلب الإبداعي.");
        return;
    }
    if (!dueDate) {
        alert("يرجى تحديد موعد التسليم.");
        return;
    }

    const payload = {
        assigned_to_id: assignedToId,
        details: details,
        due_date: dueDate,
        due_time: dueTime || null,
        notes: notes || null,
        created_by_name: currentUser ? currentUser.name : "عضو الفريق",
        created_by_id: currentUser ? currentUser.id : null
    };

    try {
        const res = await fetch('/api/creative-tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeModal('modal-new-creative-task');
            loadCreativeTasks();
            if (data.wa_url && confirm(`✓ ${data.message}\n\nهل ترغب في فتح محادثة الواتساب لإرسال تفاصيل المهمة إلى (${data.assignee_name}) مباشرة الآن؟`)) {
                window.open(data.wa_url, '_blank');
            } else {
                alert(`✓ ${data.message}`);
            }
        } else {
            alert(data.detail || "حدث خطأ أثناء حفظ المهمة الإبداعية.");
        }
    } catch (err) {
        console.error("Create creative task failed:", err);
        alert("حدث خطأ أثناء إرسال المهمة.");
    }
}

async function updateCreativeTaskStatus(taskId, newStatus) {
    try {
        const res = await fetch(`/api/creative-tasks/${taskId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        const data = await res.json();
        if (data.success) {
            loadCreativeTasks();
        } else {
            alert(data.detail || "حدث خطأ أثناء تحديث الحالة.");
        }
    } catch (err) {
        console.error("Update task status failed:", err);
    }
}

async function deleteCreativeTask(taskId) {
    if (!confirm("هل أنت متأكد من حذف هذه المهمة الإبداعية؟")) return;
    try {
        const res = await fetch(`/api/creative-tasks/${taskId}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
            loadCreativeTasks();
        }
    } catch (err) {
        console.error("Delete task failed:", err);
    }
}



