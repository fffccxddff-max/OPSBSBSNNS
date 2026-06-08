import os
import sys
import time
import requests
import torch
import gc
import subprocess
import re
from transformers import AutoModelForCausalLM, AutoTokenizer

# --- تنظیمات اولیه و بارگذاری مدل بهینه ---
# توکن شما مستقیماً جایگذاری شد داداش
TELEGRAM_TOKEN = "8940324884:AAGZLh7pJ1go9JmWdlMnaoD6j2wWRAnpADY"
MODEL_NAME = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

if not TELEGRAM_TOKEN:
    print("❌ خطای امنیتی: توکن تلگرام تنظیم نشده است.")
    sys.exit(1)

print("⏳ در حال بارگذاری غول کدنویسی و ابزارها (نسخه بهینه شده رم)...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# لود کردن مدل در حالت bfloat16 روی CPU
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME, 
    torch_dtype=torch.bfloat16, 
    device_map="cpu",
    low_cpu_mem_usage=True
)
print("✅ سیستم با موفقیت بالا آمد داداش! شنود مستمر تلگرام شروع شد...")

# ---------------------------------------------------------
# 🛠 ابزارهای بومی ایجنت (ترمینال + سرچ وب)
# ---------------------------------------------------------

def web_search(query):
    """ابزار سرچ اختصاصی در وب بدون نیاز به کلید API"""
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
    """ابزار ترمینال: اجرای واقعی کد روی سرور اوبونتوی گیت‌هاب"""
    file_name = "sandbox_test.py"
    clean_code = re.sub(r'```python|```', '', code_string).strip()
    
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(clean_code)
    
    try:
        result = subprocess.run(
            ["python3", file_name], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "خطا: زمان اجرای کد بیش از حد طولانی شد (احتمال حلقه بی‌نهایت)."
    except Exception as e:
        return False, f"خطای سیستمی ترمینال: {str(e)}"

def ask_coder_llm(system_prompt, user_input):
    """رابط گفتگو با مدل"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = tokenizer([text], return_tensors="pt")
    
    generated_ids = model.generate(
        **model_inputs, 
        max_new_tokens=1500, 
        do_sample=False
    )
    generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)]
    return tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

# ---------------------------------------------------------
# 🚀 موتور پردازش ۶ عامله (با چرخه عیب‌یابی خودکار)
# ---------------------------------------------------------
def process_autonomous_code(user_prompt, chat_id, message_id):
    requests.post(f"{API_URL}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
    print(f"📥 دریافت درخواست جدید از تلگرام: {user_prompt}")
    
    # ۱. شارد اول: سرچ وب و تحقیق
    print("🤖 شارد ۱: تحقیق و سرچ در وب...")
    search_context = web_search(user_prompt)
    
    # ۲. شارد دوم: تفکر عمیق و معماری
    print("🤖 شارد ۲: تفکر و طراحی منطق برنامه...")
    think_prompt = "تو یک معمار نرم‌افزار هستی. با توجه به درخواست کاربر و نتایج جستجوی زیر، گام به گام فکر کن و ساختار الگوریتم را بنویس. کدی ننویس."
    logic_plan = ask_coder_llm(think_prompt, f"درخواست: {user_prompt}\nنتایج تحقیق وب:\n{search_context}")
    
    # ۳. شارد سوم: کدنویس اصلی
    print("🤖 شارد ۳: تولید کد اولیه...")
    dev_prompt = "تو برنامه‌نویس ارشد هستی. بر اساس نقشه راه زیر، فقط کد خالص پایتون بنویس. هیچ توضیح اضافه‌ای نده."
    generated_code = ask_coder_llm(dev_prompt, logic_plan)
    
    # ۴ و ۵. شارد چهارم و پنجم: مجری ترمینال و دیباگر خودکار
    print("🤖 شارد ۴ و ۵: ورود به چرخه تست ترمینال و دیباگ خودکار...")
    max_retries = 3
    attempt = 0
    is_success = False
    terminal_output = ""
    
    while attempt < max_retries:
        attempt += 1
        print(f"🧪 تست کد در ترمینال اوبونتو (تلاش {attempt} از {max_retries})...")
        is_success, terminal_output = execute_in_terminal(generated_code)
        
        if is_success:
            print("✅ کد با موفقیت در ترمینال تست شد و هیچ باگی نداشت!")
            break
        else:
            print(f"❌ ترمینال خطا داد! ارجاع به شارد دیباگر...")
            debug_prompt = (
                "تو یک دیباگر ارشد هستی. کد زیر در ترمینال با خطا مواجه شده است. "
                "خطا را تحلیل کن و نسخه کاملا اصلاح شده و بدون باگ کد را برگردان. فقط کد خالص بدون توضیح."
            )
            generated_code = ask_coder_llm(debug_prompt, f"کد باگ‌دار:\n{generated_code}\n\nخطای ترمینال:\n{terminal_output}")
            
    # ۶. شارد ششم: مستندسازی و تحویل نهایی
    print("🤖 شارد ۶: آماده‌سازی گزارش دلیوری...")
    delivery_prompt = "تو مسئول تحویل پروژه هستی. یک راهنمای فارسی کوتاه و شیک برای این کد بنویس. خود کد را در متن نگذار."
    explanations = ask_coder_llm(delivery_prompt, f"درخواست: {user_prompt}\nوضعیت تست ترمینال: {is_success}")
    
    # --- ارسال مجزا به تلگرام ---
    status_icon = "🟢" if is_success else "🔴"
    report_message = (
        f"🛠 **پروژه شما با موفقیت در سیستم ۶ شارده پردازش شد داداش!**\n\n"
        f"📊 **وضعیت تست در ترمینال اوبونتو:** {status_icon} { 'بدون خطا و تایید شده' if is_success else 'دارای خطای حل نشده' }\n\n"
        f"📝 **راهنمای اجرای کد:**\n{explanations}"
    )
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": report_message, "parse_mode": "Markdown", "reply_to_message_id": message_id})
    
    code_message = f"💻 **کد نهایی (تست شده و کاملاً خالص):**\n```python\n{generated_code}\n```"
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": code_message, "parse_mode": "Markdown"})
    
    if not is_success:
        error_message = f"⚠️ **آخرین خطای ترمینال که رفع نشد:**\n```text\n{terminal_output}\n```"
        requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": error_message, "parse_mode": "Markdown"})
        
    gc.collect()

# ---------------------------------------------------------
# چرخه شنود مستمر تلگرام
# ---------------------------------------------------------
def start_polling():
    offset = 0
    while True:
        try:
            response = requests.get(f"{API_URL}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            if response.status_code == 409:
                print("⚠️ تداخل رانر (خطای ۴۰۹): ورکر جدیدتری روشن شد.")
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
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    start_polling()
