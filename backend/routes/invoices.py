from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db
from datetime import datetime, date
import base64
import io
import qrcode

router = APIRouter(prefix="/api/invoices", tags=["Invoices & Accounting"])

class PaymentCreateSchema(BaseModel):
    invoice_id: int
    amount: float
    payment_method: str = "pos" # cash, pos, transfer, stc_pay, online
    reference_number: Optional[str] = None
    notes: Optional[str] = None

def generate_zatca_tlv_qr(seller_name: str, vat_no: str, timestamp: str, total_amount: str, tax_amount: str) -> str:
    """Encodes ZATCA standard TLV (Tag-Length-Value) base64 string"""
    def to_tlv(tag: int, value: str) -> bytes:
        val_bytes = value.encode('utf-8')
        length = len(val_bytes)
        return bytes([tag, length]) + val_bytes

    tlv_data = (
        to_tlv(1, seller_name) +
        to_tlv(2, vat_no) +
        to_tlv(3, timestamp) +
        to_tlv(4, total_amount) +
        to_tlv(5, tax_amount)
    )
    b64_qr = base64.b64encode(tlv_data).decode('utf-8')
    
    # Generate QR image as base64 data URL
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data(b64_qr)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"

@router.get("")
def get_invoices(status: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()

    query = """
    SELECT inv.*, o.order_number, o.customer_phone, o.recipient_name
    FROM invoices inv
    LEFT JOIN orders o ON inv.order_id = o.id
    WHERE 1=1
    """
    params = []
    if status and status != "all":
        query += " AND inv.status = ?"
        params.append(status)

    query += " ORDER BY inv.id DESC"
    cursor.execute(query, params)
    invoices = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return invoices

@router.get("/{invoice_id}")
def get_invoice_detail(invoice_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT inv.*, o.order_number, o.customer_phone, o.recipient_name, o.recipient_phone, o.recipient_address,
           o.card_message, o.delivery_date, o.delivery_time_slot, o.delivery_fee, o.discount, d.name as driver_name
    FROM invoices inv
    LEFT JOIN orders o ON inv.order_id = o.id
    LEFT JOIN drivers d ON o.driver_id = d.id
    WHERE inv.id = ?
    """, (invoice_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = dict(row)

    # Fetch order items
    if invoice["order_id"]:
        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (invoice["order_id"],))
        invoice["items"] = [dict(r) for r in cursor.fetchall()]
    else:
        invoice["items"] = []

    # Fetch payments history
    cursor.execute("SELECT * FROM payments WHERE invoice_id = ? ORDER BY id DESC", (invoice_id,))
    invoice["payments"] = [dict(r) for r in cursor.fetchall()]

    # Generate or return ZATCA QR code
    timestamp = invoice["created_at"] or datetime.now().isoformat()
    invoice["qr_image"] = generate_zatca_tlv_qr(
        seller_name="نبت للزهور والمناسبات",
        vat_no="300987654300003",
        timestamp=str(timestamp),
        total_amount=f"{invoice['total_amount']:.2f}",
        tax_amount=f"{invoice['tax_amount']:.2f}"
    )

    conn.close()
    return invoice

@router.post("/pay")
def record_payment(payload: PaymentCreateSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM invoices WHERE id = ?", (payload.invoice_id,))
    invoice = cursor.fetchone()
    if not invoice:
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found")

    new_paid = round(invoice["paid_amount"] + payload.amount, 2)
    new_remaining = round(max(0.0, invoice["total_amount"] - new_paid), 2)
    
    new_status = "paid" if new_remaining <= 0 else "partial"

    # Insert payment record with safe unique number
    cursor.execute("SELECT COALESCE(MAX(id), 0) FROM payments")
    p_count = cursor.fetchone()[0] + 1
    payment_number = f"PAY-{p_count:05d}"

    cursor.execute("""
    INSERT INTO payments (payment_number, invoice_id, amount, payment_method, reference_number, notes)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (payment_number, payload.invoice_id, payload.amount, payload.payment_method, payload.reference_number, payload.notes))

    # Update invoice
    cursor.execute("""
    UPDATE invoices
    SET paid_amount = ?, remaining_amount = ?, status = ?, payment_method = ?
    WHERE id = ?
    """, (new_paid, new_remaining, new_status, payload.payment_method, payload.invoice_id))

    # Sync with associated order
    if invoice["order_id"]:
        cursor.execute("""
        UPDATE orders
        SET payment_status = ?, payment_method = ?
        WHERE id = ?
        """, (new_status, payload.payment_method, invoice["order_id"]))

    # Also log receipt WhatsApp message
    if invoice["customer_name"]:
        cursor.execute("SELECT customer_phone, order_number FROM orders WHERE id = ?", (invoice["order_id"],))
        ord_info = cursor.fetchone()
        if ord_info:
            receipt_msg = (
                f"سند قبض إلكتروني - نبت للزهور 🌸\n"
                f"تم استلام دفعة مالية بمبلغ: {payload.amount} ر.س\n"
                f"رقم الفاتورة: {invoice['invoice_number']}\n"
                f"المبلغ المتبقي: {new_remaining} ر.س\n"
                f"حالة الفاتورة: {'مسددة بالكامل' if new_remaining == 0 else 'مسددة جزئياً'}\n"
                f"شكراً لتعاملكم معنا ✨"
            )
            cursor.execute("""
            INSERT INTO whatsapp_messages (recipient_phone, recipient_name, direction, message_type, content, status, related_order_id)
            VALUES (?, ?, 'outbound', 'order_update', ?, 'delivered', ?)
            """, (ord_info['customer_phone'], invoice['customer_name'], receipt_msg, invoice['order_id']))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "payment_number": payment_number,
        "new_paid": new_paid,
        "new_remaining": new_remaining,
        "status": new_status
    }
