from typing import Optional, Literal
from pydantic import BaseModel, Field


class ExtractedTransaction(BaseModel):
    """
    مخطط معياري لتمثيل بيانات الفاتورة أو المعاملة المالية المستخرجة
    Strict Schema for Financial Invoices & Transactions
    """
    invoice_number: Optional[str] = Field(
        default=None, 
        description="رقم الفاتورة أو المرجع أو رقم الإشعار إن وجد"
    )
    date: str = Field(
        description="تاريخ المعاملة بصيغة YYYY-MM-DD. إذا لم يوجد بالتحديد يتم وضع تاريخ اليوم"
    )
    merchant_name: str = Field(
        description="اسم المتجر أو البائع أو الجهة المحول لها / منها"
    )
    total_amount: float = Field(
        description="المبلغ الإجمالي النهائي شامل الضريبة (قيمة رقمية موجبة)"
    )
    tax_amount: Optional[float] = Field(
        default=0.0, 
        description="قيمة الضريبة المضافة (VAT) إن وجدت أو 0.0"
    )
    subtotal_amount: Optional[float] = Field(
        default=0.0, 
        description="المبلغ قبل الضريبة إن وجد"
    )
    currency: str = Field(
        default="SAR", 
        description="رمز العملة، الافتراضي SAR (ريال سعودي) أو USD أو غيرها"
    )
    transaction_type: Literal["EXPENSE", "INCOME"] = Field(
        default="EXPENSE", 
        description="نوع العملية: EXPENSE (مصروف/شراء/دفع) أو INCOME (دخل/إيداع/راتب)"
    )
    category: str = Field(
        description="تصنيف العملية، مثال: Food, Fuel, Office, Utilities, Electronics, Groceries, Salary, Other"
    )
    items_summary: Optional[str] = Field(
        default=None, 
        description="ملخص سريع مقتضب للأصناف أو الخدمة المشتراة"
    )