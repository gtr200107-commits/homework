import os
import requests
import json
import jdatetime
from supabase import create_client, Client

# --- تنظیمات و متغیرهای محیطی ---
# این مقادیر از تنظیمات گیت‌هاب (Secrets) خوانده می‌شوند
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

# بررسی وجود متغیرها
if not all([SUPABASE_URL, SUPABASE_KEY, BOT_TOKEN, CHANNEL_ID]):
    raise ValueError("All environment variables (SUPABASE_URL, SUPABASE_KEY, BOT_TOKEN, CHANNEL_ID) must be set.")

# --- اتصال به سوپابیس ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_tomorrow_date_str():
    """تاریخ فردای شمسی را برمی‌گرداند"""
    # گرفتن زمان فعلی به وقت تهران نیست، اما کتابخانه jdatetime به صورت پیش‌فرض تاریخ سیستم را می‌گیرد.
    # برای اطمینان، یک روز به تاریخ امروز اضافه می‌کنیم.
    tomorrow = jdatetime.date.today() + jdatetime.timedelta(days=1)
    # فرمت باید دقیقا مثل دیتابیس باشد: YYYY/MM/DD
    return tomorrow.strftime("%Y/%m/%d")

def fetch_plan(date_str):
    """برنامه یک تاریخ خاص را از دیتابیس می‌گیرد"""
    try:
        response = supabase.table('daily_plans').select('*').eq('date', date_str).execute()
        # اگر رکوردی پیدا شود، اولین مورد را برمی‌گرداند
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def format_telegram_message(plan, date_str):
    """داده‌ها را به یک متن HTML زیبا برای تلگرام تبدیل می‌کند"""
    
    if not plan:
        return f"📅 <b>برنامه روز {date_str}</b>\n\n<i>هنوز برنامه‌ای برای فردا در سیستم ثبت نشده است.</i> 🏖"

    message = f"📅 <b>برنامه تکالیف فردا ({date_str})</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # --- بخش تکالیف ---
    message += "🟢 <b>📚 تکالیف درسی:</b>\n"
    homeworks = plan.get('homework', [])
    if homeworks:
        for idx, hw in enumerate(homeworks, 1):
            subject = hw.get('subject', 'درس نامشخص')
            task = hw.get('task', '')
            message += f"{idx}. <b>{subject}:</b> {task}\n"
    else:
        message += "<i>تکلیفی ثبت نشده است.</i>\n"
    
    message += "\n"

    # --- بخش امتحانات ---
    exams = plan.get('exams', [])
    if exams:
        message += "🟡 <b>🎯 امتحانات و کوییزها:</b>\n"
        for idx, ex in enumerate(exams, 1):
            subject = ex.get('subject', 'درس نامشخص')
            type_ = ex.get('type', 'امتحان')
            message += f"⚠️ {idx}. <b>{subject}:</b> {type_}\n"
        message += "\n"

    # --- نکته روز ---
    tip = plan.get('tip', '')
    if tip:
        message += "💡 <b>نکته معلم:</b>\n"
        message += f"<i>«{tip}»</i>\n\n"

    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "🤖 <i>ارسال شده توسط بات راما هوم‌ورک</i>"

    return message

def send_to_telegram(text):
    """پیام نهایی را به کانال ارسال می‌کند"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ Message sent successfully!")
    else:
        print(f"❌ Failed to send message: {response.text}")

def main():
    print("🚀 Starting Daily Notifier...")
    
    tomorrow_str = get_tomorrow_date_str()
    print(f"📅 Checking plan for: {tomorrow_str}")
    
    plan = fetch_plan(tomorrow_str)
    
    if plan:
        print("✅ Plan found.")
    else:
        print("⚠️ No plan found for tomorrow.")
        # اگر می‌خواهید وقتی برنامه‌ای نیست پیامی نرود، خط بعدی را کامنت کنید
        # return 
        
    message = format_telegram_message(plan, tomorrow_str)
    send_to_telegram(message)

if __name__ == "__main__":
    main()
