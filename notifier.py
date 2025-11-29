import os
import requests
import json
import jdatetime
from supabase import create_client, Client
from pytz import timezone

# --- تنظیمات و متغیرهای محیطی ---
# این مقادیر از تنظیمات گیت‌هاب (Secrets) خوانده می‌شوند
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

# تزئینات خواسته شده توسط کاربر
STARS = "₊⊹₊⊹₊⊹₊⊹₊⊹"
BOAT = "⊹ ࣪ ﹏𓊝﹏𓂁﹏⊹ ࣪ ˖"

# برنامه هفتگی (شنبه=0, یکشنبه=1, ..., جمعه=6)
WEEKLY_SCHEDULE = {
    0: ["کارگاه ارائه دهنده خدمات رایانه ای 💻", "کارگاه ارائه دهنده خدمات رایانه ای 💻"], # شنبه
    1: ["کارگاه نگه داری از سیستم های رایانه ای 🛠️", "کارگاه نگه داری از سیستم های رایانه ای 🛠️"], # یکشنبه
    2: ["زنگ اول: فارسی 📖", "زنگ دوم: جغرافیا 🌍", "زنگ سوم: ورزش 🏃", "زنگ چهارم: دینی 🕌"], # دوشنبه
    3: ["زنگ اول: متغیر (الزامات/عربی) 🔄", "زنگ دوم: دانش فنی 🧠", "زنگ سوم: زبان 🗣️", "زنگ چهارم: دانش فنی 🧠"], # سه‌شنبه
    4: ["زنگ اول: ریاضی 🧮", "زنگ دوم: فیزیک ⚛️", "زنگ سوم: نقشه کشی 📐", "زنگ چهارم: نقشه کشی 📐"], # چهارشنبه
    5: ["تعطیلی 🥳"], # پنج‌شنبه
    6: ["تعطیلی 🌙"], # جمعه
}

WEEKDAYS_NAMES = {
    0: "شنبه", 1: "یکشنبه", 2: "دوشنبه", 
    3: "سه‌شنبه", 4: "چهارشنبه", 5: "پنج‌شنبه", 6: "جمعه"
}

# بررسی وجود متغیرها
if not all([SUPABASE_URL, SUPABASE_KEY, BOT_TOKEN, CHANNEL_ID]):
    raise ValueError("All environment variables (SUPABASE_URL, SUPABASE_KEY, BOT_TOKEN, CHANNEL_ID) must be set.")

# --- اتصال به سوپابیس ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_tomorrow_date_info():
    """تاریخ فردای شمسی و روز هفته آن را برمی‌گرداند"""
    # امروز را با در نظر گرفتن منطقه زمانی تهران (اگرچه در گیت‌هاب اکشن مهم نیست، اما برای دقت)
    # توجه: jdatetime به صورت پیش‌فرض تاریخ سیستم عامل را می‌گیرد، که در اکشن UTC است.
    # اما چون فقط +1 روز می‌کنیم، روز هفته و تاریخ شمسی درست محاسبه می‌شود.
    tomorrow_jdate = jdatetime.date.today() + jdatetime.timedelta(days=1)
    
    # فرمت باید دقیقا مثل دیتابیس باشد: YYYY/MM/DD
    date_str = tomorrow_jdate.strftime("%Y/%m/%d")
    
    # jdayofweek: شنبه = 0, یکشنبه = 1, ...
    weekday_index = tomorrow_jdate.weekday()
    weekday_name = WEEKDAYS_NAMES.get(weekday_index, "نامشخص")
    
    return date_str, weekday_index, weekday_name

def fetch_plan(date_str):
    """برنامه یک تاریخ خاص را از دیتابیس می‌گیرد"""
    try:
        response = supabase.table('daily_plans').select('*').eq('date', date_str).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def format_telegram_message(plan, date_str, weekday_name, weekday_index):
    """داده‌ها را به یک متن HTML زیبا برای تلگرام تبدیل می‌کند"""
    
    message = f"🌟🌟🌟 <b>اطلاعیه جدید تکالیف و برنامه کلاسی</b> 🌟🌟🌟\n\n"
    message += f"🗓️ تاریخ: <b>{date_str}</b> | روز: <b>{weekday_name}</b>\n"
    message += f"{STARS}\n\n"


    # --- بخش برنامه هفتگی ---
    message += "🏫 <b>برنامه کلاسی فردا:</b>\n"
    schedule = WEEKLY_SCHEDULE.get(weekday_index, ["برنامه‌ای ثبت نشده است."])
    for item in schedule:
        message += f"🔸 {item}\n"
    
    message += f"\n{STARS}\n\n"


    # --- بخش تکالیف و امتحانات (از دیتابیس) ---
    if plan:
        message += f"📝 <b>تکالیف و آزمون‌های روز {weekday_name}:</b>\n\n"
        
        # تکالیف
        homeworks = plan.get('homework', [])
        message += "🟢 <b>📚 تکالیف درسی:</b>\n"
        if homeworks:
            for idx, hw in enumerate(homeworks, 1):
                subject = hw.get('subject', 'درس نامشخص')
                task = hw.get('task', '')
                message += f"  • {idx}. <b>{subject}:</b> {task}\n"
        else:
            message += "  <i>تکلیفی ثبت نشده است.</i>\n"
        
        message += "\n"

        # امتحانات
        exams = plan.get('exams', [])
        if exams:
            message += "🟡 <b>🎯 امتحانات و کوییزها:</b>\n"
            for idx, ex in enumerate(exams, 1):
                subject = ex.get('subject', 'درس نامشخص')
                type_ = ex.get('type', 'امتحان')
                message += f"  • ⚠️ <b>{subject}:</b> {type_}\n"
            message += "\n"

        # نکته روز
        tip = plan.get('tip', '')
        if tip:
            message += "💡 <b>پیام و نکته مهم معلم:</b>\n"
            message += f"  <i>«{tip}»</i>\n\n"
            
    else:
        message += "❌ <b>تکالیف فردا:</b>\n"
        message += "  <i>هنوز برنامه‌ای برای فردا در سیستم ثبت نشده است.</i> 🏖\n\n"

    # --- فوتر و تزئینات نهایی ---
    message += f"{STARS}\n"
    message += f"✨ با آرزوی موفقیت برای شما!\n"
    message += f"{BOAT}"

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
    
    date_str, weekday_index, weekday_name = get_tomorrow_date_info()
    print(f"📅 Checking plan for: {weekday_name} ({date_str})")
    
    plan = fetch_plan(date_str)
    
    if plan:
        print("✅ Plan found in database.")
    else:
        print("⚠️ No specific plan found for tomorrow. Sending only the fixed schedule.")
        
    message = format_telegram_message(plan, date_str, weekday_name, weekday_index)
    send_to_telegram(message)

if __name__ == "__main__":
    main()
