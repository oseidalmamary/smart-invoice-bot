from datetime import date
from typing import Optional
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL
from schemas import ExtractedTransaction

# تهيئة عميل Google GenAI الرسمي
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = f"""
أنت مساعد مالي ومحلل فواتير وإيصالات ورسائل بنكية فائق الدقة.
مهمتك هي قراءة المدخلات (سواء كانت صورة فاتورة، إيصال، نص رسالة بنكية، أو نص مكتوب بالعامية السعودية أو العربية أو الإنجليزية) واستخراج البيانات بدقة متناهية.

قواعد صارمة:
1. تاريخ العملية (date): استخرج التاريخ بصيغة YYYY-MM-DD. إذا لم تجد تاريخاً مذكوراً بشكل صريح، استخدم تاريخ اليوم الحالي وهو: {date.today().isoformat()}.
2. إجمالي المبلغ (total_amount): استخرج القيمة الرقمية النهائية المدفوعة أو المحولة كعدد عشري موجب دائماً (float).
3. نوع العملية (transaction_type):
   - حددها EXPENSE إذا كانت شراء، خصم، سداد فاتورة، تحويل صادر، رسوم، أو مصروف.
   - حددها INCOME إذا كانت راتب، إيداع، تحويل وارد، أو استرداد أموال (Refund).
4. التصنيف (category): اختر تصنيفاً مناسباً ومختصراً مثل: Food, Fuel, Office, Utilities, Electronics, Groceries, Healthcare, Entertainment, Salary.
5. المتجر (merchant_name): اسم المحل أو المتجر أو الخدمة أو الشخص.
6. ملخص الأصناف (items_summary): ملخص موجز بالبنود المشتراة.
7. العملة (currency): SAR إذا كانت داخل السعودية أو لم تُذكر، وإلا فاستخرج رمز العملة المذكور.
"""


def extract_from_text(text: str) -> ExtractedTransaction:
    """استخراج المعاملة المالية من نص رسالة أو نص بنكي"""
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=ExtractedTransaction,
            temperature=0.1
        )
    )
    return response.parsed


def extract_from_image(image_bytes: bytes, mime_type: str = "image/jpeg", caption: Optional[str] = None) -> ExtractedTransaction:
    """استخراج المعاملة المالية من صورة فاتورة متعددة الوسائط (Multimodal)"""
    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    ]
    if caption:
        contents.append(f"ملاحظة إضافية من المستخدم: {caption}")
    else:
        contents.append("قم بقراءة هذه الفاتورة واستخراج البيانات المالية منها بدقة.")

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=ExtractedTransaction,
            temperature=0.1
        )
    )
    return response.parsed