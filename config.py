import os
from pathlib import Path
from dotenv import load_dotenv

# تحميل المتغيرات من ملف .env
load_dotenv()

# المسار الأساسي للمشروع
BASE_DIR = Path(__file__).resolve().parent

# جلب الإعدادات مع قيم افتراضية للأمان
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "smart_invoice.db")).strip()
EXCEL_EXPORT_PATH = os.getenv("EXCEL_EXPORT_PATH", str(BASE_DIR / "exports")).strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

# التأكد من وجود مجلد التصدير
os.makedirs(EXCEL_EXPORT_PATH, exist_ok=True)

# التحقق من وجود المتغيرات الأساسية
def validate_config():
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    
    if missing:
        raise ValueError(f"CRITICAL: Missing environment variables in .env: {', '.join(missing)}")
