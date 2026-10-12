#!/usr/bin/env python3
import os
import sys

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print("\n" + "="*60)
    print(" 🌸 نظام نبت المتكامل لإدارة محلات الورد والزهور (Nabt ERP)")
    print(f" 🚀 جاري تشغيل السيستم على: http://localhost:{port}")
    print(f" 📱 للفتح من الجوال والشبكة المحلية: http://0.0.0.0:{port}")
    uvicorn.run(
        "backend.main:app", 
        host=host, 
        port=port, 
        reload=True,
        reload_dirs=[BACKEND_DIR],
        reload_excludes=["*.db", "*.db-wal", "*.db-shm", "*.sqlite*", "static/*", "uploads/*"]
    )
