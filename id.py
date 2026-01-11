import asyncio
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from playwright.async_api import async_playwright

# --- 1. إعداد سيرفر فحص الحالة (Health Check) لـ Render ---
def run_health_check():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is alive")
    
    # Render يمرر المنفذ تلقائياً عبر متغير PORT
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"Health check server started on port {port}")
    server.serve_forever()

# --- 2. إعدادات البوت الآمنة ---
# هنا سحب التوكن من إعدادات Render (لن يظهر التوكن في جيت هب)
API_TOKEN = os.environ.get('BOT_TOKEN')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- 3. وظيفة الفحص باستخدام المتصفح ---
async def get_vaccine_result(id_number):
    async with async_playwright() as p:
        # إعدادات خاصة للعمل داخل Docker وسيرفرات Linux
        browser = await p.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            await page.goto('https://vaccine.moh.ps/certificate', wait_until="networkidle", timeout=60000)
            
            # إدخال البيانات والضغط على الزر
            await page.fill('input[name="id_no"]', id_number)
            await page.click('#inquiryBtn')
            
            # الانتظار حتى تظهر النتيجة (الاسم)
            try:
                await page.wait_for_selector('#name_span', timeout=15000)
            except:
                return "❌ لم يتم العثور على بيانات لهذا الرقم، أو أن الموقع لا يستجيب حالياً."

            # جلب النصوص من العناصر المحددة
            name = await page.inner_text('#name_span')
            mobile = await page.inner_text('#mobile_span')
            birth_date = await page.inner_text('#dob_span')
            address = await page.inner_text('#district_span')

            return (
                f"✅ *تم العثور على البيانات:*\n\n"
                f"👤 *الاسم:* {name}\n"
                f"📅 *تاريخ الميلاد:* {birth_date}\n"
                f"📱 *رقم الهاتف:* {mobile}\n"
                f"📍 *المحافظة:* {address}"
            )

        except Exception as e:
            return f"⚠️ حدث خطأ فني أثناء محاولة الوصول للموقع: {str(e)}"
        finally:
            await browser.close()

# --- 4. أوامر تلجرام ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 أهلاً بك! أرسل رقم الهوية (9 أرقام) وسأقوم بجلب البيانات لك من وزارة الصحة.")

@dp.message()
async def handle_message(message: types.Message):
    if message.text and message.text.isdigit() and len(message.text) == 9:
        status_msg = await message.answer("🔍 جاري الفحص، يرجى الانتظار ثوانٍ...")
        result = await get_vaccine_result(message.text)
        await status_msg.edit_text(result, parse_mode="Markdown")
    else:
        await message.answer("⚠️ يرجى إدخال رقم هوية صحيح مكون من 9 أرقام فقط.")

# --- 5. التشغيل الرئيسي ---
async def main():
    # تشغيل سيرفر الـ Health Check في Thread منفصل
    threading.Thread(target=run_health_check, daemon=True).start()
    
    print("البوت يعمل الآن على السيرفر...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    if not API_TOKEN:
        print("خطأ: لم يتم العثور على BOT_TOKEN في إعدادات البيئة!")
    else:
        asyncio.run(main())