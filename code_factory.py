import os
import sys
import time
import requests
import torch
import gc
from transformers import AutoModelForCausalLM, AutoTokenizer

# --- تنظیمات اولیه هوش مصنوعی ---
MODEL_NAME = "Qwen/Qwen2.5-Coder-3B-Instruct"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

if not TELEGRAM_TOKEN:
    print("❌ خطای امنیتی: توکن تلگرام در Secrets گیت‌هاب تنظیم نشده است.")
    sys.exit(1)

print("⏳ در حال بارگذاری مدل هوش مصنوعی در حافظه موقت (این کار فقط یک‌بار انجام می‌شود)...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
# لود کردن مدل در حالت bfloat16 روی CPU جهت استفاده بهینه از ۶ گیگابایت رم
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME, 
    torch_dtype=torch.bfloat16, 
    device_map="cpu",
    low_cpu_mem_usage=True
)
print("✅ مدل با موفقیت در رم سرور مستقر شد. ربات آماده پاسخگویی آنی است!")

def ask_coder_llm(system_prompt, user_input):
    """تابع گفتگو با مدل مستقر در حافظه"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = tokenizer([text], return_tensors="pt")
    
    # تولید خروجی با حداکثر کیفیت و تنظیمات بهینه تخصصی کدنویسی
    generated_ids = model.generate(
        **model_inputs, 
        max_new_tokens=2048, 
        do_sample=False,
        temperature=0.0 # صفر کردن دما برای دقت حداکثری در سینتکس کد
    )
    generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)]
    return tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

def send_telegram_message(chat_id, text, reply_to_message_id=None):
    """ارسال پیام به کاربر تلگرام با مدیریت محدودیت ۴۰۰۰ کاراکتر"""
    url = f"{API_URL}/sendMessage"
    
    # اگر طول پیام بیشتر از محدوده تلگرام بود، آن را تکه تکه ارسال کن
    if len(text) > 4000:
        parts = [text[i:i+3900] for i in range(0, len(text), 3900)]
        for index, part in enumerate(parts):
            suffix = "\n\n(ادامه در پیام بعدی...)" if index < len(parts) - 1 else ""
            payload = {
                "chat_id": chat_id,
                "text": part + suffix,
                "parse_mode": "Markdown",
                "reply_to_message_id": reply_to_message_id
            }
            requests.post(url, json=payload)
    else:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_to_message_id": reply_to_message_id
        }
        requests.post(url, json=payload)

def send_typing_status(chat_id):
    """ارسال وضعیت در حال تایپ به کاربر برای تجربه کاربری بهتر"""
    url = f"{API_URL}/sendChatAction"
    requests.post(url, json={"chat_id": chat_id, "action": "typing"})

# ---------------------------------------------------------
# چرخه پردازش تیمی ۵ عامله با حداکثر کیفیت تخصصی
# ---------------------------------------------------------
def process_code_generation(user_prompt, chat_id, message_id):
    send_typing_status(chat_id)
    print(f"📥 دریافت درخواست جدید: {user_prompt}")
    
    # ۱. معمار نرم‌افزار (تحلیل نیازمندی‌ها و معماری سیستم)
    print("🤖 عامل ۱: در حال تحلیل معماری نرم‌افزار...")
    architect_prompt = (
        "تو یک معمار ارشد سیستم‌های نرم‌افزاری هستید. درخواست کاربر را تحلیل کنید و "
        "بهترین ساختار، الگوهای طراحی (Design Patterns)، ماژول‌ها و کلاس‌های مورد نیاز "
        "برای اجرای بدون نقص این کد را تدوین کنید. کدی ننویسید، فقط منطق و گام‌ها را مشخص کنید."
    )
    logic_plan = ask_coder_llm(architect_prompt, user_prompt)
    send_typing_status(chat_id)

    # ۲. کدنویس ارشد (پیاده‌سازی تمیز بر اساس معماری)
    print("🤖 عامل ۲: در حال نوشتن کدهای تمیز...")
    developer_prompt = (
        "تو یک برنامه‌نویس ارشد و فوق‌العاده با استعداد هستی. بر اساس ساختار تحلیل‌شده، "
        "کامل‌ترین و بهینه‌ترین کدها را بنویس. مدیریت خطاها (Exception Handling)، لاگ‌ها "
        "و مستندسازی کدهای درون برنامه‌ای الزامی است. هیچ توضیحی ننویس، فقط کد خام."
    )
    raw_code = ask_coder_llm(developer_prompt, logic_plan)
    send_typing_status(chat_id)

    # ۳. بازبین ارشد کد (بررسی امنیت، پرفورمنس و بهینه‌سازی نهایی)
    print("🤖 عامل ۳: در حال بازبینی امنیتی و فنی کد...")
    reviewer_prompt = (
        "تو متخصص امنیت و بازبین فنی کد (Code Reviewer) هستی. کد نوشته شده را خط به خط "
        "از لحاظ نشتی حافظه، امنیت، سرعت و استانداردهای برنامه‌نویسی بررسی کن. اصلاحات لازم "
        "را اعمال کرده و فقط و فقط کد اصلاح‌شده نهایی را بدون هیچ متن اضافی خروجی بده."
    )
    clean_code = ask_coder_llm(reviewer_prompt, raw_code)
    send_typing_status(chat_id)

    # ۴. مهندس تست (طراحی سناریوهای تست خودکار برای اثبات درستی کد)
    print("🤖 عامل ۴: در حال پیاده‌سازی تست‌ها...")
    tester_prompt = (
        "تو مهندس تست و تضمین کیفیت (QA Engineer) هستی. برای کد نهایی ارائه‌شده، "
        "تست‌های جامع و کاربردی (Unit Tests) بنویس تا صحت کارکرد کد را تضمین کنی. فقط کد تست را خروجی بده."
    )
    test_cases = ask_coder_llm(tester_prompt, clean_code)
    send_typing_status(chat_id)

    # ۵. مستندساز تیمی (تهیه داکیومنت و تفکیک نهایی پیام‌ها)
    print("🤖 عامل ۵: در حال آماده‌سازی گزارش دلیوری...")
    delivery_prompt = (
        "تو مسئول مستندسازی تیم هستی. یک مستند فارسی بسیار شیک و تمیز شامل توضیح ایده، "
        "نحوه اجرا، کتابخانه‌های مورد نیاز و امکانات کد تولید شده بنویس. خود کد اصلی را درون این متن نگذار."
    )
    explanations = ask_coder_llm(delivery_prompt, f"ایده: {user_prompt}\nمعماری:\n{logic_plan}")

    # --- ارسال مجزا پیام‌ها جهت جلوگیری از قاطی شدن کلمات ---
    # پیام اول: گزارش و مستندات فارسی
    report_message = (
        f"🛠 **عملیات تیمی با موفقیت انجام شد داداش!**\n\n"
        f"📝 **توضیحات و راهنمای پروژه:**\n{explanations}"
    )
    send_telegram_message(chat_id, report_message, reply_to_message_id=message_id)

    # پیام دوم: فقط و فقط کد اصلی (داخل بلاک کد تلگرام جهت کپی راحت با یک کلیک)
    code_message = (
        f"💻 **کد اصلی پروژه:**\n```python\n{clean_code}\n```"
    )
    send_telegram_message(chat_id, code_message)

    # پیام سوم: کدهای تست واحد
    test_message = (
        f"🧪 **کدهای تست واحد (Unit Tests):**\n```python\n{test_cases}\n```"
    )
    send_telegram_message(chat_id, test_message)

    print("✨ پروژه‌ با موفقیت تحویل داده شد.")
    # آزادسازی رم بعد از اتمام عملیات
    gc.collect()

# ---------------------------------------------------------
# چرخه شنود دائم تلگرام (Telegram Long Polling Daemon)
# ---------------------------------------------------------
def start_polling():
    offset = 0
    print("🔄 در حال شروع شنود مستمر تلگرام...")
    
    while True:
        try:
            # زمان پاسخ‌دهی طولانی (Long Polling) برای کاهش ترافیک شبکه
            response = requests.get(f"{API_URL}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            
            # مدیریت خطای تداخل اجرای همزمان (وقتی ورکر جدید جایگزین می‌شود)
            if response.status_code == 409:
                print("⚠️ تداخل رانر (خطای ۴۰۹): ورکر جدیدتری روشن شد. این ورکر متوقف می‌شود.")
                break
                
            if response.status_code != 200:
                time.sleep(5)
                continue
                
            updates = response.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message", {})
                text = message.get("text", "")
                chat_id = message.get("chat", {}).get("id")
                message_id = message.get("message_id")
                
                # ربات فقط به پیام‌های متنی واکنش نشان می‌دهد
                if text and chat_id:
                    # شروع پردازش تیمی
                    process_code_generation(text, chat_id, message_id)
                    
        except requests.exceptions.RequestException:
            # مدیریت خطاهای قطع موقت اینترنت سرور
            time.sleep(5)
        except Exception as e:
            print(f"❌ خطای غیرمنتظره در چرخه ربات: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    start_polling()
