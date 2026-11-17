import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from config import DB_PATH, EXCEL_EXPORT_PATH
from schemas import ExtractedTransaction


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """إنشاء اتصال مع قاعدة البيانات SQLite"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """إنشاء الجداول الأساسية إذا لم تكن موجودة"""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                invoice_number TEXT,
                date TEXT NOT NULL,
                merchant_name TEXT NOT NULL,
                total_amount REAL NOT NULL,
                tax_amount REAL DEFAULT 0.0,
                subtotal_amount REAL DEFAULT 0.0,
                currency TEXT DEFAULT 'SAR',
                transaction_type TEXT NOT NULL,
                category TEXT NOT NULL,
                items_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def save_transaction(user_id: int, tx: ExtractedTransaction, db_path: str = DB_PATH) -> int:
    """إدراج معاملة جديدة في قاعدة البيانات وإرجاع المعرف الخاص بها"""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (
                user_id, invoice_number, date, merchant_name,
                total_amount, tax_amount, subtotal_amount, currency,
                transaction_type, category, items_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            tx.invoice_number,
            tx.date,
            tx.merchant_name,
            tx.total_amount,
            tx.tax_amount or 0.0,
            tx.subtotal_amount or tx.total_amount,
            tx.currency or "SAR",
            tx.transaction_type,
            tx.category,
            tx.items_summary
        ))
        conn.commit()
        return cursor.lastrowid


def delete_last_transaction(user_id: int, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """حذف آخر عملية قام المستخدم بإدخالها للتراجع عنها (/undo)"""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, merchant_name, total_amount, currency, category, date
            FROM transactions
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
            
        record = dict(row)
        cursor.execute("DELETE FROM transactions WHERE id = ?", (record["id"],))
        conn.commit()
        return record


def get_summary(user_id: int, db_path: str = DB_PATH) -> Dict[str, Any]:
    """حساب ملخص المصروفات والدخل والصافي للمستخدم"""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN transaction_type = 'INCOME' THEN total_amount ELSE 0 END), 0) as total_income,
                COALESCE(SUM(CASE WHEN transaction_type = 'EXPENSE' THEN total_amount ELSE 0 END), 0) as total_expense,
                COUNT(id) as total_count
            FROM transactions
            WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        
        total_income = row["total_income"]
        total_expense = row["total_expense"]
        net_balance = total_income - total_expense
        count = row["total_count"]
        
        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "net_balance": net_balance,
            "count": count
        }


def export_to_excel(user_id: int, output_dir: str = EXCEL_EXPORT_PATH, db_path: str = DB_PATH) -> Optional[str]:
    """تصدير جميع معاملات المستخدم إلى ملف إكسل احترافي منسق"""
    with get_connection(db_path) as conn:
        query = """
            SELECT 
                id AS 'المعرف',
                date AS 'التاريخ',
                merchant_name AS 'المتجر / الجهة',
                transaction_type AS 'النوع',
                category AS 'التصنيف',
                total_amount AS 'المبلغ الإجمالي',
                tax_amount AS 'الضريبة',
                currency AS 'العملة',
                invoice_number AS 'رقم الفاتورة',
                items_summary AS 'تفاصيل الأصناف',
                created_at AS 'وقت التسجيل'
            FROM transactions
            WHERE user_id = ?
            ORDER BY id DESC
        """
        df = pd.read_sql_query(query, conn, params=(user_id,))
        
    if df.empty:
        return None

    # اسم الملف ومساره
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"report_user_{user_id}_{timestamp}.xlsx"
    file_path = os.path.join(output_dir, file_name)

    # حفظ وتنسيق الملف عبر openpyxl
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="المعاملات المالية")
        worksheet = writer.sheets["المعاملات المالية"]

        # تنسيق رأس الجدول (Header)
        header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        center_align = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style="thin", color="D3D3D3"),
            right=Side(style="thin", color="D3D3D3"),
            top=Side(style="thin", color="D3D3D3"),
            bottom=Side(style="thin", color="D3D3D3")
        )

        for col_num in range(1, len(df.columns) + 1):
            cell = worksheet.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align

        # ضبط اتساع الأعمدة تلقائياً وحدود الخلايا
        for col in worksheet.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                cell.border = thin_border
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            worksheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

    return file_path