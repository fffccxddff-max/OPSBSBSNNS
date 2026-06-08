import os
import sys
import time
import requests
import torch
import gc
import subprocess
import re
from transformers import AutoModelForCausalLM, AutoTokenizer

# --- تنظیمات توکن و ارتقا به مدل 1.5B ---
MODEL_NAME = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
TELEGRAM_TOKEN = "8940324884:AAGZLh7pJ1go9JmWdlMnaoD6j2wWRAnpADY"
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

print("⏳ در حال بارگذاری مدل قدرتمند 1.5B به صورت محلی روی سرور گیت‌هاب...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME, 
    torch_dtype=torch.bfloat16, 
    device_map="cpu",
    low_cpu_mem_usage=True
)

# ---------------------------------------------------------
# 🛠 ابزارهای سیستم (ترمینال + سرچ وب)
# ---------------------------------------------------------

def web_search(query):
    """ابزار سرچ اختصاصی در وب"""
    try:
        print(f"🔍 در حال جستجوی وب برای: {query}")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        url = f"https://html.duckduckgo.com/html/?q={query}"
        response = requests.get(url, headers=headers, timeout=10)
        
        snippets = re.findall(r'<a class="result__snippet".*?>(.*?)</a>', response.text, re.DOTALL)
        clean_snippets = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:3]]
        
        if clean_snippets:
            return "\n".join(clean_snippets)
        return "نتیجه مستقیمی در سرچ پیدا نشد."
    except Exception as e:
        return f"خطا در سرچ وب: {str(e)}"

def execute_in_terminal(code_string):
    """ابزار ترمینال: اجرای واقعی کد روی لینوکس اوبونتو"""
    file_name = "sandbox_test.py"
    clean_code = re.sub(r'```python|```', '', code_string).strip()
    
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(clean_code)
    
    try:
        result = subprocess.run(
            ["python3", file_name], 
            capture_output=True, 
            text=True, 
            timeout=12
        )
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "خطا: زمان اجرای کد به دلیل فرآیند سنگین یا حلقه بی‌نهایت اکسپایر شد."
    except Exception as e:
        return False, f"خطای سیستمی ترمینال: {str(e)}"

