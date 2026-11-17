import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, validate_config
from storage import (
    init_db,
    save_transaction,
    delete_last_transaction,
    get_summary,
    export_to_excel
)
from ai_extractor import extract_from_text, extract_from_image

# إعداد السجلات (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    user_name = update.effective_user.first_name or "صديقي"
    msg = (
        f"أهلاً بك يا {user_name} في **Smart Invoice Bot** 🤖🧾\n\n"
        "أنا مساعدك الذكي لإدارة الفواتير والمصاريف.\n"
        "إليك ما يمكنني فعله:\n"
        "📸 **أرسل صورة فاتورة** وسأستخرج تفاصيلها وأسجلها تلقائياً.\n"
        "💬 **أرسل نص رسالة بنكية أو عامية** (مثال: 'دفعت 60 بنزين' أو 'تم خصم 150 سوبرماركت').\n\n"
        "📌 **الأوامر المتاحة:**\n"
        "📊 `/summary` - عرض الملخص المالي الإجمالي.\n"
        "↩️ `/undo` - التراجع وحذف آخر عملية سجلتها.\n"
        "📥 `/export` - تصدير سجل مصاريفك في ملف إكسل منسق."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /summary"""
    user_id = update.effective_user.id
    summary = get_summary(user_id)
    
    if summary["count"] == 0:
        await update.message.reply_text("لا توجد لديك أي معاملات مسجلة حتى الآن. 📭")
        return

    msg = (
        "📊 **الملخص المالي العام:**\n"
        "────────────────────\n"
        f"💰 **إجمالي الدخل:** {summary['total_income']:,.2f} SAR\n"
        f"💸 **إجمالي المصروفات:** {summary['total_expense']:,.2f} SAR\n"
        "────────────────────\n"
        f"⚖️ **الصافي المتبقي:** {summary['net_balance']:,.2f} SAR\n"
        f"🔢 **عدد العمليات المسجلة:** {summary['count']}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /undo"""
    user_id = update.effective_user.id
    deleted = delete_last_transaction(user_id)
    
    if not deleted:
        await update.message.reply_text("لا توجد عمليات سابقة للتراجع عنها.")
        return

    msg = (
        "🗑️ **تم التراجع وحذف آخر معاملة بنجاح:**\n"
        f"🏢 **المتجر:** {deleted['merchant_name']}\n"
        f"💵 **المبلغ:** {deleted['total_amount']} {deleted['currency']}\n"
        f"🏷️ **التصنيف:** {deleted['category']}\n"
        f"📅 **التاريخ:** {deleted['date']}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /export"""
    user_id = update.effective_user.id
    status_msg = await update.message.reply_text("⏳ جاري توليد ملف الإكسل وتنسيقه...")

    excel_path = export_to_excel(user_id)
    if not excel_path:
        await status_msg.edit_text("لا توجد بيانات مسجلة لديك لتصديرها! 📭")
        return

    try:
        with open(excel_path, "rb") as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename="My_Expenses_Report.xlsx",
                caption="✅ إليك تقرير معاملاتك المالية منسق بالكامل."
            )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Error sending export: {e}")
        await status_msg.edit_text("حدث خطأ أثناء إرسال ملف الإكسل.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة صور الفواتير والإيصالات"""
    user_id = update.effective_user.id
    status_msg = await update.message.reply_text("🔍 جاري قراءة الفاتورة وتحليلها بالذكاء الاصطناعي...")

    try:
        # جلب أعلى دقة للصورة
        photo_file = await update.message.photo[-1].get_file()
        image_bytes = await photo_file.download_as_bytearray()
        caption = update.message.caption

        # استخراج البيانات
        tx = extract_from_image(bytes(image_bytes), mime_type="image/jpeg", caption=caption)
        
        # الحفظ في قاعدة البيانات
        record_id = save_transaction(user_id, tx)

        response_text = (
            "✅ **تم تسجيل الفاتورة بنجاح!**\n"
            "────────────────────\n"
            f"🏢 **المتجر:** {tx.merchant_name}\n"
            f"💵 **المبلغ الإجمالي:** {tx.total_amount:,.2f} {tx.currency}\n"
            f"🏷️ **النوع:** {'مصروف 💸' if tx.transaction_type == 'EXPENSE' else 'دخل 💰'}\n"
            f"📂 **التصنيف:** {tx.category}\n"
            f"📅 **التاريخ:** {tx.date}\n"
        )
        if tx.invoice_number:
            response_text += f"🔢 **رقم الفاتورة:** {tx.invoice_number}\n"
        if tx.items_summary:
            response_text += f"📝 **الأصناف:** {tx.items_summary}\n"
            
        response_text += f"────────────────────\nمعرف السجل: #{record_id}"

        await status_msg.edit_text(response_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error processing photo: {e}", exc_info=True)
        await status_msg.edit_text(f"⚠️ تعذر تحليل الفاتورة: تأكد من وضوح الصورة ومن إعدادات مفتاح API.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة النصوص والرسائل البنكية"""
    user_id = update.effective_user.id
    user_text = update.message.text

    status_msg = await update.message.reply_text("🧠 جاري تحليل المعاملة المالية...")

    try:
        tx = extract_from_text(user_text)
        record_id = save_transaction(user_id, tx)

        response_text = (
            "✅ **تم تسجيل المعاملة بنجاح!**\n"
            "────────────────────\n"
            f"🏢 **الجهة:** {tx.merchant_name}\n"
            f"💵 **المبلغ:** {tx.total_amount:,.2f} {tx.currency}\n"
            f"🏷️ **النوع:** {'مصروف 💸' if tx.transaction_type == 'EXPENSE' else 'دخل 💰'}\n"
            f"📂 **التصنيف:** {tx.category}\n"
            f"📅 **التاريخ:** {tx.date}\n"
            f"────────────────────\nمعرف السجل: #{record_id}"
        )
        await status_msg.edit_text(response_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error processing text: {e}", exc_info=True)
        await status_msg.edit_text("⚠️ تعذر تحليل النص مالياً. يرجى كتابة تفاصيل واضحة عن المبلغ والجهة.")


def main():
    """نقطة تشغيل البوت"""
    # التحقق من الإعدادات
    validate_config()
    
    # تهيئة قاعدة البيانات
    init_db()
    
    logger.info("Starting Smart Invoice Bot...")

    # بناء التطبيق
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # تسجيل الأوامر
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("undo", undo_command))
    app.add_handler(CommandHandler("export", export_command))

    # تسجيل معالجات الوسائط والنصوص
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # بدء تشغيل البوت بنظام Polling
    app.run_polling()


if __name__ == "__main__":
    main()