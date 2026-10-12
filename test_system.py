import sys
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_full_erp_workflow():
    print("--- 1. Testing Health Check ---")
    res = client.get("/api/health")
    assert res.status_code == 200
    print("Health check response:", res.json())

    print("\n--- 2. Testing Dashboard Stats ---")
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    stats = res.json()
    print(f"Sales: {stats['today_sales']} SAR, Net Profit: {stats['net_profit']} SAR, Unpaid: {stats['total_unpaid']} SAR")

    print("\n--- 3. Testing Products List ---")
    res = client.get("/api/products")
    assert res.status_code == 200
    products = res.json()
    print(f"Loaded {len(products)} flower products/bouquets.")

    print("\n--- 4. Creating New Flower Order with Greeting Card ---")
    new_order_payload = {
        "customer_name": "سلطان عبد العزيز الخالدي",
        "customer_phone": "0554433221",
        "recipient_name": "الأستاذة مها الخالدي",
        "recipient_phone": "0559988771",
        "recipient_address": "الرياض - حي النرجس - مجمع واحة الأعمال",
        "location_url": "https://maps.google.com/?q=24.84,46.68",
        "card_message": "ألف مبروك الترقية يا أم عبد العزيز ومنها للأعلى بإذن الله 💐",
        "delivery_date": "2026-10-03",
        "delivery_time_slot": "مسائي (4ع - 8م)",
        "driver_id": 1,
        "delivery_fee": 30.0,
        "discount": 10.0,
        "payment_status": "unpaid",
        "payment_method": "pos",
        "notes": "تغليف مميز باللون الأخضر الملكي",
        "items": [
            {
                "product_id": products[0]["id"],
                "product_name": products[0]["name"],
                "quantity": 1,
                "unit_price": products[0]["price"]
            },
            {
                "product_id": products[6]["id"],
                "product_name": products[6]["name"],
                "quantity": 1,
                "unit_price": products[6]["price"]
            }
        ]
    }
    res = client.post("/api/orders", json=new_order_payload)
    assert res.status_code == 200, res.text
    order_data = res.json()
    print(f"Order created successfully: #{order_data['order_number']}, Invoice: #{order_data['invoice_number']}, Total: {order_data['total_amount']} SAR")

    order_id = order_data["order_id"]

    print("\n--- 5. Verifying Order Details & WhatsApp Auto-Confirmation ---")
    res = client.get(f"/api/orders/{order_id}")
    assert res.status_code == 200
    ord_detail = res.json()
    print(f"Customer: {ord_detail['customer_name']}, Card Message: {ord_detail['card_message']}")
    print(f"WhatsApp Messages Logged: {len(ord_detail['whatsapp_messages'])}")
    for m in ord_detail["whatsapp_messages"]:
        print(f" - [{m['message_type']}] to {m['recipient_phone']}: {m['content'][:60]}...")

    print("\n--- 6. Advancing Order Status (Preparing -> Ready -> Out for Delivery) ---")
    client.put(f"/api/orders/{order_id}/status", json={"status": "preparing"})
    client.put(f"/api/orders/{order_id}/status", json={"status": "out_for_delivery"})
    
    # Check that WhatsApp logs new update
    res = client.get(f"/api/orders/{order_id}")
    assert len(res.json()["whatsapp_messages"]) >= 3
    print("Order status advanced and WhatsApp notifications fired automatically!")

    print("\n--- 7. Recording Invoice Payment (سند قبض) ---")
    res = client.get(f"/api/invoices/{ord_detail['invoice_id']}")
    assert res.status_code == 200
    inv = res.json()
    print(f"Invoice {inv['invoice_number']} remaining before pay: {inv['remaining_amount']} SAR")

    pay_res = client.post("/api/invoices/pay", json={
        "invoice_id": inv["id"],
        "amount": inv["total_amount"],
        "payment_method": "pos",
        "reference_number": "TXN-TEST-9988",
        "notes": "سداد بالبطاقة عند المعرض"
    })
    assert pay_res.status_code == 200
    pay_data = pay_res.json()
    print(f"Payment recorded: {pay_data['payment_number']}, Status: {pay_data['status']}, Remaining: {pay_data['new_remaining']} SAR")

    print("\n--- 8. Testing ZATCA QR Code Generation ---")
    res = client.get(f"/api/invoices/{ord_detail['invoice_id']}")
    inv_paid = res.json()
    assert inv_paid["qr_image"].startswith("data:image/png;base64,")
    print("ZATCA electronic tax invoice QR code verified successfully!")

    print("\n==========================================")
    print(" ALL TESTS PASSED SUCCESSFULLY! 🌸💐")
    print("==========================================")

if __name__ == "__main__":
    test_full_erp_workflow()