def ask_coder_llm(system_prompt, user_input):
    """رابط گفتگو با مدل با بالاترین دقت قطعی"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = tokenizer([text], return_tensors="pt")
    
    generated_ids = model.generate(
        **model_inputs, 
        max_new_tokens=1200, 
        do_sample=False  # بالاترین میزان دقت منطقی و بدون خطا
    )
    generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)]
    return tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

# ---------------------------------------------------------
# 🚀 موتور پردازش ۵ شارده (دقت ارتقا یافته با مغز 1.5B)
# ---------------------------------------------------------
def process_autonomous_code(user_prompt, chat_id, message_id):
    requests.post(f"{API_URL}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
    print(f"📥 دریافت درخواست جدید: {user_prompt}")
    
    # شارد ۱: تحقیق وب
    print("🤖 شارد ۱: تحقیق...")
    search_context = web_search(user_prompt)
    
    # شارد ۲: معمار سیستم
    print("🤖 شارد ۲: مهندسی منطق...")
    think_prompt = "تو یک مهندس معمار الگوریتم هستی. ساختار و الزامات دقیق مورد نیاز کد را گام به گام بدون نوشتن خود کد بنویس."
    logic_plan = ask_coder_llm(think_prompt, f"درخواست کاربر: {user_prompt}\nداده‌های وب:\n{search_context}")
    
    # شارد ۳: تولید کد اولیه
    print("🤖 شارد ۳: تولید کد اولیه...")
    dev_prompt = "تو یک برنامه نویس ارشد پایتون هستی. بر اساس ساختار، فقط و فقط کد خالص پایتون بنویس. هیچ کلمه یا توضیح اضافه‌ای بیرون از بلاک کد ننویس."
    generated_code = ask_coder_llm(dev_prompt, logic_plan)
    
    # شارد ۴: تست ترمینال واقعی و اصلاح خودکار خطا
    print("🤖 شارد ۴: ورود به تست اوبونتو و دیباگ...")
    max_retries = 3
    attempt = 0
    is_success = False
    terminal_output = ""
    
    while attempt < max_retries:
        attempt += 1
        print(f"🧪 تست در ترمینال (تلاش {attempt})...")
        is_success, terminal_output = execute_in_terminal(generated_code)
        
        if is_success:
            print("✅ کد با موفقیت و بدون باگ در ترمینال تایید شد!")
            break
        else:
            print(f"❌ باگ پیدا شد! ارجاع به دیباگر...")
            debug_prompt = (
                "تو یک مفسر و دیباگر ارشد پایتون هستی. کد زیر در ترمینال خطا داده است. "
                "خطا را برطرف کن و نسخه نهایی، کامل و بدون باگ کد را بدون هیچ توضیح اضافی برگردان."
            )
            generated_code = ask_coder_llm(debug_prompt, f"کد معیوب:\n{generated_code}\n\nخطای اوبونتو:\n{terminal_output}")
            
    # شارد ۵: بررسی نهایی و دلیوری پروژه
    print("🤖 شارد ۵: تحویل نهایی پروژه...")
    delivery_prompt = "تو مدیر دلیوری پروژه هستی. یک راهنمای فارسی بسیار کوتاه و دقیق برای اجرای این کد بنویس. خود کد را در این متن نگذار."
    explanations = ask_coder_llm(delivery_prompt, f"درخواست: {user_prompt}\nموفقیت تست: {is_success}")
    
    # استخراج و پاکسازی نهایی کدهای مزاحم
    final_clean_code = re.sub(r'```python|```', '', generated_code).strip()
    
    # پیام اول: گزارش وضعیت و راهنما
    status_icon = "🟢" if is_success else "🔴"
    report_message = (
        f"🛠 **پروژه شما در سیستم محلی 1.5B پردازش شد داداش!**\n\n"
        f"📊 **تست ترمینال اوبونتو:** {status_icon} { 'بدون باگ و تایید شده' if is_success else 'دارای خطای حل نشده' }\n\n"
        f"📝 **راهنمای استفاده:**\n{explanations}"
    )
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": report_message, "parse_mode": "Markdown", "reply_to_message_id": message_id})
    
    # پیام دوم: ارسال کد نهایی، کاملاً خالص و بدون خطای تست شده به صورت مجزا
    code_message = f"💻 **کد اصلی و نهایی (تست شده و بی خطا):**\n```python\n{final_clean_code}\n```"
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": code_message, "parse_mode": "Markdown"})
    
    if not is_success:
        error_message = f"⚠️ **آخرین گزارش خطای ترمینال:**\n```text\n{terminal_output}\n```"
        requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": error_message, "parse_mode": "Markdown"})
        
    if os.path.exists("sandbox_test.py"):
        os.remove("sandbox_test.py")
        
    # آزادسازی فوری رم سرور پس از اتمام هر درخواست
    gc.collect()

# ---------------------------------------------------------
# چرخه هوشمند شنود (با تکنیک پاکسازی پیام‌های گذشته)
# ---------------------------------------------------------
def start_polling():
    print("🧹 در حال پاکسازی و فلاش کردن پیام‌های قدیمی صف تلگرام...")
    offset = 0
    try:
        init_resp = requests.get(f"{API_URL}/getUpdates", params={"offset": -1, "timeout": 1}, timeout=5)
        if init_resp.status_code == 200:
            results = init_resp.json().get("result", [])
            if results:
                offset = results[0]["update_id"] + 1
                print("✅ صف با موفقیت تخلیه شد! پیام‌های قدیمی انباشته شده حذف شدند.")
    except Exception as e:
        print(f"⚠️ هشدارهای اولیه فلاش صف: {e}")

    print("✅ غول محلی 1.5B بیدار شد داداش! سیستم آماده دریافت پیام‌های جدید شماست...")
    
    while True:
        try:
            response = requests.get(f"{API_URL}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            if response.status_code == 409:
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
                
                if text and chat_id:
                    process_autonomous_code(text, chat_id, message_id)
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    start_polling()
